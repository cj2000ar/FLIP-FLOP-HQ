"""Append-only audit trail with hash-linked chain verification"""

import sqlite3
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AuditEngine:
    """Immutable append-only audit trail"""

    def __init__(self, db_dir: str = "databases"):
        self.db_dir = Path(db_dir)
        self.db_path = self.db_dir / "audit.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize append-only schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload JSON NOT NULL,
                content_hash TEXT NOT NULL,
                prev_event_hash TEXT NOT NULL,
                UNIQUE(event_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)
        """)

        conn.commit()
        conn.close()

    def append(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add immutable event to chain (INSERT only, never UPDATE)"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Get previous event hash
            cursor.execute("SELECT content_hash FROM events ORDER BY event_id DESC LIMIT 1")
            prev_row = cursor.fetchone()
            prev_hash = prev_row[0] if prev_row else "0" * 64

            # Compute content hash
            event_json = json.dumps(event_dict, sort_keys=True)
            content_hash = hashlib.sha256(event_json.encode()).hexdigest()

            # INSERT only (no UPDATE possible)
            cursor.execute("""
                INSERT INTO events (timestamp, event_type, payload, content_hash, prev_event_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                event_dict.get('type', 'UNKNOWN'),
                event_json,
                content_hash,
                prev_hash
            ))

            conn.commit()
            event_id = cursor.lastrowid

            logger.info(f"Event appended: {event_dict.get('type')} (id={event_id})")

            return {
                'status': 'OK',
                'event_id': event_id,
                'hash': content_hash,
                'prev_hash': prev_hash
            }

        finally:
            conn.close()

    def verify_chain(self) -> Dict[str, Any]:
        """Independent verification of hash chain"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT event_id, payload, content_hash, prev_event_hash
            FROM events ORDER BY event_id
        """)

        rows = cursor.fetchall()
        conn.close()

        errors = []
        prev_hash = "0" * 64

        for event_id, payload, content_hash, stored_prev_hash in rows:
            # Verify previous hash link
            if stored_prev_hash != prev_hash:
                errors.append(
                    f"Event {event_id}: broken chain "
                    f"(expected prev={prev_hash[:8]}..., got {stored_prev_hash[:8]}...)"
                )

            # Recompute content hash
            recomputed = hashlib.sha256(payload.encode()).hexdigest()
            if recomputed != content_hash:
                errors.append(
                    f"Event {event_id}: corrupted content "
                    f"(computed {recomputed[:8]}..., stored {content_hash[:8]}...)"
                )

            prev_hash = content_hash

        if errors:
            return {
                'status': 'BROKEN',
                'event_count': len(rows),
                'errors': errors
            }

        return {
            'status': 'VALID',
            'event_count': len(rows),
            'final_hash': prev_hash,
            'verification_timestamp': datetime.utcnow().isoformat()
        }

    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Query events (read-only)"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        if event_type:
            cursor.execute("""
                SELECT event_id, timestamp, event_type, payload FROM events
                WHERE event_type = ? ORDER BY event_id DESC LIMIT ?
            """, (event_type, limit))
        else:
            cursor.execute("""
                SELECT event_id, timestamp, event_type, payload FROM events
                ORDER BY event_id DESC LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'event_id': row[0],
                'timestamp': row[1],
                'event_type': row[2],
                'payload': json.loads(row[3])
            }
            for row in rows
        ]

    def count_events(self) -> int:
        """Total event count"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        conn.close()
        return count


class AuditLogger:
    """High-level audit logging interface"""

    def __init__(self, audit_engine: AuditEngine):
        self.audit = audit_engine

    def log_job_started(self, job_id: str, job_type: str) -> None:
        self.audit.append({
            'type': 'JOB_STARTED',
            'job_id': job_id,
            'job_type': job_type
        })

    def log_job_checkpoint(self, job_id: str, state: str, data: Dict) -> None:
        self.audit.append({
            'type': 'JOB_CHECKPOINT',
            'job_id': job_id,
            'state': state,
            'checkpoint_hash': hashlib.sha256(
                json.dumps(data).encode()
            ).hexdigest()
        })

    def log_job_succeeded(self, job_id: str, result_hash: str) -> None:
        self.audit.append({
            'type': 'JOB_SUCCEEDED',
            'job_id': job_id,
            'result_hash': result_hash
        })

    def log_backtest_completed(self, strategy_id: str, instrument: str,
                              result_hash: str, metrics: Dict) -> None:
        self.audit.append({
            'type': 'BACKTEST_COMPLETED',
            'strategy_id': strategy_id,
            'instrument': instrument,
            'result_hash': result_hash,
            'pnl': metrics.get('pnl'),
            'win_rate': metrics.get('win_rate')
        })

    def log_variant_nominated(self, variant_hash: str, parent_hash: str,
                             score: float) -> None:
        self.audit.append({
            'type': 'VARIANT_NOMINATED',
            'variant_hash': variant_hash,
            'parent_hash': parent_hash,
            'score': score,
            'nominated_by': 'AUTO_IMPROVEMENT'
        })

    def log_guardian_verdict(self, variant_hash: str, verdict: str,
                            reasoning: str) -> None:
        self.audit.append({
            'type': 'GUARDIAN_VERDICT',
            'variant_hash': variant_hash,
            'verdict': verdict,
            'reasoning': reasoning
        })

    def log_owner_approval(self, variant_hash: str, approved: bool) -> None:
        self.audit.append({
            'type': 'OWNER_APPROVAL',
            'variant_hash': variant_hash,
            'approved': approved,
            'timestamp': datetime.utcnow().isoformat()
        })

    def log_authority_check(self, authority_level: str, action: str,
                           allowed: bool) -> None:
        self.audit.append({
            'type': 'AUTHORITY_CHECK',
            'authority': authority_level,
            'action': action,
            'allowed': allowed
        })
