"""
Evidence Retention for FlipFlop HQ
Retention policies, archival scheduling, and compliance exports
"""

import logging
import duckdb
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta
import uuid
import gzip
import json

logger = logging.getLogger(__name__)


class RetentionPolicyManager:
    """Manages evidence retention policies"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_policy(self, event_type: str) -> Optional[Dict]:
        """Get retention policy for event type"""
        conn = duckdb.connect(self.db_path)

        result = conn.execute("""
            SELECT policy_id, event_type, retention_days, archive_after_days,
                   deletion_allowed, compliance_hold
            FROM retention_policies
            WHERE event_type = ?
        """, [event_type]).fetchall()

        conn.close()

        if result:
            row = result[0]
            return {
                'policy_id': row[0],
                'event_type': row[1],
                'retention_days': row[2],
                'archive_after_days': row[3],
                'deletion_allowed': row[4],
                'compliance_hold': row[5]
            }
        return None

    def set_policy(self, event_type: str, retention_days: int,
                   archive_after_days: int = None, deletion_allowed: bool = False,
                   compliance_hold: bool = False) -> Tuple[bool, str]:
        """Create or update retention policy"""
        try:
            conn = duckdb.connect(self.db_path)

            policy_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO retention_policies
                (policy_id, event_type, retention_days, archive_after_days,
                 deletion_allowed, compliance_hold, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (event_type) DO UPDATE SET
                    retention_days = excluded.retention_days,
                    archive_after_days = excluded.archive_after_days,
                    deletion_allowed = excluded.deletion_allowed,
                    compliance_hold = excluded.compliance_hold,
                    updated_at = now()
            """, [policy_id, event_type, retention_days, archive_after_days,
                  deletion_allowed, compliance_hold])

            conn.close()
            logger.info(f"Policy set for {event_type}: {retention_days}d retention")
            return True, f"Policy updated for {event_type}"

        except Exception as e:
            logger.error(f"Policy update failed: {e}")
            return False, str(e)

    def list_policies(self) -> List[Dict]:
        """List all retention policies"""
        conn = duckdb.connect(self.db_path)

        results = conn.execute("""
            SELECT policy_id, event_type, retention_days, archive_after_days,
                   deletion_allowed, compliance_hold
            FROM retention_policies
            ORDER BY event_type
        """).fetchall()

        conn.close()

        policies = []
        for row in results:
            policies.append({
                'event_type': row[1],
                'retention_days': row[2],
                'archive_after_days': row[3],
                'deletion_allowed': row[4],
                'compliance_hold': row[5]
            })

        return policies


class EvidenceArchiver:
    """Handles evidence batch archival and compression"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def archive_batch(self, batch_id: str, compression_type: str = 'gzip') -> Tuple[bool, str]:
        """Archive batch (compress + seal)"""
        try:
            conn = duckdb.connect(self.db_path)

            # Get batch + events
            batch_result = conn.execute("""
                SELECT el.batch_id, el.start_log_id, el.end_log_id, el.log_count, el.batch_hash
                FROM evidence_ledger el
                WHERE batch_id = ?
            """, [batch_id]).fetchall()

            if not batch_result:
                conn.close()
                return False, "Batch not found"

            start_id, end_id, log_count, batch_hash = batch_result[0][1:]

            # Fetch events
            events_result = conn.execute("""
                SELECT log_id, event_type, owner_id, device_id, ip_address, status, reason, event_at
                FROM auth_audit_log
                WHERE log_id >= ? AND log_id <= ?
                ORDER BY event_at ASC
            """, [start_id, end_id]).fetchall()

            events_data = json.dumps([{
                'log_id': row[0],
                'event_type': row[1],
                'owner_id': row[2],
                'device_id': row[3],
                'ip_address': row[4],
                'status': row[5],
                'reason': row[6],
                'event_at': str(row[7])
            } for row in events_result], indent=2)

            # Compress
            if compression_type == 'gzip':
                archive_data = gzip.compress(events_data.encode())
            else:
                archive_data = events_data.encode()

            # Compute archive hash
            import hashlib
            archive_hash = hashlib.sha256(archive_data).hexdigest()

            # Record archive
            archive_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO evidence_archival
                (archive_id, batch_id, archive_hash, compression_type)
                VALUES (?, ?, ?, ?)
            """, [archive_id, batch_id, archive_hash, compression_type])

            # Update batch status
            conn.execute("""
                UPDATE evidence_batch_status
                SET status = 'ARCHIVED', status_changed_at = CURRENT_TIMESTAMP
                WHERE batch_id = ?
            """, [batch_id])

            conn.close()

            logger.info(f"Archived batch {batch_id}: {len(events_result)} events, {len(archive_data)} bytes")
            return True, f"Batch archived: {archive_id}"

        except Exception as e:
            logger.error(f"Archival failed: {e}")
            return False, str(e)

    def archive_expired_batches(self) -> Tuple[int, int]:
        """Archive batches past archive_after_days threshold"""
        conn = duckdb.connect(self.db_path)

        # Get eligible batches
        eligible_result = conn.execute("""
            SELECT el.batch_id, el.sealed_at
            FROM evidence_ledger el
            WHERE NOT EXISTS (
                SELECT 1 FROM evidence_archival ea WHERE ea.batch_id = el.batch_id
            )
            AND el.sealed_at < CURRENT_TIMESTAMP - (
                (SELECT MIN(rp.archive_after_days) FROM retention_policies rp) * INTERVAL 1 DAY
            )
        """).fetchall()

        conn.close()

        archived = 0
        failed = 0

        for batch_id, sealed_at in eligible_result:
            success, msg = self.archive_batch(batch_id)
            if success:
                archived += 1
            else:
                failed += 1
                logger.warning(f"Failed to archive {batch_id}: {msg}")

        return archived, failed


