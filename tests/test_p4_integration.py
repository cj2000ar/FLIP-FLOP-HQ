"""
Integration tests for P4: Evidence Retention + Sealing + Compliance
Full end-to-end evidence lifecycle flows
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / '04_ENGINE'))

from migrations.migration_framework import MigrationFramework
from evidence_sealing import EvidenceSealer, HashChain, EvidenceVerifier
from evidence_retention import RetentionPolicyManager, EvidenceArchiver, ComplianceExporter
import duckdb


@pytest.fixture
def temp_db():
    """Create temporary DuckDB with full schema (P3 + P4)"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.duckdb"

    # Initialize DB with migrations 0001-0003
    mf = MigrationFramework(str(db_path), str(Path(__file__).parent.parent / '04_ENGINE' / 'migrations'))
    mf.init_migrations_table()
    mf.apply_all_pending()

    # Setup test data
    conn = duckdb.connect(str(db_path))

    # Insert test owner
    conn.execute("""
        INSERT INTO owner_credentials (owner_id, password_hash, mfa_secret)
        VALUES ('owner1', 'hash123$abc', 'secret123')
    """)

    # Insert test audit events
    for i in range(50):
        conn.execute("""
            INSERT INTO auth_audit_log
            (log_id, event_type, owner_id, device_id, ip_address, status, reason, event_at)
            VALUES (?, 'LOGIN', 'owner1', 'device1', '192.168.1.1', 'SUCCESS', 'Normal login', CURRENT_TIMESTAMP)
        """, [f"log_{i:04d}"])

    conn.close()

    yield str(db_path)
    shutil.rmtree(temp_dir)


