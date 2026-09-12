"""
Migration Framework for FlipFlop HQ Database
Handles apply/rollback with checksums and transaction safety
"""

import hashlib
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import duckdb

logger = logging.getLogger(__name__)


class MigrationFramework:
    """Manages database migrations with checksums and rollback support"""

    def __init__(self, db_path: str, migrations_dir: str = "migrations",
                 create_if_missing: bool = True):
        self.db_path = Path(db_path)
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        if not self.db_path.exists():
            if not create_if_missing:
                raise FileNotFoundError(f"Database not found: {db_path}")
            # DuckDB creates the file on first connect; only the parent dir must exist.
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _forward_file(self, migration_number: int) -> Path:
        """Locate the forward SQL for a migration (NNNN_<name>.sql), excluding NNNN_rollback.sql."""
        files = [
            f for f in self.migrations_dir.glob(f"{migration_number:04d}_*.sql")
            if not f.name.endswith("_rollback.sql")
        ]

        if not files:
            raise FileNotFoundError(f"Migration {migration_number} SQL file not found")

        if len(files) > 1:
            raise ValueError(f"Multiple migration {migration_number} files found")

        return files[0]

    def get_checksum(self, migration_number: int) -> str:
        """Calculate checksum of migration SQL file"""
        with open(self._forward_file(migration_number), 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def read_migration_sql(self, migration_number: int) -> str:
        """Read migration SQL from file"""
        with open(self._forward_file(migration_number), 'r') as f:
            return f.read()

    def init_migrations_table(self):
        """Ensure migrations tracking table exists"""
        conn = duckdb.connect(str(self.db_path))
        try:
            # DuckDB has no implicit autoincrement; use an explicit sequence.
            conn.execute("CREATE SEQUENCE IF NOT EXISTS migrations_id_seq")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY DEFAULT nextval('migrations_id_seq'),
                    migration_number INTEGER NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'APPLIED',
                    checksum TEXT NOT NULL
                )
            """)
            conn.close()
        except Exception as e:
            logger.error(f"Failed to init migrations table: {e}")
            raise

    def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration numbers"""
        self.init_migrations_table()
        conn = duckdb.connect(str(self.db_path))
        try:
            result = conn.execute(
                "SELECT migration_number FROM migrations WHERE status = 'APPLIED' ORDER BY migration_number"
            ).fetchall()
            return [row[0] for row in result]
        finally:
            conn.close()

    def get_migration_status(self, migration_number: int) -> Optional[Dict[str, Any]]:
        """Get status of specific migration"""
        self.init_migrations_table()
        conn = duckdb.connect(str(self.db_path))
        try:
            result = conn.execute(
                "SELECT migration_number, name, applied_at, status, checksum FROM migrations WHERE migration_number = ?",
                [migration_number]
            ).fetchall()
            if result:
                row = result[0]
                return {
                    'number': row[0],
                    'name': row[1],
                    'applied_at': row[2],
                    'status': row[3],
                    'checksum': row[4]
                }
            return None
        finally:
            conn.close()

    @staticmethod
    def _sync_state(conn, migration_number: int, status: str, checksum: Optional[str]):
        """Mirror status into migration_state (P5 ledger) when that table exists."""
        has_state = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'migration_state'"
        ).fetchall()
        if not has_state:
            return
        ts_col = 'applied_at' if status == 'APPLIED' else 'rolled_back_at'
        existing = conn.execute(
            "SELECT 1 FROM migration_state WHERE migration_number = ?", [migration_number]
        ).fetchall()
        if existing:
            conn.execute(
                f"UPDATE migration_state SET current_status = ?, current_checksum = COALESCE(?, current_checksum), "
                f"{ts_col} = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE migration_number = ?",
                [status, checksum, migration_number]
            )
        else:
            conn.execute(
                f"INSERT INTO migration_state (migration_number, current_status, current_checksum, {ts_col}) "
                f"VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                [migration_number, status, checksum]
            )

    def apply_migration(self, migration_number: int, migration_name: str) -> bool:
        """Apply single migration (transaction-safe)"""
        logger.info(f"Applying migration {migration_number}: {migration_name}")

        try:
            sql_content = self.read_migration_sql(migration_number)
            checksum = self.get_checksum(migration_number)

            conn = duckdb.connect(str(self.db_path))

            # Begin transaction
            conn.execute("BEGIN TRANSACTION")

            try:
                # Check if already applied (a ROLLED_BACK row may be re-applied)
                existing = conn.execute(
                    "SELECT id, status FROM migrations WHERE migration_number = ?",
                    [migration_number]
                ).fetchall()

                if existing and existing[0][1] == 'APPLIED':
                    logger.warning(f"Migration {migration_number} already applied")
                    conn.execute("ROLLBACK")
                    return False

                # Execute migration SQL
                conn.execute(sql_content)

                # Record migration
                if existing:
                    conn.execute(
                        "UPDATE migrations SET status = 'APPLIED', checksum = ?, applied_at = CURRENT_TIMESTAMP "
                        "WHERE migration_number = ?",
                        [checksum, migration_number]
                    )
                else:
                    conn.execute(
                        "INSERT INTO migrations (migration_number, name, status, checksum) VALUES (?, ?, 'APPLIED', ?)",
                        [migration_number, migration_name, checksum]
                    )
                self._sync_state(conn, migration_number, 'APPLIED', checksum)

                conn.execute("COMMIT")
                logger.info(f"Migration {migration_number} applied successfully")
                return True

            except Exception as e:
                conn.execute("ROLLBACK")
                logger.error(f"Migration {migration_number} failed: {e}")
                raise
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Failed to apply migration {migration_number}: {e}")
            raise

    def rollback_migration(self, migration_number: int) -> bool:
        """Rollback single migration (reverse SQL)"""
        logger.info(f"Rolling back migration {migration_number}")

        try:
            status = self.get_migration_status(migration_number)
            if not status:
                logger.warning(f"Migration {migration_number} not applied, nothing to rollback")
                return False

            # Read rollback SQL (0001_rollback.sql, etc.)
            rollback_file = self.migrations_dir / f"{migration_number:04d}_rollback.sql"
            if not rollback_file.exists():
                raise FileNotFoundError(f"Rollback file not found: {rollback_file}")

            with open(rollback_file, 'r') as f:
                rollback_sql = f.read()

            conn = duckdb.connect(str(self.db_path))

            try:
                conn.execute("BEGIN TRANSACTION")

                # Execute rollback SQL
                conn.execute(rollback_sql)

                # Mark as rolled back
                conn.execute(
                    "UPDATE migrations SET status = 'ROLLED_BACK' WHERE migration_number = ?",
                    [migration_number]
                )
                self._sync_state(conn, migration_number, 'ROLLED_BACK', None)

                conn.execute("COMMIT")
                logger.info(f"Migration {migration_number} rolled back successfully")
                return True

            except Exception as e:
                conn.execute("ROLLBACK")
                logger.error(f"Rollback failed for migration {migration_number}: {e}")
                raise
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Failed to rollback migration {migration_number}: {e}")
            raise

    def apply_all_pending(self, target_migration: Optional[int] = None) -> List[int]:
        """Apply all pending migrations up to target (or all if None)"""
        applied = self.get_applied_migrations()

        # Scan for available migrations
        available = set()
        for sql_file in self.migrations_dir.glob("*.sql"):
            if not sql_file.name.endswith("_rollback.sql"):
                parts = sql_file.stem.split("_")
                if parts[0].isdigit():
                    available.add(int(parts[0]))

        # Determine which to apply
        to_apply = sorted([m for m in available if m not in applied])
        if target_migration:
            to_apply = [m for m in to_apply if m <= target_migration]

        results = []
        for migration_num in to_apply:
            sql_file = self._forward_file(migration_num)
            migration_name = sql_file.stem.replace(f"{migration_num:04d}_", "")

            if self.apply_migration(migration_num, migration_name):
                results.append(migration_num)

        return results

    def status(self) -> Dict[str, Any]:
        """Get current database migration status"""
        self.init_migrations_table()
        applied = self.get_applied_migrations()

        available = set()
        for sql_file in self.migrations_dir.glob("*.sql"):
            if not sql_file.name.endswith("_rollback.sql"):
                parts = sql_file.stem.split("_")
                if parts[0].isdigit():
                    available.add(int(parts[0]))

        return {
            'db_path': str(self.db_path),
            'applied_migrations': applied,
            'available_migrations': sorted(available),
            'pending_migrations': sorted([m for m in available if m not in applied]),
            'latest_applied': max(applied) if applied else 0
        }