class ComplianceExporter:
    """Exports audit trail for compliance (GDPR, SOC2, etc.)"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def export_owner_audit(self, owner_id: str, start_date: datetime = None,
                          end_date: datetime = None) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        Export audit trail for owner (GDPR: right to data access)
        Returns: (success, message, audit_events)
        """
        try:
            conn = duckdb.connect(self.db_path)

            query = """
                SELECT log_id, event_type, device_id, ip_address, status, reason, event_at
                FROM auth_audit_log
                WHERE owner_id = ?
            """
            params = [owner_id]

            if start_date:
                query += " AND event_at >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND event_at <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY event_at DESC"

            results = conn.execute(query, params).fetchall()
            conn.close()

            events = []
            for row in results:
                events.append({
                    'log_id': row[0],
                    'event_type': row[1],
                    'device_id': row[2],
                    'ip_address': row[3],
                    'status': row[4],
                    'reason': row[5],
                    'event_at': row[6]
                })

            logger.info(f"Exported {len(events)} audit events for owner {owner_id}")
            return True, f"Exported {len(events)} events", events

        except Exception as e:
            logger.error(f"Audit export failed: {e}")
            return False, str(e), None

    def export_compliance_report(self, report_type: str = 'SOC2',
                                 start_date: datetime = None,
                                 end_date: datetime = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Generate compliance report
        report_type: 'SOC2', 'GDPR', 'HIPAA', 'PCI-DSS'
        """
        try:
            conn = duckdb.connect(self.db_path)

            if start_date is None:
                start_date = datetime.utcnow() - timedelta(days=90)
            if end_date is None:
                end_date = datetime.utcnow()

            # Gather metrics
            login_events = conn.execute("""
                SELECT COUNT(*) FROM auth_audit_log
                WHERE event_type = 'LOGIN' AND event_at >= ? AND event_at <= ?
            """, [start_date.isoformat(), end_date.isoformat()]).fetchall()[0][0]

            mfa_failures = conn.execute("""
                SELECT COUNT(*) FROM auth_audit_log
                WHERE event_type = 'MFA_VERIFICATION_FAILED' AND event_at >= ? AND event_at <= ?
            """, [start_date.isoformat(), end_date.isoformat()]).fetchall()[0][0]

            rotations = conn.execute("""
                SELECT COUNT(*) FROM credential_rotations
                WHERE rotated_at >= ? AND rotated_at <= ?
            """, [start_date.isoformat(), end_date.isoformat()]).fetchall()[0][0]

            sealed_batches = conn.execute("""
                SELECT COUNT(*) FROM evidence_ledger
                WHERE sealed_at >= ? AND sealed_at <= ?
            """, [start_date.isoformat(), end_date.isoformat()]).fetchall()[0][0]

            conn.close()

            report = {
                'report_type': report_type,
                'generated_at': datetime.utcnow().isoformat(),
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'metrics': {
                    'login_attempts': login_events,
                    'mfa_failures': mfa_failures,
                    'credential_rotations': rotations,
                    'sealed_batches': sealed_batches
                },
                'compliance_status': 'PASS' if sealed_batches > 0 else 'REVIEW'
            }

            logger.info(f"Generated {report_type} compliance report")
            return True, f"Report generated", report

        except Exception as e:
            logger.error(f"Compliance report generation failed: {e}")
            return False, str(e), None
