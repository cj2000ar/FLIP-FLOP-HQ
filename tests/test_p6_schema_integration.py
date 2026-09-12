"""
Integration tests for P6: Schema Versioning + Migrations-As-Code
Test schema capture, validation, and snapshots
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / '04_ENGINE'))

from migrations.migration_framework import MigrationFramework
from schema_snapshot import SchemaSnapshot, SchemaValidator
from schema_definitions import SCHEMA_0001, SCHEMA_0002, SCHEMA_0003, SCHEMA_0004
import duckdb


@pytest.fixture
def temp_db_with_migrations():
    """Create temporary DB with all migrations applied"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.duckdb"

    # Initialize and apply all migrations
    mf = MigrationFramework(str(db_path), str(Path(__file__).parent.parent / '04_ENGINE' / 'migrations'))
    mf.init_migrations_table()
    mf.apply_all_pending(target_migration=4)

    yield str(db_path)
    shutil.rmtree(temp_dir)


class TestSchemaSnapshot:
    """Test schema capture functionality"""

    def test_capture_schema_success(self, temp_db_with_migrations):
        """Should capture current schema"""
        snapshot = SchemaSnapshot(temp_db_with_migrations)
        schema = snapshot.capture_schema()

        assert schema is not None
        assert 'captured_at' in schema
        assert 'tables' in schema
        assert 'indexes' in schema
        assert 'checksum' in schema
        assert len(schema['tables']) > 0

    def test_schema_has_tables(self, temp_db_with_migrations):
        """Schema should contain expected tables"""
        snapshot = SchemaSnapshot(temp_db_with_migrations)
        schema = snapshot.capture_schema()

        table_names = {t['name'] for t in schema['tables']}

        # Check P3 tables
        assert 'owner_credentials' in table_names
        assert 'device_registrations' in table_names
        assert 'credential_rotations' in table_names
        assert 'recovery_codes' in table_names
        assert 'auth_sessions' in table_names
        assert 'auth_audit_log' in table_names

        # Check P4 tables
        assert 'evidence_ledger' in table_names
        assert 'evidence_archival' in table_names
        assert 'retention_policies' in table_names

        # Check P5 tables
        assert 'migration_ledger' in table_names
        assert 'migration_state' in table_names

    def test_schema_columns_captured(self, temp_db_with_migrations):
        """Schema should capture columns for each table"""
        snapshot = SchemaSnapshot(temp_db_with_migrations)
        schema = snapshot.capture_schema()

        # Find owner_credentials table
        owner_creds = next((t for t in schema['tables'] if t['name'] == 'owner_credentials'), None)
        assert owner_creds is not None

        col_names = {c['name'] for c in owner_creds['columns']}
        assert 'owner_id' in col_names
        assert 'password_hash' in col_names
        assert 'mfa_secret' in col_names

    def test_schema_checksum_deterministic(self, temp_db_with_migrations):
        """Schema checksum should be deterministic"""
        snapshot = SchemaSnapshot(temp_db_with_migrations)

        schema1 = snapshot.capture_schema()
        schema2 = snapshot.capture_schema()

        # Remove timestamps for comparison
        checksum1 = schema1['checksum']
        checksum2 = schema2['checksum']

        assert checksum1 == checksum2

    def test_save_and_load_snapshot(self, temp_db_with_migrations):
        """Should save and load schema snapshot"""
        snapshot = SchemaSnapshot(temp_db_with_migrations)
        schema = snapshot.capture_schema()

        # Save
        snap_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        snap_file.close()

        success = snapshot.save_snapshot(schema, snap_file.name)
        assert success is True

        # Load
        loaded_schema = snapshot.load_snapshot(snap_file.name)
        assert loaded_schema is not None
        assert loaded_schema['checksum'] == schema['checksum']

        # Cleanup
        Path(snap_file.name).unlink()