class TestMigration0003Applied:
    """Verify migration 0003 applied correctly"""

    def test_evidence_ledger_table_exists(self, temp_db):
        """evidence_ledger table should exist"""
        conn = duckdb.connect(temp_db)
        result = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'evidence_ledger'
        """).fetchall()
        conn.close()

        assert result[0][0] == 1

    def test_all_0003_tables_exist(self, temp_db):
        """All 5 tables from 0003 should exist"""
        expected_tables = [
            'evidence_ledger',
            'evidence_archival',
            'retention_policies',
            'evidence_batch_status',
            'evidence_verification_log'
        ]

        conn = duckdb.connect(temp_db)

        for table in expected_tables:
            result = conn.execute(f"""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = '{table}'
            """).fetchall()
            assert result[0][0] == 1, f"Table {table} missing"

        conn.close()

    def test_default_policies_initialized(self, temp_db):
        """Default retention policies should be initialized"""
        conn = duckdb.connect(temp_db)
        result = conn.execute("""
            SELECT COUNT(*) FROM retention_policies
        """).fetchall()
        conn.close()

        assert result[0][0] == 7  # 7 default policies


class TestBatchSealing:
    """Test batch sealing and hash chain"""

    def test_seal_batch_success(self, temp_db):
        """Should seal batch of events"""
        sealer = EvidenceSealer(temp_db)

        events = sealer.get_unsealed_events(limit=10)
        assert len(events) > 0

        success, msg, batch_data = sealer.seal_batch(events)

        assert success is True
        assert batch_data is not None
        assert 'batch_id' in batch_data
        assert 'batch_hash' in batch_data
        assert 'signature' in batch_data

    def test_hash_chain_created(self, temp_db):
        """Hash chain should link batches"""
        sealer = EvidenceSealer(temp_db)

        # Seal first batch
        events1 = sealer.get_unsealed_events(limit=10)
        success1, _, batch1 = sealer.seal_batch(events1)

        # Seal second batch
        events2 = sealer.get_unsealed_events(limit=10)
        success2, _, batch2 = sealer.seal_batch(events2)

        assert success1 and success2

        # Verify chain: batch2 should reference batch1 hash
        conn = duckdb.connect(temp_db)
        result = conn.execute("""
            SELECT batch_sequence, previous_batch_hash FROM evidence_ledger
            ORDER BY batch_sequence ASC
        """).fetchall()
        conn.close()

        assert len(result) == 2
        assert result[0][1] is None  # First batch has no previous
        assert result[1][1] == batch1['batch_hash']  # Second references first

    def test_seal_all_pending(self, temp_db):
        """Should seal all unsealed events"""
        sealer = EvidenceSealer(temp_db, batch_size=15)

        batches, events = sealer.seal_all_pending()

        assert batches > 0
        assert events >= 15  # At least one full batch

    def test_batch_hash_deterministic(self, temp_db):
        """Same events should produce same hash"""
        events = [
            {'log_id': '1', 'event_type': 'LOGIN', 'owner_id': 'o1', 'device_id': 'd1',
             'ip_address': '1.1.1.1', 'status': 'SUCCESS', 'reason': None, 'event_at': '2026-09-11T10:00:00'}
        ]

        hash1 = HashChain.compute_batch_hash(events)
        hash2 = HashChain.compute_batch_hash(events)

        assert hash1 == hash2


class TestChainVerification:
    """Test hash chain validation"""

    def test_verify_chain_valid(self, temp_db):
        """Valid chain should pass verification"""
        sealer = EvidenceSealer(temp_db)
        sealer.seal_all_pending()

        verifier = EvidenceVerifier(temp_db)
        is_valid, msg, count = verifier.verify_chain()

        assert is_valid is True
        assert count > 0

    def test_verify_single_batch(self, temp_db):
        """Single batch should verify"""
        sealer = EvidenceSealer(temp_db)
        events = sealer.get_unsealed_events(limit=10)
        success, msg, batch = sealer.seal_batch(events)

        verifier = EvidenceVerifier(temp_db)
        is_valid, msg = verifier.verify_batch(batch['batch_id'])

        assert is_valid is True


class TestRetentionPolicies:
    """Test retention policy management"""

    def test_get_default_policy(self, temp_db):
        """Should retrieve default policy"""
        manager = RetentionPolicyManager(temp_db)

        policy = manager.get_policy('LOGIN')

        assert policy is not None
        assert policy['retention_days'] == 365
        assert policy['archive_after_days'] == 90

    def test_set_custom_policy(self, temp_db):
        """Should set custom retention policy"""
        manager = RetentionPolicyManager(temp_db)

        success, msg = manager.set_policy('CUSTOM_EVENT', 60, 30, True, False)

        assert success is True

        policy = manager.get_policy('CUSTOM_EVENT')
        assert policy is not None
        assert policy['retention_days'] == 60

    def test_list_all_policies(self, temp_db):
        """Should list all policies"""
        manager = RetentionPolicyManager(temp_db)

        policies = manager.list_policies()

        assert len(policies) >= 7  # At least default policies


class TestEvidenceArchival:
    """Test batch archival and compression"""

    def test_archive_batch_success(self, temp_db):
        """Should archive batch"""
        sealer = EvidenceSealer(temp_db)
        events = sealer.get_unsealed_events(limit=10)
        success, msg, batch = sealer.seal_batch(events)

        archiver = EvidenceArchiver(temp_db)
        success, msg = archiver.archive_batch(batch['batch_id'])

        assert success is True

    def test_archive_batch_status_updated(self, temp_db):
        """Batch status should change to ARCHIVED"""
        sealer = EvidenceSealer(temp_db)
        events = sealer.get_unsealed_events(limit=10)
        success, msg, batch = sealer.seal_batch(events)

        archiver = EvidenceArchiver(temp_db)
        archiver.archive_batch(batch['batch_id'])

        conn = duckdb.connect(temp_db)
        result = conn.execute("""
            SELECT status FROM evidence_batch_status
            WHERE batch_id = ?
        """, [batch['batch_id']]).fetchall()
        conn.close()

        assert result[0][0] == 'ARCHIVED'


class TestComplianceExport:
    """Test compliance reporting and exports"""

    def test_export_owner_audit(self, temp_db):
        """Should export owner audit trail"""
        exporter = ComplianceExporter(temp_db)

        success, msg, events = exporter.export_owner_audit('owner1')

        assert success is True
        assert events is not None
        assert len(events) > 0

    def test_export_compliance_report(self, temp_db):
        """Should generate compliance report"""
        exporter = ComplianceExporter(temp_db)

        success, msg, report = exporter.export_compliance_report('SOC2')

        assert success is True
        assert report is not None
        assert 'metrics' in report
        assert 'login_attempts' in report['metrics']

    def test_compliance_report_structure(self, temp_db):
        """Compliance report should have required fields"""
        exporter = ComplianceExporter(temp_db)

        success, msg, report = exporter.export_compliance_report()

        assert 'report_type' in report
        assert 'generated_at' in report
        assert 'period_start' in report
        assert 'period_end' in report
        assert 'compliance_status' in report


class TestEndToEndFlow:
    """Complete evidence lifecycle flow"""

    def test_audit_seal_verify_archive_export(self, temp_db):
        """Full flow: events → seal → verify chain → archive → export"""
        # 1. Events inserted (done in fixture)
        conn = duckdb.connect(temp_db)
        event_count = conn.execute("""
            SELECT COUNT(*) FROM auth_audit_log
        """).fetchall()[0][0]
        conn.close()

        assert event_count > 0

        # 2. Seal batches
        sealer = EvidenceSealer(temp_db, batch_size=15)
        batches, total = sealer.seal_all_pending()
        assert batches > 0

        # 3. Verify chain
        verifier = EvidenceVerifier(temp_db)
        is_valid, msg, count = verifier.verify_chain()
        assert is_valid is True

        # 4. Archive batches
        archiver = EvidenceArchiver(temp_db)
        archived, failed = archiver.archive_expired_batches()
        # May or may not archive depending on dates

        # 5. Export compliance
        exporter = ComplianceExporter(temp_db)
        success, msg, report = exporter.export_compliance_report()
        assert success is True

        # 6. Export owner audit
        success, msg, audit = exporter.export_owner_audit('owner1')
        assert success is True
        assert len(audit) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
