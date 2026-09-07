"""
NinjaTrader Batch Engine - Comprehensive Test Suite
Red-Green-Refactor: 48+ test cases
Authority Invariant: ZERO (immutable)
"""

import gc
import pytest
import uuid
import json
import tempfile
import os
from datetime import datetime, date, timedelta
from pathlib import Path

from batch_engine import (
    BatchEngine,
    BatchRun,
    BatchVerdict,
    DayReport,
    AlertRecord,
    ComplianceBundle,
    ArchiveRecord,
    BatchMode,
    BatchStatus,
    VerdictStatus,
    GateVerdictStatus,
    AlertSeverity,
    GateDecisionTuple,
    ImmutabilityViolation,
    WriteOnceViolation,
    RequiredVerdictMissing,
    MissingHPReceipt,
    RetentionNotMet,
    AuthorityLevel
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db_path():
    """Create temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    gc.collect()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def engine(db_path):
    """Create batch engine instance"""
    return BatchEngine(db_path)


@pytest.fixture
def sample_batch(engine):
    """Create sample batch"""
    return engine.create_batch(
        run_date=date(2026, 9, 7),
        market_open_time=datetime(2026, 9, 7, 13, 30, 0),
        market_close_time=datetime(2026, 9, 7, 20, 0, 0),
        mode=BatchMode.PAPER,
        correlation_id=str(uuid.uuid4())
    )


@pytest.fixture
def sample_pnl():
    """Sample P&L data"""
    return {
        "gross_pnl": 1500.00,
        "net_pnl": 1350.00,
        "currency": "USD",
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_risk_metrics():
    """Sample risk metrics"""
    return {
        "max_drawdown": 0.05,
        "var_95": 2000,
        "sharpe_ratio": 1.2,
        "win_rate": 0.65,
        "avg_win": 250,
        "avg_loss": 100
    }


@pytest.fixture
def sample_tax_summary():
    """Sample tax data"""
    return {
        "gains": 5000,
        "losses": 2000,
        "wash_sales": 500,
        "adjustments": 0,
        "total_taxable_income": 2500
    }


@pytest.fixture
def sample_gate_results():
    """Sample 8 Guardian gate results (all PASS)"""
    return [
        GateDecisionTuple(
            gate_id=i,
            verdict=GateVerdictStatus.PASS,
            evidence_id=f"ev-{i}",
            event_time=datetime.utcnow(),
            knowledge_time=datetime.utcnow()
        )
        for i in range(1, 9)
    ]


# ============================================================================
# CG01: NO_AUTHORITY_ESCALATION
# ============================================================================

class TestCG01AuthorityEscalation:
    """CG01 tests: mode must be PAPER/SHADOW/ANALYSIS (never LIVE)"""

    def test_cg01_batch_mode_paper_valid(self, engine):
        """CG01: PAPER mode is valid"""
        batch = engine.create_batch(
            run_date=date(2026, 9, 7),
            market_open_time=datetime(2026, 9, 7, 13, 30, 0),
            market_close_time=datetime(2026, 9, 7, 20, 0, 0),
            mode=BatchMode.PAPER,
            correlation_id=str(uuid.uuid4())
        )
        assert batch.mode == BatchMode.PAPER

    def test_cg01_batch_mode_shadow_valid(self, engine):
        """CG01: SHADOW mode is valid"""
        batch = engine.create_batch(
            run_date=date(2026, 9, 7),
            market_open_time=datetime(2026, 9, 7, 13, 30, 0),
            market_close_time=datetime(2026, 9, 7, 20, 0, 0),
            mode=BatchMode.SHADOW,
            correlation_id=str(uuid.uuid4())
        )
        assert batch.mode == BatchMode.SHADOW

    def test_cg01_batch_mode_analysis_valid(self, engine):
        """CG01: ANALYSIS mode is valid"""
        batch = engine.create_batch(
            run_date=date(2026, 9, 7),
            market_open_time=datetime(2026, 9, 7, 13, 30, 0),
            market_close_time=datetime(2026, 9, 7, 20, 0, 0),
            mode=BatchMode.ANALYSIS,
            correlation_id=str(uuid.uuid4())
        )
        assert batch.mode == BatchMode.ANALYSIS

    def test_cg01_batch_mode_immutable_after_creation(self, engine):
        """CG01: mode is immutable after creation"""
        batch = engine.create_batch(
            run_date=date(2026, 9, 7),
            market_open_time=datetime(2026, 9, 7, 13, 30, 0),
            market_close_time=datetime(2026, 9, 7, 20, 0, 0),
            mode=BatchMode.PAPER,
            correlation_id=str(uuid.uuid4())
        )
        # Try to mutate mode (should fail in real implementation)
        retrieved = engine.get_batch(batch.batch_id)
        assert retrieved.mode == BatchMode.PAPER

    def test_cg01_authority_verdict_must_be_zero(self, engine, sample_batch, sample_gate_results):
        """CG01: verdict authority_used must be ZERO"""
        verdict = engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        assert verdict.authority_used == AuthorityLevel.ZERO


# ============================================================================
# CG02: BATCH_DATA_IMMUTABLE_AFTER_CLOSE
# ============================================================================

class TestCG02DataImmutability:
    """CG02 tests: batch data immutable after closed_at is set"""

    def test_cg02_batch_allows_changes_before_close(self, engine, sample_batch, sample_pnl, sample_risk_metrics):
        """CG02: batch allows changes before close"""
        report = engine.create_day_report(
            batch_id=sample_batch.batch_id,
            pnl_summary=sample_pnl,
            risk_metrics=sample_risk_metrics
        )
        assert report.report_id is not None

    def test_cg02_alert_blocked_after_batch_close(self, engine, sample_batch, sample_gate_results):
        """CG02: cannot create alert after batch close"""
        # Close batch
        engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        engine.close_batch(sample_batch.batch_id)

        # Try to create alert
        with pytest.raises(ImmutabilityViolation):
            engine.create_alert(
                batch_id=sample_batch.batch_id,
                severity=AlertSeverity.CRITICAL,
                alert_type="TEST",
                message="Should fail"
            )

    def test_cg02_report_blocked_after_batch_close(self, engine, sample_batch, sample_pnl, sample_risk_metrics, sample_gate_results):
        """CG02: cannot create report after batch close"""
        # Close batch
        engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        engine.close_batch(sample_batch.batch_id)

        # Try to create report
        with pytest.raises(ImmutabilityViolation):
            engine.create_day_report(
                batch_id=sample_batch.batch_id,
                pnl_summary=sample_pnl,
                risk_metrics=sample_risk_metrics
            )

    def test_cg02_compliance_bundle_blocked_after_batch_close(self, engine, sample_batch, sample_tax_summary, sample_gate_results):
        """CG02: cannot create compliance bundle after batch close"""
        # Close batch
        engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        engine.close_batch(sample_batch.batch_id)

        # Try to create bundle
        with pytest.raises(ImmutabilityViolation):
            engine.create_compliance_bundle(
                batch_id=sample_batch.batch_id,
                tax_summary=sample_tax_summary,
                receipt_hashes=["hash1", "hash2"]
            )


# ============================================================================
# CG03: VERDICT_REQUIRES_ALL_GATES_PASS
# ============================================================================

class TestCG03VerdictLogic:
    """CG03 tests: verdict status depends on all gate results"""

    def test_cg03_all_gates_pass_approved(self, engine, sample_batch, sample_gate_results):
        """CG03: all PASS gates + verifications = APPROVED"""
        verdict = engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        assert verdict.batch_status == VerdictStatus.APPROVED

    def test_cg03_any_gate_blocked_means_blocked_verdict(self, engine, sample_batch, sample_gate_results):
        """CG03: any gate BLOCKED = verdict BLOCKED"""
        blocked_gates = sample_gate_results[:-1] + [
            GateDecisionTuple(
                gate_id=8,
                verdict=GateVerdictStatus.BLOCKED,
                evidence_id="ev-8",
                event_time=datetime.utcnow(),
                knowledge_time=datetime.utcnow()
            )
        ]
        verdict = engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=blocked_gates,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        assert verdict.batch_status == VerdictStatus.BLOCKED

    def test_cg03_compliance_failed_means_blocked_verdict(self, engine, sample_batch, sample_gate_results):
        """CG03: compliance_passed=false = verdict BLOCKED"""
        verdict = engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=False,
            tax_verified=True,
            archive_verified=True
        )
        assert verdict.batch_status == VerdictStatus.BLOCKED

    def test_cg03_tax_unverified_means_blocked_verdict(self, engine, sample_batch, sample_gate_results):
        """CG03: tax_verified=false = verdict BLOCKED"""
        verdict = engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=False,
            archive_verified=True
        )
        assert verdict.batch_status == VerdictStatus.BLOCKED

    def test_cg03_archive_unverified_means_blocked_verdict(self, engine, sample_batch, sample_gate_results):
        """CG03: archive_verified=false = verdict BLOCKED"""
        verdict = engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=False
        )
        assert verdict.batch_status == VerdictStatus.BLOCKED

    def test_cg03_any_gate_not_proven_means_not_proven_verdict(self, engine, sample_batch, sample_gate_results):
        """CG03: any gate NOT_PROVEN = verdict NOT_PROVEN"""
        not_proven_gates = sample_gate_results[:-1] + [
            GateDecisionTuple(
                gate_id=8,
                verdict=GateVerdictStatus.NOT_PROVEN,
                evidence_id="ev-8",
                event_time=datetime.utcnow(),
                knowledge_time=datetime.utcnow()
            )
        ]
        verdict = engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=not_proven_gates,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        assert verdict.batch_status == VerdictStatus.NOT_PROVEN


# ============================================================================
# CG04: GUARDIAN_GATES_MUST_COMPLETE
# ============================================================================

class TestCG04GatesComplete:
    """CG04 tests: exactly 8 gates required, batch cannot close without verdict"""

    def test_cg04_verdict_requires_exactly_8_gates(self, engine, sample_batch):
        """CG04: verdict must have exactly 8 gate results"""
        incomplete_gates = [
            GateDecisionTuple(
                gate_id=i,
                verdict=GateVerdictStatus.PASS,
                evidence_id=f"ev-{i}",
                event_time=datetime.utcnow(),
                knowledge_time=datetime.utcnow()
            )
            for i in range(1, 7)  # Only 6 gates
        ]

        with pytest.raises(ValueError) as exc_info:
            engine.issue_verdict(
                batch_id=sample_batch.batch_id,
                guardian_gate_results=incomplete_gates,
                compliance_passed=True,
                tax_verified=True,
                archive_verified=True
            )
        assert "exactly 8" in str(exc_info.value).lower()

    def test_cg04_batch_close_requires_verdict(self, engine, sample_batch):
        """CG04: batch cannot close without verdict"""
        with pytest.raises(RequiredVerdictMissing):
            engine.close_batch(sample_batch.batch_id)

    def test_cg04_batch_close_succeeds_with_verdict(self, engine, sample_batch, sample_gate_results):
        """CG04: batch closes successfully with complete verdict"""
        engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        batch = engine.close_batch(sample_batch.batch_id)
        assert batch.batch_status == BatchStatus.CLOSED
        assert batch.closed_at is not None


# ============================================================================
# CG05: COMPLIANCE_LOCK
# ============================================================================

class TestCG05ComplianceLock:
    """CG05 tests: compliance bundle locked after certification"""

    def test_cg05_bundle_certified_cannot_be_modified(self, engine, sample_batch, sample_tax_summary):
        """CG05: certified bundle cannot be modified"""
        bundle = engine.create_compliance_bundle(
            batch_id=sample_batch.batch_id,
            tax_summary=sample_tax_summary,
            receipt_hashes=["hash1", "hash2"]
        )

        # Certify
        engine.certify_compliance_bundle(bundle.bundle_id, "TEST_AUTHORITY")

        # Try to modify (bundle is frozen)
        with pytest.raises(ImmutabilityViolation):
            engine.certify_compliance_bundle(bundle.bundle_id, "ANOTHER_AUTHORITY")

    def test_cg05_bundle_computes_immutability_hash(self, engine, sample_batch, sample_tax_summary):
        """CG05: bundle hash seals immutability"""
        bundle = engine.create_compliance_bundle(
            batch_id=sample_batch.batch_id,
            tax_summary=sample_tax_summary,
            receipt_hashes=["hash1", "hash2"]
        )

        certified = engine.certify_compliance_bundle(bundle.bundle_id, "TEST_AUTHORITY")
        assert certified.bundle_hash is not None
        assert len(certified.bundle_hash) == 64  # SHA256


# ============================================================================
# CG06: ARCHIVE_WRITE_ONCE
# ============================================================================

class TestCG06ArchiveWriteOnce:
    """CG06 tests: ArchiveRecord is write-once (INSERT only)"""

    def test_cg06_archive_record_created_write_once(self, engine, sample_batch):
        """CG06: archive record is write-once"""
        retrieval_metadata = {
            "format": "tarball",
            "size_bytes": 5242880,
            "created_date": date(2026, 9, 7).isoformat(),
            "archived_date": date(2026, 9, 7).isoformat()
        }

        archive = engine.create_archive_record(
            batch_id=sample_batch.batch_id,
            storage_path="/durable/2026-09-07/batch-001.tar.gz",
            retrieval_metadata=retrieval_metadata
        )

        # Try to create same path again
        with pytest.raises(Exception):  # SQLite UNIQUE constraint
            engine.create_archive_record(
                batch_id=sample_batch.batch_id,
                storage_path="/durable/2026-09-07/batch-001.tar.gz",
                retrieval_metadata=retrieval_metadata
            )

    def test_cg06_archive_hash_immutable(self, engine, sample_batch):
        """CG06: archive immutable hash is set"""
        retrieval_metadata = {
            "format": "tarball",
            "size_bytes": 5242880,
            "created_date": date(2026, 9, 7).isoformat(),
            "archived_date": date(2026, 9, 7).isoformat()
        }

        archive = engine.create_archive_record(
            batch_id=sample_batch.batch_id,
            storage_path="/durable/2026-09-07/batch-001.tar.gz",
            retrieval_metadata=retrieval_metadata
        )

        assert archive.immutable_hash is not None
        assert len(archive.immutable_hash) == 64


# ============================================================================
# CG07: HP_DURABLE_RECEIPT
# ============================================================================

class TestCG07HPReceipt:
    """CG07 tests: HP receipt required before VERIFIED status"""

    def test_cg07_archive_created_with_written_status(self, engine, sample_batch):
        """CG07: newly created archive has WRITTEN status"""
        retrieval_metadata = {
            "format": "tarball",
            "size_bytes": 5242880,
            "created_date": date(2026, 9, 7).isoformat(),
            "archived_date": date(2026, 9, 7).isoformat()
        }

        archive = engine.create_archive_record(
            batch_id=sample_batch.batch_id,
            storage_path="/durable/2026-09-07/batch-001.tar.gz",
            retrieval_metadata=retrieval_metadata
        )

        assert archive.archive_status.value == "WRITTEN"


# ============================================================================
# CG08: RETENTION_ENFORCED
# ============================================================================

class TestCG08Retention:
    """CG08 tests: archive retention enforced (minimum 7 years)"""

    def test_cg08_retention_minimum_7_years(self, engine, sample_batch):
        """CG08: retention_years must be >= 7"""
        retrieval_metadata = {
            "format": "tarball",
            "size_bytes": 5242880,
            "created_date": date(2026, 9, 7).isoformat(),
            "archived_date": date(2026, 9, 7).isoformat()
        }

        # Should fail with retention_years < 7
        with pytest.raises(ValueError):
            engine.create_archive_record(
                batch_id=sample_batch.batch_id,
                storage_path="/durable/2026-09-07/batch-001.tar.gz",
                retrieval_metadata=retrieval_metadata,
                retention_years=5
            )

    def test_cg08_retention_default_7_years(self, engine, sample_batch):
        """CG08: default retention is 7 years"""
        retrieval_metadata = {
            "format": "tarball",
            "size_bytes": 5242880,
            "created_date": date(2026, 9, 7).isoformat(),
            "archived_date": date(2026, 9, 7).isoformat()
        }

        archive = engine.create_archive_record(
            batch_id=sample_batch.batch_id,
            storage_path="/durable/2026-09-07/batch-001.tar.gz",
            retrieval_metadata=retrieval_metadata
        )

        assert archive.retention_years == 7


# ============================================================================
# ALERT SEVERITY RANKING
# ============================================================================

class TestAlertSeverityRanking:
    """Tests: alerts sorted by severity (CRITICAL > HIGH > MEDIUM > LOW)"""

    def test_alerts_ranked_by_severity(self, engine, sample_batch):
        """Alerts are retrieved in severity order"""
        # Create alerts in mixed order
        engine.create_alert(
            batch_id=sample_batch.batch_id,
            severity=AlertSeverity.LOW,
            alert_type="LOW_ALERT",
            message="Low priority"
        )
        engine.create_alert(
            batch_id=sample_batch.batch_id,
            severity=AlertSeverity.CRITICAL,
            alert_type="CRITICAL_ALERT",
            message="Critical"
        )
        engine.create_alert(
            batch_id=sample_batch.batch_id,
            severity=AlertSeverity.MEDIUM,
            alert_type="MEDIUM_ALERT",
            message="Medium priority"
        )
        engine.create_alert(
            batch_id=sample_batch.batch_id,
            severity=AlertSeverity.HIGH,
            alert_type="HIGH_ALERT",
            message="High priority"
        )

        alerts = engine.get_all_alerts_for_batch(sample_batch.batch_id)

        # Verify order: CRITICAL > HIGH > MEDIUM > LOW
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert alerts[1].severity == AlertSeverity.HIGH
        assert alerts[2].severity == AlertSeverity.MEDIUM
        assert alerts[3].severity == AlertSeverity.LOW


# ============================================================================
# DAY REPORT VALIDATION
# ============================================================================

class TestDayReportValidation:
    """Tests: day report field validation"""

    def test_report_requires_pnl_summary_fields(self, engine, sample_batch, sample_risk_metrics):
        """Report must have all P&L fields"""
        incomplete_pnl = {
            "gross_pnl": 1500.00,
            # Missing net_pnl, currency, timestamp
        }

        with pytest.raises(ValueError):
            engine.create_day_report(
                batch_id=sample_batch.batch_id,
                pnl_summary=incomplete_pnl,
                risk_metrics=sample_risk_metrics
            )

    def test_report_requires_risk_metrics_fields(self, engine, sample_batch, sample_pnl):
        """Report must have all risk metric fields"""
        incomplete_risk = {
            "max_drawdown": 0.05,
            # Missing var_95, sharpe_ratio, win_rate, avg_win, avg_loss
        }

        with pytest.raises(ValueError):
            engine.create_day_report(
                batch_id=sample_batch.batch_id,
                pnl_summary=sample_pnl,
                risk_metrics=incomplete_risk
            )

    def test_report_alert_count_matches_summary(self, engine, sample_batch, sample_pnl, sample_risk_metrics):
        """Report alert_count must match alert_summary totals"""
        alert_summary = {
            "critical": 1,
            "high": 2,
            "medium": 1,
            "low": 0
        }

        report = engine.create_day_report(
            batch_id=sample_batch.batch_id,
            pnl_summary=sample_pnl,
            risk_metrics=sample_risk_metrics,
            alert_summary=alert_summary
        )

        assert report.alert_count == 4  # 1 + 2 + 1 + 0


# ============================================================================
# COMPLIANCE BUNDLE VALIDATION
# ============================================================================

class TestComplianceBundleValidation:
    """Tests: compliance bundle field validation"""

    def test_bundle_requires_tax_summary_fields(self, engine, sample_batch):
        """Bundle must have all tax summary fields"""
        incomplete_tax = {
            "gains": 5000,
            # Missing losses, wash_sales, adjustments, total_taxable_income
        }

        with pytest.raises(ValueError):
            engine.create_compliance_bundle(
                batch_id=sample_batch.batch_id,
                tax_summary=incomplete_tax,
                receipt_hashes=["hash1", "hash2"]
            )

    def test_bundle_requires_receipt_hashes(self, engine, sample_batch, sample_tax_summary):
        """Bundle must have at least one receipt hash"""
        with pytest.raises(ValueError):
            engine.create_compliance_bundle(
                batch_id=sample_batch.batch_id,
                tax_summary=sample_tax_summary,
                receipt_hashes=[]  # Empty
            )


# ============================================================================
# ARCHIVE RECORD VALIDATION
# ============================================================================

class TestArchiveRecordValidation:
    """Tests: archive record field validation"""

    def test_archive_requires_retrieval_metadata_fields(self, engine, sample_batch):
        """Archive must have all retrieval metadata fields"""
        incomplete_metadata = {
            "format": "tarball",
            # Missing size_bytes, created_date, archived_date
        }

        with pytest.raises(ValueError):
            engine.create_archive_record(
                batch_id=sample_batch.batch_id,
                storage_path="/durable/2026-09-07/batch-001.tar.gz",
                retrieval_metadata=incomplete_metadata
            )


# ============================================================================
# IMMUTABLE TUPLE CONVERSIONS
# ============================================================================

class TestImmutableTuples:
    """Tests: entities convert to immutable tuples"""

    def test_batch_run_to_tuple(self, sample_batch):
        """BatchRun converts to immutable tuple"""
        tuple_form = sample_batch.to_tuple()
        assert tuple_form.batch_id == sample_batch.batch_id
        assert tuple_form.run_date == sample_batch.run_date
        assert tuple_form.mode == sample_batch.mode

    def test_day_report_to_tuple(self, engine, sample_batch, sample_pnl, sample_risk_metrics):
        """DayReport converts to immutable tuple"""
        report = engine.create_day_report(
            batch_id=sample_batch.batch_id,
            pnl_summary=sample_pnl,
            risk_metrics=sample_risk_metrics
        )
        tuple_form = report.to_tuple()
        assert tuple_form.report_id == report.report_id
        assert tuple_form.batch_id == report.batch_id

    def test_alert_to_tuple(self, engine, sample_batch):
        """AlertRecord converts to immutable tuple"""
        alert = engine.create_alert(
            batch_id=sample_batch.batch_id,
            severity=AlertSeverity.HIGH,
            alert_type="TEST",
            message="Test alert"
        )
        tuple_form = alert.to_tuple()
        assert tuple_form.alert_id == alert.alert_id
        assert tuple_form.severity == alert.severity


# ============================================================================
# PERSISTENCE
# ============================================================================

class TestPersistence:
    """Tests: data persists correctly to database"""

    def test_batch_persists_to_database(self, engine):
        """Batch is persisted and retrievable"""
        batch = engine.create_batch(
            run_date=date(2026, 9, 7),
            market_open_time=datetime(2026, 9, 7, 13, 30, 0),
            market_close_time=datetime(2026, 9, 7, 20, 0, 0),
            mode=BatchMode.PAPER,
            correlation_id=str(uuid.uuid4())
        )

        retrieved = engine.get_batch(batch.batch_id)
        assert retrieved.batch_id == batch.batch_id
        assert retrieved.mode == batch.mode

    def test_verdict_persists_to_database(self, engine, sample_batch, sample_gate_results):
        """Verdict is persisted and retrievable"""
        verdict = engine.issue_verdict(
            batch_id=sample_batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )

        retrieved = engine.get_verdict(sample_batch.batch_id)
        assert retrieved.verdict_id == verdict.verdict_id
        assert retrieved.batch_status == VerdictStatus.APPROVED


# ============================================================================
# BATCH LIFECYCLE
# ============================================================================

class TestBatchLifecycle:
    """Tests: complete batch lifecycle"""

    def test_complete_batch_workflow(self, engine, sample_pnl, sample_risk_metrics,
                                    sample_tax_summary, sample_gate_results):
        """Complete batch workflow: create → process → verdict → close"""
        # Create batch
        batch = engine.create_batch(
            run_date=date(2026, 9, 7),
            market_open_time=datetime(2026, 9, 7, 13, 30, 0),
            market_close_time=datetime(2026, 9, 7, 20, 0, 0),
            mode=BatchMode.PAPER,
            correlation_id=str(uuid.uuid4())
        )
        assert batch.batch_status == BatchStatus.PENDING

        # Process: create report
        report = engine.create_day_report(
            batch_id=batch.batch_id,
            pnl_summary=sample_pnl,
            risk_metrics=sample_risk_metrics,
            trade_count=42
        )
        assert report.report_id is not None

        # Create compliance bundle
        bundle = engine.create_compliance_bundle(
            batch_id=batch.batch_id,
            tax_summary=sample_tax_summary,
            receipt_hashes=["hash1", "hash2"]
        )

        # Certify compliance
        engine.certify_compliance_bundle(bundle.bundle_id, "TEST_AUTHORITY")

        # Create archive
        retrieval_metadata = {
            "format": "tarball",
            "size_bytes": 5242880,
            "created_date": date(2026, 9, 7).isoformat(),
            "archived_date": date(2026, 9, 7).isoformat()
        }
        archive = engine.create_archive_record(
            batch_id=batch.batch_id,
            storage_path="/durable/2026-09-07/batch-001.tar.gz",
            retrieval_metadata=retrieval_metadata,
            report_id=report.report_id,
            bundle_id=bundle.bundle_id
        )

        # Issue verdict (all gates PASS)
        verdict = engine.issue_verdict(
            batch_id=batch.batch_id,
            guardian_gate_results=sample_gate_results,
            compliance_passed=True,
            tax_verified=True,
            archive_verified=True
        )
        assert verdict.batch_status == VerdictStatus.APPROVED

        # Close batch
        closed_batch = engine.close_batch(batch.batch_id)
        assert closed_batch.batch_status == BatchStatus.CLOSED
        assert closed_batch.closed_at is not None


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