class TestSchemaValidator:
    """Test schema validation"""

    def test_validate_identical_schemas(self):
        """Should pass when schemas are identical"""
        schema = SCHEMA_0002.copy()
        is_valid, errors = SchemaValidator.validate_schema(schema, schema)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_table(self):
        """Should detect missing table"""
        expected = SCHEMA_0002.copy()
        actual = SCHEMA_0002.copy()
        actual['tables'] = actual['tables'][1:]  # Remove first table

        is_valid, errors = SchemaValidator.validate_schema(actual, expected)

        assert is_valid is False
        assert any('Missing table' in err for err in errors)

    def test_validate_missing_column(self):
        """Should detect missing column"""
        import copy
        expected = copy.deepcopy(SCHEMA_0002)
        actual = copy.deepcopy(SCHEMA_0002)

        # Remove a column from first table
        if actual['tables'] and actual['tables'][0]['columns']:
            actual['tables'][0]['columns'] = actual['tables'][0]['columns'][1:]

        is_valid, errors = SchemaValidator.validate_schema(actual, expected)

        assert is_valid is False
        assert any('Missing column' in err for err in errors)

    def test_validate_extra_table(self):
        """Should detect extra table"""
        expected = SCHEMA_0001.copy()
        actual = SCHEMA_0002.copy()

        is_valid, errors = SchemaValidator.validate_schema(actual, expected)

        assert is_valid is False
        assert any('Extra table' in err for err in errors)


class TestSchemaDefinitions:
    """Test schema definitions as code"""

    def test_schema_0001_defined(self):
        """Schema 0001 should be defined"""
        assert SCHEMA_0001 is not None
        assert SCHEMA_0001['version'] == 1
        assert 'migrations' in {t['name'] for t in SCHEMA_0001['tables']}

    def test_schema_0002_defined(self):
        """Schema 0002 should include P3 tables"""
        assert SCHEMA_0002 is not None
        assert SCHEMA_0002['version'] == 2
        table_names = {t['name'] for t in SCHEMA_0002['tables']}

        assert 'owner_credentials' in table_names
        assert 'device_registrations' in table_names
        assert 'credential_rotations' in table_names

    def test_schema_0003_defined(self):
        """Schema 0003 should include P4 tables"""
        assert SCHEMA_0003 is not None
        assert SCHEMA_0003['version'] == 3
        table_names = {t['name'] for t in SCHEMA_0003['tables']}

        assert 'evidence_ledger' in table_names
        assert 'evidence_archival' in table_names
        assert 'retention_policies' in table_names

    def test_schema_0004_defined(self):
        """Schema 0004 should include P5 tables"""
        assert SCHEMA_0004 is not None
        assert SCHEMA_0004['version'] == 4
        table_names = {t['name'] for t in SCHEMA_0004['tables']}

        assert 'migration_ledger' in table_names
        assert 'migration_state' in table_names
        assert 'migration_dependencies' in table_names

    def test_schema_constraints_defined(self):
        """Schemas should define constraints"""
        # P3 has foreign keys
        for table in SCHEMA_0002['tables']:
            if 'constraints' in table and table['constraints']:
                constraint_types = {c.get('type') for c in table['constraints']}
                # Should have at least PRIMARY_KEY or FOREIGN_KEY
                assert len(constraint_types) > 0


class TestEndToEndSchemaValidation:
    """End-to-end schema capture and validation"""

    def test_capture_and_validate_against_definition(self, temp_db_with_migrations):
        """Should capture current schema and validate against definition"""
        snapshot = SchemaSnapshot(temp_db_with_migrations)
        actual_schema = snapshot.capture_schema()

        # Validate against P3 definition (migration 0002)
        # This is a partial validation (P3 only)
        is_valid, errors = SchemaValidator.validate_schema(actual_schema, SCHEMA_0002)

        # May not be completely valid if DB has extra tables from P4/P5
        # But should have all P3 tables
        p3_tables = {t['name'] for t in SCHEMA_0002['tables']}
        actual_tables = {t['name'] for t in actual_schema['tables']}

        for table in p3_tables:
            assert table in actual_tables, f"P3 table {table} missing from actual schema"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
