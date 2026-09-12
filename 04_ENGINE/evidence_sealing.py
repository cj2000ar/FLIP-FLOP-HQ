"""
Evidence Sealing for FlipFlop HQ
Cryptographic batch sealing with hash chain for immutable audit trail
"""

import hashlib
import logging
import duckdb
from typing import List, Tuple, Optional, Dict
from datetime import datetime
import uuid
import json
import hmac

logger = logging.getLogger(__name__)


class HashChain:
    """Manages cryptographic hash chain for evidence batches"""

    @staticmethod
    def compute_batch_hash(events: List[Dict], previous_batch_hash: str = None) -> str:
        """
        Compute SHA256 hash of batch
        Includes previous_batch_hash to create chain
        """
        event_data = json.dumps(events, sort_keys=True, default=str)
        event_hash = hashlib.sha256(event_data.encode()).hexdigest()

        if previous_batch_hash:
            chain_data = f"{previous_batch_hash}{event_hash}"
            return hashlib.sha256(chain_data.encode()).hexdigest()

        return event_hash

    @staticmethod
    def validate_chain(batch_hashes: List[Tuple[str, str]]) -> bool:
        """
        Validate hash chain integrity
        batch_hashes: list of (batch_hash, previous_batch_hash) tuples
        """
        if not batch_hashes:
            return True

        for i, (batch_hash, previous_hash) in enumerate(batch_hashes):
            if i == 0 and previous_hash is not None:
                logger.warning("First batch should have no previous hash")
                return False

            if i > 0:
                expected_prev = batch_hashes[i-1][0]
                if previous_hash != expected_prev:
                    logger.error(f"Hash chain broken at batch {i}: expected {expected_prev}, got {previous_hash}")
                    return False

        return True

    @staticmethod
    def verify_batch_hash(events: List[Dict], batch_hash: str, previous_batch_hash: str = None) -> bool:
        """Verify batch hash matches event data"""
        computed_hash = HashChain.compute_batch_hash(events, previous_batch_hash)
        return hmac.compare_digest(computed_hash, batch_hash)


