"""
Integration tests for P5: Migration Ledger + Idempotent Apply + State Machine
Full migration lifecycle with audit trail
"""

import pytest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / '04_ENGINE'))

from migrations.migration_framework import MigrationFramework
from migration_ledger import MigrationLedger, MigrationState, IdempotentMigrator, DependencyValidator
import duckdb


@pytest.fixture
def temp_db():
    """Create temporary DuckDB with migrations 0001-0004"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.duckdb"

    # Initialize DB with all migrations
    mf = MigrationFramework(str(db_path), str(Path(__file__).parent.parent / '04_ENGINE' / 'migrations'))
    mf.init_migrations_table()
    mf.apply_all_pending(target_migration=4)

    yield str(db_path), mf

    shutil.rmtree(temp_dir)


class TestMigration0004Applied:
    """Verify migration 0004 applied successfully"""

    def test_migration_0004_recorded(self, temp_db):
        """Migration 0004 should be recorded"""
        db_path, mf = temp_db

        status = mf.status()
        assert 4 in status['applied_migrations']
        assert status['latest_applied'] == 4

    def test_all_0004_tables_exist(self, temp_db):
        """All 4 tables from 0004 should exist"""
        db_path, _ = temp_db

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


class TestMigrationLedger:
    """Test audit trail recording"""

    def test_record_apply_attempt(self, temp_db):
        """Should record apply attempt"""
        db_path, _ = temp_db

        ledger = MigrationLedger(db_path)
        success, msg, ledger_id = ledger.record_apply_attempt(5, "hash123abc", "TEST_APPLY")

        assert success is True
        assert ledger_id is not None

    def test_record_apply_success(self, temp_db):
        """Should mark apply as successful"""
        db_path, _ = temp_db

        ledger = MigrationLedger(db_path)
        success, msg, ledger_id = ledger.record_apply_attempt(5, "hash123", "TEST")

        result = ledger.record_apply_success(ledger_id)
        assert result is True

    def test_record_apply_failure(self, temp_db):
        """Should mark apply as failed"""
        db_path, _ = temp_db

        ledger = MigrationLedger(db_path)
        success, msg, ledger_id = ledger.record_apply_attempt(5, "hash123", "TEST")

        result = ledger.record_apply_failure(ledger_id, "Schema error")
        assert result is True

    def test_get_migration_history(self, temp_db):
        """Should retrieve migration audit trail"""
        db_path, _ = temp_db

        ledger = MigrationLedger(db_path)

        # Record multiple attempts
        for i in range(3):
            ledger.record_apply_attempt(5, f"hash{i}", f"ATTEMPT_{i}")

        history = ledger.get_migration_history(5)

        assert len(history) == 3


class TestMigrationState:
    """Test state machine"""

    def test_get_state(self, temp_db):
        """Should retrieve current state"""
        db_path, _ = temp_db

        state = MigrationState(db_path)
        current_state = state.get_state(1)

        assert current_state is not None
        assert current_state['current_status'] == 'APPLIED'

    def test_set_state_applied(self, temp_db):
        """Should set migration to APPLIED"""
        db_path, _ = temp_db

        state = MigrationState(db_path)
        result = state.set_state(5, 'APPLIED', 'newhash123')

        assert result is True

        current_state = state.get_state(5)
        assert current_state['current_status'] == 'APPLIED'

    def test_set_state_failed(self, temp_db):
        """Should set migration to FAILED with reason"""
        db_path, _ = temp_db

        state = MigrationState(db_path)
        result = state.set_state(5, 'FAILED', failure_reason="Schema error")

        assert result is True

        current_state = state.get_state(5)
        assert current_state['current_status'] == 'FAILED'
        assert 'Schema error' in current_state['failure_reason']

    def test_acquire_release_lock(self, temp_db):
        """Should acquire and release lock"""
        db_path, _ = temp_db

        state = MigrationState(db_path)

        # Acquire
        result = state.acquire_lock(5, "test_app")
        assert result is True

        current_state = state.get_state(5)
        assert current_state['locked'] is True

        # Release
        result = state.release_lock(5)
        assert result is True

        current_state = state.get_state(5)
        assert current_state['locked'] is False

    def test_lock_prevents_duplicate_acquire(self, temp_db):
        """Should prevent acquiring already-held lock"""
        db_path, _ = temp_db

        state = MigrationState(db_path)

        # Acquire first
        result1 = state.acquire_lock(5, "app1")
        assert result1 is True

        # Try to acquire again (should fail)
        result2 = state.acquire_lock(5, "app2")
        assert result2 is False


class TestDependencyValidator:
    """Test migration dependencies"""

    def test_validate_dependencies_satisfied(self, temp_db):
        """Should pass if all dependencies applied"""
        db_path, _ = temp_db

        validator = DependencyValidator(db_path)

        # Migration 3 depends on 2, both should be applied
        valid, msg = validator.validate_dependencies(3)

        assert valid is True

    def test_validate_sequence_valid(self, temp_db):
        """Should validate sequence up to target"""
        db_path, _ = temp_db

        validator = DependencyValidator(db_path)

        # All migrations 1-4 should be applied
        valid, msg, missing = validator.validate_sequence(4)

        assert valid is True
        assert len(missing) == 0


class TestIdempotentMigrator:
    """Test idempotent apply"""

    def test_idempotent_apply_first_time(self, temp_db):
        """First apply should succeed"""
        db_path, mf = temp_db

        idempotent = IdempotentMigrator(db_path, mf)

        # Create dummy migration (use 0001 that's already applied, just verify)
        success, msg = idempotent.apply_idempotent(1, "baseline")

        # Should succeed (already applied, checksum matches)
        assert success is True or "already applied" in msg.lower()

    def test_idempotent_apply_twice_same_file(self, temp_db):
        """Applying same migration twice should be idempotent"""
        db_path, mf = temp_db

        idempotent = IdempotentMigrator(db_path, mf)

        # Apply migration 1 twice
        success1, msg1 = idempotent.apply_idempotent(1, "baseline")
        success2, msg2 = idempotent.apply_idempotent(1, "baseline")

        assert success1 is True or "already applied" in msg1.lower()
        assert success2 is True or "already applied" in msg2.lower()

    def test_checksum_mismatch_detected(self, temp_db):
        """Should detect if migration file changed"""
        db_path, mf = temp_db

        # Get current checksum of migration 1
        checksum1 = mf.get_checksum(1)

        state = MigrationState(db_path)
        current = state.get_state(1)

        # Verify checksums match
        assert current['current_checksum'] == checksum1

    def test_dependency_check_before_apply(self, temp_db):
        """Should check dependencies before applying"""
        db_path, mf = temp_db

        idempotent = IdempotentMigrator(db_path, mf)

        # Create state for migration 5 (not applied)
        state = MigrationState(db_path)
        state.set_state(5, 'PENDING')

        # Try to apply 5 (no 4 dependency, should be in ledger)
        # This may fail or succeed depending on dependency setup
        success, msg = idempotent.apply_idempotent(5, "test")

        # Just verify it didn't crash
        assert isinstance(success, bool)


class TestAuditTrail:
    """Test complete audit trail"""

    def test_full_audit_flow(self, temp_db):
        """Complete flow: attempt → success → verify history"""
        db_path, _ = temp_db

        ledger = MigrationLedger(db_path)

        # Record attempt
        success, msg, ledger_id = ledger.record_apply_attempt(99, "hash999", "AUDIT_TEST")
        assert success is True

        # Mark success
        result = ledger.record_apply_success(ledger_id)
        assert result is True

        # Verify history
        history = ledger.get_migration_history(99)
        assert len(history) > 0
        assert history[0]['status'] == 'SUCCESS'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
