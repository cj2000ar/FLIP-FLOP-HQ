"""Idempotent, resumable job orchestrator with checkpoint system"""

import sqlite3
import json
import hashlib
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class JobState(Enum):
    SUBMITTED = "SUBMITTED"
    VALIDATING = "VALIDATING"
    DOWNLOADING = "DOWNLOADING"
    SIMULATING = "SIMULATING"
    SCORING = "SCORING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class JobCheckpoint:
    """Immutable checkpoint for resumability"""
    job_id: str
    state: JobState
    timestamp: str
    checkpoint_data: Dict[str, Any]
    data_hash: str = ""

    def save(self, db_path: Path) -> None:
        """Save checkpoint (append-only)"""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO job_checkpoints (job_id, state, timestamp, checkpoint_data, data_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (
            self.job_id,
            self.state.value,
            self.timestamp,
            json.dumps(self.checkpoint_data),
            self.data_hash
        ))

        conn.commit()
        conn.close()


class JobOrchestrator:
    """Idempotent job execution with resumability"""

    def __init__(self, db_dir: str = "databases"):
        self.db_dir = Path(db_dir)
        self.db_path = self.db_dir / "jobs.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize append-only job database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE NOT NULL,
                state TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL,
                result JSON,
                error TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_checkpoints (
                checkpoint_id INTEGER PRIMARY KEY,
                job_id TEXT NOT NULL,
                state TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                checkpoint_data JSON NOT NULL,
                data_hash TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_state
            ON jobs(job_id, state)
        """)

        conn.commit()
        conn.close()

    def _compute_idempotency_key(self, job_def: Dict[str, Any]) -> str:
        """Compute idempotency key from job definition"""
        content = json.dumps({
            'strategy_hash': job_def.get('strategy_hash'),
            'data_hash': job_def.get('data_hash'),
            'params': job_def.get('params', {})
        }, sort_keys=True)

        return hashlib.sha256(content.encode()).hexdigest()

    def check_duplicate(self, job_def: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if identical job already completed"""
        idempotency_key = self._compute_idempotency_key(job_def)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT job_id, state, result FROM jobs
            WHERE idempotency_key = ? AND state = ?
        """, (idempotency_key, JobState.SUCCEEDED.value))

        row = cursor.fetchone()
        conn.close()

        if row:
            job_id, state, result = row
            logger.info(f"Duplicate detected: {job_id} already succeeded")
            return {
                'status': 'DUPLICATE_SKIPPED',
                'job_id': job_id,
                'prior_result': json.loads(result) if result else None
            }

        return None

    def resume_job(self, job_id: str) -> Optional[JobState]:
        """Get last checkpoint for job resumption"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT state, checkpoint_data FROM job_checkpoints
            WHERE job_id = ? ORDER BY checkpoint_id DESC LIMIT 1
        """, (job_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            state_str, checkpoint_data = row
            logger.info(f"Resuming job {job_id} from state {state_str}")
            return JobState(state_str), json.loads(checkpoint_data)

        return None, None

    def run_job(self, job_def: Dict[str, Any], job_handler) -> Dict[str, Any]:
        """Execute job with idempotency and resumability"""
        job_id = job_def.get('job_id')
        idempotency_key = self._compute_idempotency_key(job_def)

        # Check for duplicates
        duplicate = self.check_duplicate(job_def)
        if duplicate:
            return duplicate

        # Check for resumption point
        start_state = JobState.SUBMITTED
        checkpoint_data = {}
        resume_info = self.resume_job(job_id)
        if resume_info[0]:
            start_state = resume_info[0]
            checkpoint_data = resume_info[1]

        # Create job record if new
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO jobs
                (job_id, idempotency_key, state, start_time, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                job_id,
                idempotency_key,
                start_state.value,
                datetime.utcnow().timestamp(),
                datetime.utcnow().isoformat()
            ))
            conn.commit()
        finally:
            conn.close()

        # Execute job handler
        try:
            result = job_handler(job_def, start_state, checkpoint_data)

            # Record success
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE jobs SET state = ?, end_time = ?, result = ?
                WHERE job_id = ?
            """, (
                JobState.SUCCEEDED.value,
                datetime.utcnow().timestamp(),
                json.dumps(result),
                job_id
            ))

            conn.commit()
            conn.close()

            logger.info(f"Job {job_id} succeeded")
            return {
                'status': 'SUCCEEDED',
                'job_id': job_id,
                'result': result
            }

        except Exception as e:
            # Record failure
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE jobs SET state = ?, end_time = ?, error = ?
                WHERE job_id = ?
            """, (
                JobState.FAILED.value,
                datetime.utcnow().timestamp(),
                str(e),
                job_id
            ))

            conn.commit()
            conn.close()

            logger.error(f"Job {job_id} failed: {str(e)}")
            return {
                'status': 'FAILED',
                'job_id': job_id,
                'error': str(e)
            }
