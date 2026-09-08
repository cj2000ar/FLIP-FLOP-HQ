"""
Guardian Package Verifier - V2 Launcher Component
Verifies artifact integrity before deployment.
Exits with code 78 on verification failure (Guardian-specific termination).
Immutable event logging to persistent event store.

Authority: ZERO
Date: 2026-09-07
"""

import hashlib
import json
import sqlite3
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from enum import Enum


class VerificationStatus(str, Enum):
    """Package verification outcomes"""
    PASS = "PASS"
    HASH_MISMATCH = "HASH_MISMATCH"
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    CORRUPTED = "CORRUPTED"
    POLICY_VIOLATION = "POLICY_VIOLATION"


@dataclass(frozen=True)
class ArtifactManifest:
    """Immutable artifact manifest with expected hashes"""
    strategy_hash: str
    engine_hash: str
    ui_hash: str
    passport_hash: str
    created_at: str


@dataclass(frozen=True)
class VerificationEvent:
    """Immutable verification event for logging"""
    event_id: str
    correlation_id: str
    artifact_type: str
    expected_hash: str
    actual_hash: str
    status: VerificationStatus
    event_time: str
    verified_at: str
    exit_code: int


class GuardianPackageVerifier:
    """Verifies packages before V2 launcher execution"""

    GUARDIAN_EXIT_CODE = 78  # Guardian-specific exit code (not 0, not standard 1)

    def __init__(self, db_path: str = "databases/guardian_events.db"):
        self.db_path = db_path
        self._init_event_store()

    def _init_event_store(self):
        """Initialize immutable event store"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Immutable events table (no UPDATE, DELETE)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_events (
                event_id TEXT PRIMARY KEY,
                correlation_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                expected_hash TEXT NOT NULL,
                actual_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                event_time TEXT NOT NULL,
                verified_at TEXT NOT NULL,
                exit_code INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_correlation_id
            ON verification_events(correlation_id)
        """)

        conn.commit()
        conn.close()

    def compute_hash(self, filepath: str) -> Optional[str]:
        """Compute SHA256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            return None

    def verify_artifact(
        self,
        artifact_path: str,
        expected_hash: str,
        artifact_type: str,
        correlation_id: str
    ) -> Tuple[VerificationStatus, VerificationEvent]:
        """
        Verify single artifact against expected hash.
        Returns (status, immutable_event).
        """
        event_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        # Check file exists
        if not os.path.exists(artifact_path):
            event = VerificationEvent(
                event_id=event_id,
                correlation_id=correlation_id,
                artifact_type=artifact_type,
                expected_hash=expected_hash,
                actual_hash="",
                status=VerificationStatus.MISSING_ARTIFACT,
                event_time=now,
                verified_at=now,
                exit_code=self.GUARDIAN_EXIT_CODE
            )
            self._log_event(event)
            return VerificationStatus.MISSING_ARTIFACT, event

        # Compute actual hash
        actual_hash = self.compute_hash(artifact_path)
        if actual_hash is None:
            event = VerificationEvent(
                event_id=event_id,
                correlation_id=correlation_id,
                artifact_type=artifact_type,
                expected_hash=expected_hash,
                actual_hash="",
                status=VerificationStatus.CORRUPTED,
                event_time=now,
                verified_at=now,
                exit_code=self.GUARDIAN_EXIT_CODE
            )
            self._log_event(event)
            return VerificationStatus.CORRUPTED, event

        # Compare hashes
        if actual_hash != expected_hash:
            event = VerificationEvent(
                event_id=event_id,
                correlation_id=correlation_id,
                artifact_type=artifact_type,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                status=VerificationStatus.HASH_MISMATCH,
                event_time=now,
                verified_at=now,
                exit_code=self.GUARDIAN_EXIT_CODE
            )
            self._log_event(event)
            return VerificationStatus.HASH_MISMATCH, event

        # Hash match
        event = VerificationEvent(
            event_id=event_id,
            correlation_id=correlation_id,
            artifact_type=artifact_type,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            status=VerificationStatus.PASS,
            event_time=now,
            verified_at=now,
            exit_code=0  # Success
        )
        self._log_event(event)
        return VerificationStatus.PASS, event

    def verify_package(
        self,
        manifest: ArtifactManifest,
        artifact_paths: Dict[str, str],  # {artifact_type: filepath}
        correlation_id: str
    ) -> Tuple[VerificationStatus, List[VerificationEvent]]:
        """
        Verify entire package against manifest.
        Returns (overall_status, all_events).
        Exit code 78 if ANY artifact fails.
        """
        events = []
        overall_status = VerificationStatus.PASS

        # Verify each artifact
        artifact_checks = [
            ("strategy", manifest.strategy_hash),
            ("engine", manifest.engine_hash),
            ("ui", manifest.ui_hash),
            ("passport", manifest.passport_hash),
        ]

        for artifact_type, expected_hash in artifact_checks:
            if artifact_type not in artifact_paths:
                status = VerificationStatus.MISSING_ARTIFACT
                overall_status = status
            else:
                filepath = artifact_paths[artifact_type]
                status, event = self.verify_artifact(
                    filepath, expected_hash, artifact_type, correlation_id
                )
                events.append(event)

                if status != VerificationStatus.PASS:
                    overall_status = status

        return overall_status, events

    def _log_event(self, event: VerificationEvent):
        """Log immutable verification event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        payload = {
            "event_id": event.event_id,
            "correlation_id": event.correlation_id,
            "artifact_type": event.artifact_type,
            "expected_hash": event.expected_hash,
            "actual_hash": event.actual_hash,
            "status": event.status.value,
            "event_time": event.event_time,
            "verified_at": event.verified_at,
            "exit_code": event.exit_code,
        }

        cursor.execute("""
            INSERT INTO verification_events
            (event_id, correlation_id, artifact_type, expected_hash, actual_hash,
             status, event_time, verified_at, exit_code, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.correlation_id,
            event.artifact_type,
            event.expected_hash,
            event.actual_hash,
            event.status.value,
            event.event_time,
            event.verified_at,
            event.exit_code,
            json.dumps(payload)
        ))

        conn.commit()
        conn.close()

    def get_verification_events(self, correlation_id: str) -> List[Dict]:
        """Retrieve all verification events for correlation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT payload_json FROM verification_events
            WHERE correlation_id = ?
            ORDER BY created_at ASC
        """, (correlation_id,))

        rows = cursor.fetchall()
        conn.close()

        return [json.loads(row[0]) for row in rows]
