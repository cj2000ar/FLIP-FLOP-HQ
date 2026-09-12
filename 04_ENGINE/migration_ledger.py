"""
Migration Ledger for FlipFlop HQ
Immutable audit trail, idempotent apply, state machine, dependency tracking
"""

import logging
import duckdb
from typing import List, Tuple, Optional, Dict
from datetime import datetime
import uuid
import hashlib

logger = logging.getLogger(__name__)


class MigrationLedger:
    """Immutable audit trail of all migration attempts"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def record_apply_attempt(self, migration_number: int, checksum: str,
                             reason: str = "APPLY") -> Tuple[bool, str, str]:
        """Record apply attempt in ledger"""
        try:
            conn = duckdb.connect(self.db_path)

            ledger_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO migration_ledger
                (ledger_id, migration_number, action, status, checksum, reason)
                VALUES (?, ?, 'APPLY', 'STARTED', ?, ?)
            """, [ledger_id, migration_number, checksum, reason])

            conn.close()
            logger.info(f"Recorded apply attempt for migration {migration_number}")
            return True, "Attempt recorded", ledger_id

        except Exception as e:
            logger.error(f"Failed to record apply attempt: {e}")
            return False, str(e), None

    def record_apply_success(self, ledger_id: str) -> bool:
        """Mark apply as succeeded"""
        try:
            conn = duckdb.connect(self.db_path)

            conn.execute("""
                UPDATE migration_ledger
                SET status = 'SUCCESS', completed_at = CURRENT_TIMESTAMP
                WHERE ledger_id = ?
            """, [ledger_id])

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to record apply success: {e}")
            return False

    def record_apply_failure(self, ledger_id: str, error_message: str) -> bool:
        """Mark apply as failed"""
        try:
            conn = duckdb.connect(self.db_path)

            conn.execute("""
                UPDATE migration_ledger
                SET status = 'FAILED', completed_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE ledger_id = ?
            """, [error_message, ledger_id])

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to record apply failure: {e}")
            return False

    def record_rollback(self, migration_number: int, reason: str = "ROLLBACK") -> bool:
        """Record rollback attempt"""
        try:
            conn = duckdb.connect(self.db_path)

            ledger_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO migration_ledger
                (ledger_id, migration_number, action, status, reason, completed_at)
                VALUES (?, ?, 'ROLLBACK', 'SUCCESS', ?, CURRENT_TIMESTAMP)
            """, [ledger_id, migration_number, reason])

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to record rollback: {e}")
            return False

    def get_migration_history(self, migration_number: int) -> List[Dict]:
        """Get audit trail for migration"""
        conn = duckdb.connect(self.db_path)

        results = conn.execute("""
            SELECT ledger_id, action, status, attempted_at, completed_at, reason, error_message
            FROM migration_ledger
            WHERE migration_number = ?
            ORDER BY attempted_at DESC
        """, [migration_number]).fetchall()

        conn.close()

        history = []
        for row in results:
            history.append({
                'ledger_id': row[0],
                'action': row[1],
                'status': row[2],
                'attempted_at': row[3],
                'completed_at': row[4],
                'reason': row[5],
                'error_message': row[6]
            })

        return history


class MigrationState:
    """Atomic state management for migrations"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_state(self, migration_number: int) -> Optional[Dict]:
        """Get current state of migration"""
        conn = duckdb.connect(self.db_path)

        result = conn.execute("""
            SELECT migration_number, current_status, current_checksum, applied_at,
                   rolled_back_at, failed_at, failure_reason, locked
            FROM migration_state
            WHERE migration_number = ?
        """, [migration_number]).fetchall()

        conn.close()

        if result:
            row = result[0]
            return {
                'migration_number': row[0],
                'current_status': row[1],
                'current_checksum': row[2],
                'applied_at': row[3],
                'rolled_back_at': row[4],
                'failed_at': row[5],
                'failure_reason': row[6],
                'locked': row[7]
            }
        return None

    def set_state(self, migration_number: int, status: str, checksum: str = None,
                  failure_reason: str = None) -> bool:
        """Set migration state"""
        try:
            conn = duckdb.connect(self.db_path)

            # Initialize if not exists
            existing = conn.execute(
                "SELECT migration_number FROM migration_state WHERE migration_number = ?",
                [migration_number]
            ).fetchall()

            if not existing:
                ts_col = {'APPLIED': 'applied_at', 'FAILED': 'failed_at',
                          'ROLLED_BACK': 'rolled_back_at'}.get(status, 'updated_at')
                conn.execute(f"""
                    INSERT INTO migration_state
                    (migration_number, current_status, current_checksum, failure_reason, {ts_col})
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, [migration_number, status, checksum, failure_reason])
            else:
                # Update existing
                update_sql = "UPDATE migration_state SET current_status = ?"
                params = [status]

                if status == 'APPLIED':
                    update_sql += ", applied_at = CURRENT_TIMESTAMP"
                    if checksum:
                        update_sql += ", current_checksum = ?"
                        params.append(checksum)

                elif status == 'FAILED':
                    update_sql += ", failed_at = CURRENT_TIMESTAMP"
                    if failure_reason:
                        update_sql += ", failure_reason = ?"
                        params.append(failure_reason)

                elif status == 'ROLLED_BACK':
                    update_sql += ", rolled_back_at = CURRENT_TIMESTAMP"

                update_sql += " WHERE migration_number = ?"
                params.append(migration_number)

                conn.execute(update_sql, params)

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to set state for migration {migration_number}: {e}")
            return False

    def acquire_lock(self, migration_number: int, lock_owner: str = "app") -> bool:
        """Acquire exclusive lock for migration"""
        try:
            conn = duckdb.connect(self.db_path)

            # Check if already locked
            result = conn.execute(
                "SELECT locked FROM migration_state WHERE migration_number = ? AND locked = TRUE",
                [migration_number]
            ).fetchall()

            if result:
                conn.close()
                return False  # Already locked

            exists = conn.execute(
                "SELECT 1 FROM migration_state WHERE migration_number = ?", [migration_number]
            ).fetchall()
            if not exists:
                conn.execute(
                    "INSERT INTO migration_state (migration_number, current_status) VALUES (?, 'PENDING')",
                    [migration_number]
                )

            conn.execute("""
                UPDATE migration_state
                SET locked = TRUE, locked_by = ?, locked_at = CURRENT_TIMESTAMP
                WHERE migration_number = ?
            """, [lock_owner, migration_number])

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False

    def release_lock(self, migration_number: int) -> bool:
        """Release exclusive lock"""
        try:
            conn = duckdb.connect(self.db_path)

            conn.execute("""
                UPDATE migration_state
                SET locked = FALSE, locked_by = NULL, locked_at = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE migration_number = ?
            """, [migration_number])

            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
            return False


class DependencyValidator:
    """Validates migration sequence and dependencies"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def validate_dependencies(self, migration_number: int) -> Tuple[bool, str]:
        """Validate all dependencies applied before migration"""
        conn = duckdb.connect(self.db_path)

        # Get dependencies
        deps_result = conn.execute("""
            SELECT depends_on_migration FROM migration_dependencies
            WHERE migration_number = ?
        """, [migration_number]).fetchall()

        if not deps_result:
            conn.close()
            return True, "No dependencies"

        # Check each dependency
        for dep_row in deps_result:
            dep_migration = dep_row[0]

            dep_state_result = conn.execute("""
                SELECT current_status FROM migration_state
                WHERE migration_number = ?
            """, [dep_migration]).fetchall()

            if not dep_state_result or dep_state_result[0][0] != 'APPLIED':
                conn.close()
                return False, f"Dependency migration {dep_migration} not applied"

        conn.close()
        return True, "All dependencies satisfied"

    def validate_sequence(self, target_migration: int) -> Tuple[bool, str, List[int]]:
        """Validate all migrations up to target are applied in sequence"""
        conn = duckdb.connect(self.db_path)

        # Get all migrations up to target
        required = list(range(1, target_migration + 1))

        # Get applied migrations
        applied_result = conn.execute("""
            SELECT migration_number FROM migration_state
            WHERE current_status = 'APPLIED'
            ORDER BY migration_number ASC
        """).fetchall()

        applied = [row[0] for row in applied_result]
        conn.close()

        # Check sequence
        missing = [m for m in required if m not in applied]

        if missing:
            return False, f"Missing migrations: {missing}", missing

        return True, "Sequence valid", []


class IdempotentMigrator:
    """Idempotent migration apply with state machine"""

    def __init__(self, db_path: str, migration_framework):
        self.db_path = db_path
        self.mf = migration_framework
        self.ledger = MigrationLedger(db_path)
        self.state = MigrationState(db_path)
        self.validator = DependencyValidator(db_path)

    def apply_idempotent(self, migration_number: int, migration_name: str) -> Tuple[bool, str]:
        """
        Apply migration idempotently (safe to re-run)
        Returns: (success, message)
        """
        try:
            # Validate dependencies first
            valid, dep_msg = self.validator.validate_dependencies(migration_number)
            if not valid:
                return False, f"Dependency check failed: {dep_msg}"

            # Get current state
            current_state = self.state.get_state(migration_number)

            # If already applied, verify checksum
            if current_state and current_state['current_status'] == 'APPLIED':
                current_checksum = current_state['current_checksum']
                new_checksum = self.mf.get_checksum(migration_number)

                if current_checksum == new_checksum:
                    logger.info(f"Migration {migration_number} already applied (idempotent)")
                    return True, f"Migration {migration_number} already applied"
                else:
                    logger.error(f"Checksum mismatch for migration {migration_number}")
                    return False, f"Migration file has changed (checksum mismatch)"

            # Try to acquire lock
            if not self.state.acquire_lock(migration_number):
                return False, f"Migration {migration_number} is locked (in progress)"

            try:
                # Record apply attempt
                checksum = self.mf.get_checksum(migration_number)
                success, msg, ledger_id = self.ledger.record_apply_attempt(
                    migration_number, checksum, "IDEMPOTENT_APPLY"
                )

                if not success:
                    return False, f"Failed to record attempt: {msg}"

                # Apply migration
                sql_content = self.mf.read_migration_sql(migration_number)

                conn = duckdb.connect(self.db_path)
                conn.execute("BEGIN TRANSACTION")

                try:
                    # Execute SQL
                    conn.execute(sql_content)

                    # Update state
                    self.state.set_state(migration_number, 'APPLIED', checksum)

                    # Record in legacy migrations table (for backward compat)
                    existing = conn.execute(
                        "SELECT id FROM migrations WHERE migration_number = ?",
                        [migration_number]
                    ).fetchall()

                    if not existing:
                        conn.execute(
                            "INSERT INTO migrations (migration_number, name, status, checksum) VALUES (?, ?, 'APPLIED', ?)",
                            [migration_number, migration_name, checksum]
                        )

                    conn.execute("COMMIT")

                    # Record success
                    self.ledger.record_apply_success(ledger_id)

                    logger.info(f"Applied migration {migration_number} idempotently")
                    return True, f"Migration {migration_number} applied successfully"

                except Exception as e:
                    conn.execute("ROLLBACK")

                    # Record failure
                    self.ledger.record_apply_failure(ledger_id, str(e))
                    self.state.set_state(migration_number, 'FAILED', failure_reason=str(e))

                    logger.error(f"Migration {migration_number} apply failed: {e}")
                    return False, f"Apply failed: {str(e)}"

                finally:
                    conn.close()

            finally:
                # Release lock
                self.state.release_lock(migration_number)

        except Exception as e:
            logger.error(f"Idempotent apply error: {e}")
            return False, str(e)

    def apply_all_idempotent(self, target_migration: int = None) -> Tuple[int, int, List[str]]:
        """
        Apply all pending migrations idempotently
        Returns: (applied_count, failed_count, errors)
        """
        applied = 0
        failed = 0
        errors = []

        # Validate sequence
        if target_migration:
            valid, msg, missing = self.validator.validate_sequence(target_migration)
            if not valid:
                return 0, 1, [f"Sequence validation failed: {msg}"]

        # Get pending migrations
        pending = self.mf.apply_all_pending(target_migration) if hasattr(self.mf, 'apply_all_pending') else []

        for migration_num in pending:
            # Get migration name
            files = list(self.mf.migrations_dir.glob(f"{migration_num:04d}_*.sql"))
            if files:
                migration_name = files[0].stem.replace(f"{migration_num:04d}_", "")

                success, msg = self.apply_idempotent(migration_num, migration_name)
                if success:
                    applied += 1
                else:
                    failed += 1
                    errors.append(msg)

        return applied, failed, errors
