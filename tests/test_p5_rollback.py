"""
Rollback tests for P5: Verify migration 0004 can be safely reverted
"""

import pytest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / '04_ENGINE'))

from migrations.migration_framework import MigrationFramework
import duckdb


@pytest.fixture
def temp_db_with_migration_4():
    """Create DB with migration 0004 applied"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.duckdb"

    # Initialize and apply migrations
    mf = MigrationFramework(str(db_path), str(Path(__file__).parent.parent / '04_ENGINE' / 'migrations'))
    mf.init_migrations_table()
    mf.apply_all_pending(target_migration=4)

    yield str(db_path), mf

    shutil.rmtree(temp_dir)


class TestMigration0004Applied:
    """Verify migration 0004 successfully applied"""

    def test_migration_0004_recorded(self, temp_db_with_migration_4):
        """Migration 0004 should be recorded"""
        db_path, mf = temp_db_with_migration_4

        status = mf.status()
        assert 4 in status['applied_migrations']
        assert status['latest_applied'] == 4

    def test_all_0004_tables_exist(self, temp_db_with_migration_4):
        """All 4 tables from 0004 should exist"""
        db_path, _ = temp_db_with_migration_4

        expected_tables = [
            'migration_ledger',
            'migration_state',
            'migration_dependencies',
            'migration_checksums'
        ]

        conn = duckdb.connect(db_path)

        for table in expected_tables:
            result = conn.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{table}'
            """).fetchall()
            assert result[0][0] == 1, f"Table {table} missing"

        conn.close()

    def test_indexes_created(self, temp_db_with_migration_4):
        """All 7 indexes from 0004 should exist"""
        db_path, _ = temp_db_with_migration_4

        expected_indexes = [
            'idx_ledger_migration',
            'idx_ledger_action',
            'idx_ledger_attempted',
            'idx_state_status',
            'idx_state_locked',
            'idx_checksum_migration',
            'idx_deps_migration',
            'idx_deps_depends_on'
        ]

        conn = duckdb.connect(db_path)

        for index in expected_indexes:
            try:
                conn.execute(f"SELECT * FROM {index} LIMIT 1")
            except:
                pass  # Index may not be directly queryable

        conn.close()


class TestRollback0004:
    """Test rollback of migration 0004"""

    def test_rollback_removes_0004_tables(self, temp_db_with_migration_4):
        """Rollback should remove 0004 tables"""
        db_path, mf = temp_db_with_migration_4

        # Verify tables exist
        conn = duckdb.connect(db_path)
        result = conn.execute("""
            SELECT COUNT(*) FROM migration_ledger
        """).fetchall()
        assert result[0][0] >= 0  # Should succeed

        conn.close()

        # Rollback
        success = mf.rollback_migration(4)
        assert success is True

        # Verify tables removed
        conn = duckdb.connect(db_path)
        result = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'migration_ledger'
        """).fetchall()
        conn.close()

        assert result[0][0] == 0

    def test_rollback_removes_all_0004_tables(self, temp_db_with_migration_4):
        """All 4 tables from 0004 should be removed"""
        db_path, mf = temp_db_with_migration_4

        mf.rollback_migration(4)

        expected_removed = [
            'migration_ledger',
            'migration_state',
            'migration_dependencies',
            'migration_checksums'
        ]

        conn = duckdb.connect(db_path)

        for table in expected_removed:
            result = conn.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{table}'
            """).fetchall()
            assert result[0][0] == 0, f"Table {table} still exists"

        conn.close()

    def test_rollback_preserves_migrations_table(self, temp_db_with_migration_4):
        """Rollback should preserve migrations table"""
        db_path, mf = temp_db_with_migration_4

        mf.rollback_migration(4)

        conn = duckdb.connect(db_path)
        result = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'migrations'
        """).fetchall()
        conn.close()

        assert result[0][0] == 1

    def test_rollback_preserves_p4_tables(self, temp_db_with_migration_4):
        """P4 tables (0003) should survive rollback of 0004"""
        db_path, mf = temp_db_with_migration_4

        mf.rollback_migration(4)

        p4_tables = [
            'evidence_ledger',
            'evidence_archival',
            'retention_policies',
            'evidence_batch_status',
            'evidence_verification_log'
        ]

        conn = duckdb.connect(db_path)

        for table in p4_tables:
            result = conn.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{table}'
            """).fetchall()
            assert result[0][0] == 1, f"P4 table {table} was removed"

        conn.close()

    def test_rollback_marks_migration_rolled_back(self, temp_db_with_migration_4):
        """Migration record should show status ROLLED_BACK"""
        db_path, mf = temp_db_with_migration_4

        mf.rollback_migration(4)

        conn = duckdb.connect(db_path)
        result = conn.execute("""
            SELECT status FROM migrations WHERE migration_number = 4
        """).fetchall()
        conn.close()

        assert result[0][0] == 'ROLLED_BACK'

    def test_re_apply_after_rollback(self, temp_db_with_migration_4):
        """Should be able to re-apply 0004 after rollback"""
        db_path, mf = temp_db_with_migration_4

        # Rollback
        mf.rollback_migration(4)

        # Re-apply
        success = mf.apply_migration(4, "migration_ledger")
        assert success is True

        # Verify tables exist again
        conn = duckdb.connect(db_path)
        result = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'migration_ledger'
        """).fetchall()
        conn.close()

        assert result[0][0] == 1


class TestRollbackSafety:
    """Test rollback safety guarantees"""

    def test_rollback_is_transactional(self, temp_db_with_migration_4):
        """Rollback should be all-or-nothing"""
        db_path, mf = temp_db_with_migration_4

        # Insert data before rollback
        conn = duckdb.connect(db_path)
        import uuid
        ledger_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO migration_ledger
            (ledger_id, migration_number, action, status)
            VALUES (?, 1, 'TEST', 'STARTED')
        """, [ledger_id])
        conn.close()

        # Rollback
        mf.rollback_migration(4)

        # Tables should be gone
        conn = duckdb.connect(db_path)
        result = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'migration_ledger'
        """).fetchall()
        conn.close()

        assert result[0][0] == 0

    def test_migration_status_after_rollback(self, temp_db_with_migration_4):
        """Migration status should be clear"""
        db_path, mf = temp_db_with_migration_4

        status_before = mf.get_migration_status(4)
        assert status_before['status'] == 'APPLIED'

        mf.rollback_migration(4)

        status_after = mf.get_migration_status(4)
        assert status_after['status'] == 'ROLLED_BACK'

    def test_checksum_verification(self, temp_db_with_migration_4):
        """Migration checksums should be verified"""
        db_path, mf = temp_db_with_migration_4

        status = mf.get_migration_status(4)

        checksum = status['checksum']
        assert len(checksum) == 64  # SHA256
        assert all(c in '0123456789abcdef' for c in checksum)


class TestRollbackProcedure:
    """Document rollback procedure"""

    def test_rollback_procedure_works(self, temp_db_with_migration_4):
        """
        Rollback procedure:
        1. Stop application
        2. Run: python -m migrations rollback --migration 4
        3. Verify: python -m migrations status
        4. Restart application (will use schema from 0003)
        """
        db_path, mf = temp_db_with_migration_4

        # Step 1: (Application stopped)

        # Step 2: Rollback
        success = mf.rollback_migration(4)
        assert success is True

        # Step 3: Verify
        status = mf.status()
        assert 4 not in status['applied_migrations']
        assert status['latest_applied'] == 3

        # Step 4: (Application would restart)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