class BatchSigner:
    """Optional cryptographic signing for batches (HMAC-SHA256)"""

    def __init__(self, signing_key: str = None):
        self.signing_key = signing_key or "default-key"

    def sign_batch(self, batch_hash: str) -> str:
        """Generate HMAC signature for batch"""
        signature = hmac.new(
            self.signing_key.encode(),
            batch_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify_signature(self, batch_hash: str, signature: str) -> bool:
        """Verify batch signature"""
        expected_sig = self.sign_batch(batch_hash)
        return hmac.compare_digest(expected_sig, signature)


class EvidenceSealer:
    """Seals audit events into cryptographically verified batches"""

    def __init__(self, db_path: str, batch_size: int = 1000):
        self.db_path = db_path
        self.batch_size = batch_size
        self.signer = BatchSigner()

    def get_unsealed_events(self, limit: int = None) -> List[Dict]:
        """Fetch unsealed events from auth_audit_log"""
        if limit is None:
            limit = self.batch_size

        conn = duckdb.connect(self.db_path)

        results = conn.execute("""
            SELECT log_id, event_type, owner_id, device_id, ip_address, status, reason, event_at
            FROM auth_audit_log
            WHERE log_id NOT IN (
                SELECT start_log_id FROM evidence_ledger
                UNION
                SELECT end_log_id FROM evidence_ledger
            )
            ORDER BY event_at ASC
            LIMIT ?
        """, [limit]).fetchall()

        conn.close()

        events = []
        for row in results:
            events.append({
                'log_id': row[0],
                'event_type': row[1],
                'owner_id': row[2],
                'device_id': row[3],
                'ip_address': row[4],
                'status': row[5],
                'reason': row[6],
                'event_at': row[7]
            })

        return events

    def get_last_batch_hash(self) -> Optional[str]:
        """Get previous batch hash for chain continuation"""
        conn = duckdb.connect(self.db_path)

        result = conn.execute("""
            SELECT batch_hash FROM evidence_ledger
            ORDER BY batch_sequence DESC
            LIMIT 1
        """).fetchall()

        conn.close()

        return result[0][0] if result else None

    def seal_batch(self, events: List[Dict]) -> Tuple[bool, str, Optional[Dict]]:
        """
        Seal events into batch
        Returns: (success, message, batch_data)
        """
        if not events:
            return False, "No events to seal", None

        try:
            conn = duckdb.connect(self.db_path)

            # Get sequence number
            seq_result = conn.execute("""
                SELECT COALESCE(MAX(batch_sequence), 0) + 1
                FROM evidence_ledger
            """).fetchall()
            batch_sequence = seq_result[0][0]

            # Get previous batch hash
            previous_batch_hash = self.get_last_batch_hash()

            # Compute batch hash
            batch_hash = HashChain.compute_batch_hash(events, previous_batch_hash)

            # Sign batch
            signature = self.signer.sign_batch(batch_hash)

            # Create batch record
            batch_id = str(uuid.uuid4())
            start_log_id = events[0]['log_id']
            end_log_id = events[-1]['log_id']
            log_count = len(events)

            conn.execute("""
                INSERT INTO evidence_ledger
                (batch_id, batch_sequence, start_log_id, end_log_id, log_count,
                 batch_hash, previous_batch_hash, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [batch_id, batch_sequence, start_log_id, end_log_id, log_count,
                  batch_hash, previous_batch_hash, signature])

            # Record batch status
            conn.execute("""
                INSERT INTO evidence_batch_status (batch_id, status)
                VALUES (?, 'SEALED')
            """, [batch_id])

            conn.close()

            batch_data = {
                'batch_id': batch_id,
                'batch_sequence': batch_sequence,
                'batch_hash': batch_hash,
                'log_count': log_count,
                'signature': signature
            }

            logger.info(f"Sealed batch {batch_id}: {log_count} events, hash {batch_hash[:16]}...")
            return True, f"Sealed batch with {log_count} events", batch_data

        except Exception as e:
            logger.error(f"Batch sealing failed: {e}")
            conn.close()
            return False, str(e), None

    def seal_all_pending(self) -> Tuple[int, int]:
        """Seal all pending events into batches. Returns (batches_sealed, total_events)"""
        batches_sealed = 0
        total_events = 0

        while True:
            events = self.get_unsealed_events(limit=self.batch_size)
            if not events:
                break

            success, msg, batch_data = self.seal_batch(events)
            if success:
                batches_sealed += 1
                total_events += len(events)
            else:
                logger.warning(f"Failed to seal batch: {msg}")
                break

        logger.info(f"Sealed {batches_sealed} batches ({total_events} events)")
        return batches_sealed, total_events


class EvidenceVerifier:
    """Verifies evidence batch integrity and chain validity"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.signer = BatchSigner()

    def verify_batch(self, batch_id: str) -> Tuple[bool, str]:
        """Verify single batch integrity"""
        conn = duckdb.connect(self.db_path)

        # Get batch
        batch_result = conn.execute("""
            SELECT batch_id, batch_hash, previous_batch_hash, signature, start_log_id, end_log_id
            FROM evidence_ledger
            WHERE batch_id = ?
        """, [batch_id]).fetchall()

        if not batch_result:
            conn.close()
            return False, "Batch not found"

        batch_hash, prev_hash, signature, start_id, end_id = batch_result[0][1:]

        # Get events in batch
        events_result = conn.execute("""
            SELECT log_id, event_type, owner_id, device_id, ip_address, status, reason, event_at
            FROM auth_audit_log
            WHERE log_id >= ? AND log_id <= ?
            ORDER BY event_at ASC
        """, [start_id, end_id]).fetchall()

        conn.close()

        if not events_result:
            return False, "No events found in batch"

        events = []
        for row in events_result:
            events.append({
                'log_id': row[0],
                'event_type': row[1],
                'owner_id': row[2],
                'device_id': row[3],
                'ip_address': row[4],
                'status': row[5],
                'reason': row[6],
                'event_at': row[7]
            })

        # Verify hash
        if not HashChain.verify_batch_hash(events, batch_hash, prev_hash):
            return False, "Batch hash mismatch (data may have been tampered)"

        # Verify signature
        if signature and not self.signer.verify_signature(batch_hash, signature):
            return False, "Signature verification failed"

        return True, "Batch verified"

    def verify_chain(self) -> Tuple[bool, str, int]:
        """
        Verify entire hash chain
        Returns: (is_valid, message, batches_checked)
        """
        conn = duckdb.connect(self.db_path)

        batches = conn.execute("""
            SELECT batch_id, batch_hash, previous_batch_hash
            FROM evidence_ledger
            ORDER BY batch_sequence ASC
        """).fetchall()

        conn.close()

        if not batches:
            return True, "No batches to verify", 0

        chain_data = [(b[1], b[2]) for b in batches]

        if not HashChain.validate_chain(chain_data):
            return False, "Chain integrity check failed", len(batches)

        logger.info(f"Chain verified: {len(batches)} batches")
        return True, "Chain integrity verified", len(batches)

    def log_verification(self, batch_id: str, is_valid: bool, failure_reason: str = None):
        """Log verification result"""
        conn = duckdb.connect(self.db_path)

        verification_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO evidence_verification_log
            (verification_id, batch_id, verification_type, is_valid, failure_reason)
            VALUES (?, ?, 'HASH_CHAIN', ?, ?)
        """, [verification_id, batch_id, is_valid, failure_reason])

        conn.close()