def main():
    """CLI for migration management"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Database Migration Manager')
    parser.add_argument('--db', default='flip_flop.duckdb', help='Database path')
    parser.add_argument('--migrations-dir', default='migrations', help='Migrations directory')
    parser.add_argument('command', choices=['status', 'apply', 'rollback'], help='Command')
    parser.add_argument('--migration', type=int, help='Migration number (for apply/rollback)')
    parser.add_argument('--to', type=int, help='Target migration number (for apply)')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    mf = MigrationFramework(args.db, args.migrations_dir)

    if args.command == 'status':
        status = mf.status()
        print(json.dumps(status, indent=2, default=str))

    elif args.command == 'apply':
        if args.to:
            applied = mf.apply_all_pending(args.to)
            print(f"Applied migrations: {applied}")
        elif args.migration:
            name = f"migration_{args.migration:04d}"
            mf.apply_migration(args.migration, name)
            print(f"Applied migration {args.migration}")
        else:
            applied = mf.apply_all_pending()
            print(f"Applied migrations: {applied}")

    elif args.command == 'rollback':
        if not args.migration:
            print("--migration required for rollback")
            sys.exit(1)
        mf.rollback_migration(args.migration)
        print(f"Rolled back migration {args.migration}")


if __name__ == '__main__':
    main()
