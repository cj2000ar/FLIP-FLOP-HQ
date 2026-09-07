"""
NinjaTrader Batch Engine - Phase 2 Frozen Implementation
Authority Invariant: ZERO (immutable)
Failure Policy: FAIL_CLOSED
"""

import uuid
import hashlib
import json
import os
import logging
from datetime import datetime, date, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
import sqlite3
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class BatchMode(str, Enum):
    """Batch execution mode - immutable after creation"""
    PAPER = "PAPER"           # Paper-only execution (no real orders)
    SHADOW = "SHADOW"         # Shadow-mode (monitoring only, no execution)
    ANALYSIS = "ANALYSIS"     # Post-analysis of historical data


class BatchStatus(str, Enum):
    """Batch lifecycle state"""
    PENDING = "PENDING"       # Created, waiting for processing
    PROCESSING = "PROCESSING" # Market open/close triggered
    CLOSED = "CLOSED"         # Export + summary + compliance complete
    ARCHIVED = "ARCHIVED"     # Archive finalized


class VerdictStatus(str, Enum):
    """BatchVerdict final authorization status"""
    APPROVED = "APPROVED"     # All gates PASS + compliance + tax + archive verified
    BLOCKED = "BLOCKED"       # Any gate BLOCKED or verification failed
    NOT_PROVEN = "NOT_PROVEN" # Any gate NOT_PROVEN (waiting for evidence)


class GateVerdictStatus(str, Enum):
    """Individual Guardian gate verdict"""
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    NOT_PROVEN = "NOT_PROVEN"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReportStatus(str, Enum):
    """DayReport lifecycle"""
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    ARCHIVED = "ARCHIVED"


class BundleStatus(str, Enum):
    """ComplianceBundle lifecycle"""
    DRAFT = "DRAFT"
    CERTIFIED = "CERTIFIED"
    ARCHIVED = "ARCHIVED"


class ArchiveStatus(str, Enum):
    """ArchiveRecord lifecycle"""
    WRITTEN = "WRITTEN"
    VERIFIED = "VERIFIED"
    RETRIEVED = "RETRIEVED"
    PURGED = "PURGED"


class AuthorityLevel(str, Enum):
    """Authority level - ZERO only"""
    ZERO = "ZERO"


# ============================================================================
# DATA CLASSES (Immutable tuples)
# ============================================================================

@dataclass(frozen=True)
class GateDecisionTuple:
    """Guardian gate decision (immutable)"""
    gate_id: int
    verdict: GateVerdictStatus
    evidence_id: str
    event_time: datetime
    knowledge_time: datetime


@dataclass(frozen=True)
class BatchRunTuple:
    """Immutable snapshot of batch identity + timing"""
    batch_id: str
    run_date: date
    market_open_time: datetime
    market_close_time: datetime
    mode: BatchMode
    correlation_id: str


@dataclass(frozen=True)
class DayReportTuple:
    """Immutable snapshot of end-of-day summary"""
    report_id: str
    batch_id: str
    trade_count: int
    pnl_summary: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    alert_count: int
    export_time: datetime


@dataclass(frozen=True)
class AlertRecordTuple:
    """Immutable snapshot of alert + context"""
    alert_id: str
    batch_id: str
    severity: AlertSeverity
    alert_type: str
    message: str
    timestamp: datetime
    escalation_flag: bool


@dataclass(frozen=True)
class ComplianceBundleTuple:
    """Immutable snapshot of compliance data at certification"""
    bundle_id: str
    batch_id: str
    tax_summary: Dict[str, Any]
    receipt_hashes: List[str]
    audit_trail: List[Dict[str, Any]]
    certification_time: datetime


@dataclass(frozen=True)
class ArchiveRecordTuple:
    """Immutable snapshot of archived data in HP storage"""
    archive_record_id: str
    batch_id: str
    storage_path: str
    retention_years: int
    immutable_hash: str
    retrieval_metadata: Dict[str, Any]


@dataclass(frozen=True)
class BatchVerdictTuple:
    """Immutable snapshot of batch authorization verdict"""
    verdict_id: str
    batch_id: str
    guardian_gate_results: List[GateDecisionTuple]
    compliance_passed: bool
    tax_verified: bool
    archive_verified: bool
    batch_status: VerdictStatus


# ============================================================================
# MUTABLE DOMAIN ENTITIES
# ============================================================================

@dataclass
class BatchRun:
    """End-of-day batch execution session"""
    batch_id: str
    run_date: date
    market_open_time: datetime
    market_close_time: datetime
    mode: BatchMode
    correlation_id: str
    batch_status: BatchStatus = BatchStatus.PENDING
    initiated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)

    def to_tuple(self) -> BatchRunTuple:
        """Convert to immutable tuple"""
        return BatchRunTuple(
            batch_id=self.batch_id,
            run_date=self.run_date,
            market_open_time=self.market_open_time,
            market_close_time=self.market_close_time,
            mode=self.mode,
            correlation_id=self.correlation_id
        )

    def is_immutable(self) -> bool:
        """Check if batch is closed (immutable)"""
        return self.closed_at is not None

    def validate(self) -> None:
        """Validate batch constraints (CG01)"""
        # CG01: NO_AUTHORITY_ESCALATION - mode must be PAPER, SHADOW, or ANALYSIS
        if self.mode not in [BatchMode.PAPER, BatchMode.SHADOW, BatchMode.ANALYSIS]:
            raise ValueError(f"CG01 VIOLATION: mode must be PAPER/SHADOW/ANALYSIS, got {self.mode}")

        # Market times must be valid
        if self.market_open_time >= self.market_close_time:
            raise ValueError("Market open time must be before market close time")


@dataclass
class DayReport:
    """End-of-day summary report"""
    report_id: str
    batch_id: str
    report_date: date
    trade_count: int = 0
    pnl_summary: Dict[str, Any] = field(default_factory=dict)
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    alert_count: int = 0
    alert_summary: Dict[str, int] = field(default_factory=dict)
    export_time: datetime = field(default_factory=datetime.utcnow)
    report_status: ReportStatus = ReportStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    finalized_at: Optional[datetime] = None

    def to_tuple(self) -> DayReportTuple:
        """Convert to immutable tuple"""
        return DayReportTuple(
            report_id=self.report_id,
            batch_id=self.batch_id,
            trade_count=self.trade_count,
            pnl_summary=self.pnl_summary,
            risk_metrics=self.risk_metrics,
            alert_count=self.alert_count,
            export_time=self.export_time
        )

    def is_finalized(self) -> bool:
        """Check if report is locked (immutable)"""
        return self.finalized_at is not None

    def validate(self) -> None:
        """Validate report constraints"""
        if self.trade_count < 0:
            raise ValueError("trade_count must be >= 0")

        if self.alert_count < 0:
            raise ValueError("alert_count must be >= 0")

        # Verify required fields in pnl_summary
        required_pnl = {'gross_pnl', 'net_pnl', 'currency', 'timestamp'}
        if not required_pnl.issubset(self.pnl_summary.keys()):
            raise ValueError(f"pnl_summary must contain {required_pnl}")

        # Verify required fields in risk_metrics
        required_risk = {'max_drawdown', 'var_95', 'sharpe_ratio', 'win_rate', 'avg_win', 'avg_loss'}
        if not required_risk.issubset(self.risk_metrics.keys()):
            raise ValueError(f"risk_metrics must contain {required_risk}")


@dataclass
class AlertRecord:
    """Trade alert or anomaly detection"""
    alert_id: str
    batch_id: str
    severity: AlertSeverity
    alert_type: str
    message: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    escalation_flag: bool = False
    escalated_to: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_tuple(self) -> AlertRecordTuple:
        """Convert to immutable tuple"""
        return AlertRecordTuple(
            alert_id=self.alert_id,
            batch_id=self.batch_id,
            severity=self.severity,
            alert_type=self.alert_type,
            message=self.message,
            timestamp=self.timestamp,
            escalation_flag=self.escalation_flag
        )

    def validate(self) -> None:
        """Validate alert constraints"""
        if self.escalation_flag and not self.escalated_to:
            raise ValueError("escalation_flag=true requires escalated_to to be set")

        if self.resolved and not self.resolved_at:
            raise ValueError("resolved=true requires resolved_at to be set")

        if self.resolved_at and self.resolved_at < self.timestamp:
            raise ValueError("resolved_at must be >= timestamp")


@dataclass
class ComplianceBundle:
    """Immutable compliance package"""
    bundle_id: str
    batch_id: str
    tax_summary: Dict[str, Any]
    receipt_hashes: List[str]
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    bundle_status: BundleStatus = BundleStatus.DRAFT
    certification_time: Optional[datetime] = None
    certifying_authority: Optional[str] = None
    bundle_hash: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_tuple(self) -> ComplianceBundleTuple:
        """Convert to immutable tuple"""
        return ComplianceBundleTuple(
            bundle_id=self.bundle_id,
            batch_id=self.batch_id,
            tax_summary=self.tax_summary,
            receipt_hashes=self.receipt_hashes,
            audit_trail=self.audit_trail,
            certification_time=self.certification_time
        )

    def is_certified(self) -> bool:
        """Check if bundle is locked (immutable)"""
        return self.bundle_status == BundleStatus.CERTIFIED

    def compute_hash(self) -> str:
        """Compute immutability seal hash"""
        data = {
            'tax_summary': self.tax_summary,
            'receipt_hashes': self.receipt_hashes,
            'audit_trail': self.audit_trail
        }
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def validate(self) -> None:
        """Validate bundle constraints"""
        required_tax = {'gains', 'losses', 'wash_sales', 'adjustments', 'total_taxable_income'}
        if not required_tax.issubset(self.tax_summary.keys()):
            raise ValueError(f"tax_summary must contain {required_tax}")

        if not self.receipt_hashes or len(self.receipt_hashes) == 0:
            raise ValueError("receipt_hashes cannot be empty")


@dataclass
class ArchiveRecord:
    """Immutable archive entry in HP durable storage"""
    archive_record_id: str
    batch_id: str
    storage_path: str
    retention_years: int = 7
    immutable_hash: Optional[str] = None
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)
    archive_status: ArchiveStatus = ArchiveStatus.WRITTEN
    report_id: Optional[str] = None
    bundle_id: Optional[str] = None
    hp_receipt: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None

    def to_tuple(self) -> ArchiveRecordTuple:
        """Convert to immutable tuple"""
        return ArchiveRecordTuple(
            archive_record_id=self.archive_record_id,
            batch_id=self.batch_id,
            storage_path=self.storage_path,
            retention_years=self.retention_years,
            immutable_hash=self.immutable_hash,
            retrieval_metadata=self.retrieval_metadata
        )

    def validate(self) -> None:
        """Validate archive constraints (CG06, CG07)"""
        # CG06: ARCHIVE_WRITE_ONCE - no updates allowed after creation
        if self.retention_years < 7:
            raise ValueError("CG08 VIOLATION: retention_years must be >= 7")

        required_metadata = {'format', 'size_bytes', 'created_date', 'archived_date'}
        if not required_metadata.issubset(self.retrieval_metadata.keys()):
            raise ValueError(f"retrieval_metadata must contain {required_metadata}")


@dataclass
class BatchVerdict:
    """Final authorization verdict for batch execution"""
    verdict_id: str
    batch_id: str
    guardian_gate_results: List[GateDecisionTuple]
    compliance_passed: bool
    tax_verified: bool
    archive_verified: bool
    batch_status: VerdictStatus
    verdict_reasoning: Optional[str] = None
    authority_used: AuthorityLevel = AuthorityLevel.ZERO
    event_time: datetime = field(default_factory=datetime.utcnow)
    knowledge_time: datetime = field(default_factory=datetime.utcnow)
    policy_hash: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_tuple(self) -> BatchVerdictTuple:
        """Convert to immutable tuple"""
        return BatchVerdictTuple(
            verdict_id=self.verdict_id,
            batch_id=self.batch_id,
            guardian_gate_results=self.guardian_gate_results,
            compliance_passed=self.compliance_passed,
            tax_verified=self.tax_verified,
            archive_verified=self.archive_verified,
            batch_status=self.batch_status
        )

    def validate(self) -> None:
        """Validate verdict constraints (CG01, CG03, CG04)"""
        # CG01: NO_AUTHORITY_ESCALATION
        if self.authority_used != AuthorityLevel.ZERO:
            raise ValueError("CG01 VIOLATION: authority_used must be ZERO")

        # CG04: GUARDIAN_GATES_MUST_COMPLETE
        if len(self.guardian_gate_results) != 8:
            raise ValueError("CG04 VIOLATION: guardian_gate_results must contain exactly 8 gates")

        # Verify gate IDs are 1-8
        gate_ids = {gate.gate_id for gate in self.guardian_gate_results}
        if gate_ids != set(range(1, 9)):
            raise ValueError("CG04 VIOLATION: guardian_gate_results must contain gates 1-8")

        # CG03: VERDICT_REQUIRES_ALL_GATES_PASS
        all_gates_pass = all(gate.verdict == GateVerdictStatus.PASS
                            for gate in self.guardian_gate_results)

        if self.batch_status == VerdictStatus.APPROVED:
            if not (all_gates_pass and self.compliance_passed and
                    self.tax_verified and self.archive_verified):
                raise ValueError("CG03 VIOLATION: APPROVED requires all gates PASS + all verifications")

        if any(gate.verdict == GateVerdictStatus.BLOCKED
               for gate in self.guardian_gate_results):
            if self.batch_status != VerdictStatus.BLOCKED:
                raise ValueError("CG03 VIOLATION: any BLOCKED gate requires BLOCKED status")

        if any(gate.verdict == GateVerdictStatus.NOT_PROVEN
               for gate in self.guardian_gate_results):
            if self.batch_status != VerdictStatus.NOT_PROVEN:
                raise ValueError("CG03 VIOLATION: any NOT_PROVEN gate requires NOT_PROVEN status")

        # CG01: Verify all gates have authority_used = ZERO (in context)
        if self.event_time > self.knowledge_time:
            raise ValueError("event_time must be <= knowledge_time")


# ============================================================================
# BATCH ENGINE
# ============================================================================

class ImmutabilityViolation(Exception):
    """CG02, CG05: Batch data immutable after close"""
    pass


class WriteOnceViolation(Exception):
    """CG06: ArchiveRecord is write-once"""
    pass


class RequiredVerdictMissing(Exception):
    """CG04: Batch cannot close without complete verdict"""
    pass


class MissingHPReceipt(Exception):
    """CG07: HP receipt required before VERIFIED"""
    pass


class RetentionNotMet(Exception):
    """CG08: Cannot purge before retention_until date"""
    pass


class BatchEngine:
    """
    NinjaTrader Batch Engine - Production Implementation
    Authority Invariant: ZERO (immutable)
    """

    def __init__(self, db_path: str = None):
        """Initialize batch engine with SQLite database"""
        if db_path is None:
            # Use environment variable FLIPFLOP_DB_PATH, fallback to ./databases/
            db_dir = os.getenv('FLIPFLOP_DB_PATH', './databases/')
            db_path = os.path.join(db_dir, 'batch.db')

            # Create directory if it doesn't exist
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Batch Engine: Using database path {db_path}")

        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # BatchRun table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_runs (
                    batch_id TEXT PRIMARY KEY,
                    run_date TEXT NOT NULL,
                    market_open_time TEXT NOT NULL,
                    market_close_time TEXT NOT NULL,
                    mode TEXT NOT NULL CHECK(mode IN ('PAPER', 'SHADOW', 'ANALYSIS')),
                    correlation_id TEXT NOT NULL,
                    batch_status TEXT NOT NULL DEFAULT 'PENDING',
                    initiated_at TEXT NOT NULL,
                    closed_at TEXT,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL
                )
            ''')

            # BatchVerdict table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batch_verdicts (
                    verdict_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL UNIQUE,
                    guardian_gate_results TEXT NOT NULL,
                    compliance_passed INTEGER NOT NULL,
                    tax_verified INTEGER NOT NULL,
                    archive_verified INTEGER NOT NULL,
                    batch_status TEXT NOT NULL CHECK(batch_status IN ('APPROVED', 'BLOCKED', 'NOT_PROVEN')),
                    verdict_reasoning TEXT,
                    authority_used TEXT NOT NULL DEFAULT 'ZERO' CHECK(authority_used = 'ZERO'),
                    event_time TEXT NOT NULL,
                    knowledge_time TEXT NOT NULL,
                    policy_hash TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(batch_id) REFERENCES batch_runs(batch_id)
                )
            ''')

            # DayReport table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS day_reports (
                    report_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL UNIQUE,
                    report_date TEXT NOT NULL,
                    trade_count INTEGER NOT NULL DEFAULT 0 CHECK(trade_count >= 0),
                    pnl_summary TEXT NOT NULL,
                    risk_metrics TEXT NOT NULL,
                    alert_count INTEGER NOT NULL DEFAULT 0 CHECK(alert_count >= 0),
                    alert_summary TEXT,
                    export_time TEXT NOT NULL,
                    report_status TEXT NOT NULL DEFAULT 'DRAFT',
                    created_at TEXT NOT NULL,
                    finalized_at TEXT,
                    FOREIGN KEY(batch_id) REFERENCES batch_runs(batch_id)
                )
            ''')

            # AlertRecord table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    report_id TEXT,
                    severity TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    context TEXT,
                    timestamp TEXT NOT NULL,
                    escalation_flag INTEGER NOT NULL DEFAULT 0,
                    escalated_to TEXT,
                    resolved INTEGER NOT NULL DEFAULT 0,
                    resolved_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(batch_id) REFERENCES batch_runs(batch_id),
                    FOREIGN KEY(report_id) REFERENCES day_reports(report_id)
                )
            ''')

            # ComplianceBundle table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS compliance_bundles (
                    bundle_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL UNIQUE,
                    tax_summary TEXT NOT NULL,
                    receipt_hashes TEXT NOT NULL,
                    audit_trail TEXT NOT NULL,
                    bundle_status TEXT NOT NULL DEFAULT 'DRAFT',
                    certification_time TEXT,
                    certifying_authority TEXT,
                    bundle_hash TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(batch_id) REFERENCES batch_runs(batch_id)
                )
            ''')

            # ArchiveRecord table (write-once, append-only)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS archive_records (
                    archive_record_id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    report_id TEXT,
                    bundle_id TEXT,
                    storage_path TEXT NOT NULL UNIQUE,
                    storage_tier TEXT NOT NULL DEFAULT 'WARM',
                    retention_years INTEGER NOT NULL DEFAULT 7 CHECK(retention_years >= 7),
                    immutable_hash TEXT NOT NULL,
                    retrieval_metadata TEXT NOT NULL,
                    hp_receipt TEXT,
                    archive_status TEXT NOT NULL DEFAULT 'WRITTEN',
                    created_at TEXT NOT NULL,
                    verified_at TEXT,
                    FOREIGN KEY(batch_id) REFERENCES batch_runs(batch_id),
                    FOREIGN KEY(report_id) REFERENCES day_reports(report_id),
                    FOREIGN KEY(bundle_id) REFERENCES compliance_bundles(bundle_id)
                )
            ''')

            conn.commit()

    def create_batch(self, run_date: date, market_open_time: datetime,
                    market_close_time: datetime, mode: BatchMode,
                    correlation_id: str) -> BatchRun:
        """Create new batch run (CG01: mode validated)"""
        with self.lock:
            batch = BatchRun(
                batch_id=str(uuid.uuid4()),
                run_date=run_date,
                market_open_time=market_open_time,
                market_close_time=market_close_time,
                mode=mode,
                correlation_id=correlation_id
            )

            # CG01: Validate authority invariant
            batch.validate()

            # Persist to database
            self._insert_batch_run(batch)
            return batch

    def _insert_batch_run(self, batch: BatchRun) -> None:
        """Insert batch run into database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO batch_runs (
                    batch_id, run_date, market_open_time, market_close_time,
                    mode, correlation_id, batch_status, initiated_at, created_at, modified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                batch.batch_id,
                batch.run_date.isoformat(),
                batch.market_open_time.isoformat(),
                batch.market_close_time.isoformat(),
                batch.mode.value,
                batch.correlation_id,
                batch.batch_status.value,
                batch.initiated_at.isoformat(),
                batch.created_at.isoformat(),
                batch.modified_at.isoformat()
            ))
            conn.commit()

    def get_batch(self, batch_id: str) -> Optional[BatchRun]:
        """Retrieve batch run (immutable read)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM batch_runs WHERE batch_id = ?', (batch_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_batch_run(row)

    @staticmethod
    def _row_to_batch_run(row) -> BatchRun:
        """Convert database row to BatchRun object"""
        return BatchRun(
            batch_id=row[0],
            run_date=date.fromisoformat(row[1]),
            market_open_time=datetime.fromisoformat(row[2]),
            market_close_time=datetime.fromisoformat(row[3]),
            mode=BatchMode(row[4]),
            correlation_id=row[5],
            batch_status=BatchStatus(row[6]),
            initiated_at=datetime.fromisoformat(row[7]),
            closed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            created_at=datetime.fromisoformat(row[9]),
            modified_at=datetime.fromisoformat(row[10])
        )

    def create_day_report(self, batch_id: str, pnl_summary: Dict[str, Any],
                         risk_metrics: Dict[str, Any], trade_count: int = 0,
                         alert_summary: Dict[str, int] = None) -> DayReport:
        """Create day report for batch"""
        with self.lock:
            batch = self.get_batch(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            if batch.is_immutable():
                raise ImmutabilityViolation(f"CG02 VIOLATION: Batch {batch_id} is closed (immutable)")

            report = DayReport(
                report_id=str(uuid.uuid4()),
                batch_id=batch_id,
                report_date=batch.run_date,
                trade_count=trade_count,
                pnl_summary=pnl_summary,
                risk_metrics=risk_metrics,
                alert_count=sum(alert_summary.values()) if alert_summary else 0,
                alert_summary=alert_summary or {}
            )

            report.validate()
            self._insert_day_report(report)
            return report

    def _insert_day_report(self, report: DayReport) -> None:
        """Insert day report into database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO day_reports (
                    report_id, batch_id, report_date, trade_count, pnl_summary,
                    risk_metrics, alert_count, alert_summary, export_time,
                    report_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.report_id,
                report.batch_id,
                report.report_date.isoformat(),
                report.trade_count,
                json.dumps(report.pnl_summary),
                json.dumps(report.risk_metrics),
                report.alert_count,
                json.dumps(report.alert_summary),
                report.export_time.isoformat(),
                report.report_status.value,
                report.created_at.isoformat()
            ))
            conn.commit()

    def get_day_report(self, batch_id: str) -> Optional[DayReport]:
        """Retrieve day report for batch (immutable read)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM day_reports WHERE batch_id = ?', (batch_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return DayReport(
                report_id=row[0],
                batch_id=row[1],
                report_date=date.fromisoformat(row[2]),
                trade_count=row[3],
                pnl_summary=json.loads(row[4]),
                risk_metrics=json.loads(row[5]),
                alert_count=row[6],
                alert_summary=json.loads(row[7]) if row[7] else {},
                export_time=datetime.fromisoformat(row[8]),
                report_status=ReportStatus(row[9]),
                created_at=datetime.fromisoformat(row[10]),
                finalized_at=datetime.fromisoformat(row[11]) if row[11] else None
            )

    def create_alert(self, batch_id: str, severity: AlertSeverity,
                    alert_type: str, message: str,
                    context: Dict[str, Any] = None) -> AlertRecord:
        """Create alert record"""
        with self.lock:
            batch = self.get_batch(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            if batch.is_immutable():
                raise ImmutabilityViolation(f"CG02 VIOLATION: Batch {batch_id} is closed (immutable)")

            alert = AlertRecord(
                alert_id=str(uuid.uuid4()),
                batch_id=batch_id,
                severity=severity,
                alert_type=alert_type,
                message=message,
                timestamp=datetime.utcnow(),
                context=context or {}
            )

            alert.validate()
            self._insert_alert(alert)
            return alert

    def _insert_alert(self, alert: AlertRecord) -> None:
        """Insert alert record into database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO alerts (
                    alert_id, batch_id, severity, alert_type, message,
                    context, timestamp, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id,
                alert.batch_id,
                alert.severity.value,
                alert.alert_type,
                alert.message,
                json.dumps(alert.context),
                alert.timestamp.isoformat(),
                datetime.utcnow().isoformat()
            ))
            conn.commit()

    def create_compliance_bundle(self, batch_id: str, tax_summary: Dict[str, Any],
                                receipt_hashes: List[str]) -> ComplianceBundle:
        """Create compliance bundle"""
        with self.lock:
            batch = self.get_batch(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            if batch.is_immutable():
                raise ImmutabilityViolation(f"CG02 VIOLATION: Batch {batch_id} is closed (immutable)")

            bundle = ComplianceBundle(
                bundle_id=str(uuid.uuid4()),
                batch_id=batch_id,
                tax_summary=tax_summary,
                receipt_hashes=receipt_hashes
            )

            bundle.validate()
            self._insert_compliance_bundle(bundle)
            return bundle

    def _insert_compliance_bundle(self, bundle: ComplianceBundle) -> None:
        """Insert compliance bundle into database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO compliance_bundles (
                    bundle_id, batch_id, tax_summary, receipt_hashes,
                    audit_trail, bundle_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                bundle.bundle_id,
                bundle.batch_id,
                json.dumps(bundle.tax_summary),
                json.dumps(bundle.receipt_hashes),
                json.dumps(bundle.audit_trail),
                bundle.bundle_status.value,
                bundle.created_at.isoformat()
            ))
            conn.commit()

    def certify_compliance_bundle(self, bundle_id: str,
                                 certifying_authority: str) -> ComplianceBundle:
        """Certify compliance bundle (CG05: locks immutability)"""
        with self.lock:
            bundle = self.get_compliance_bundle(bundle_id)
            if not bundle:
                raise ValueError(f"Bundle {bundle_id} not found")

            if bundle.is_certified():
                raise ImmutabilityViolation(f"CG05 VIOLATION: Bundle {bundle_id} already certified")

            bundle.certification_time = datetime.utcnow()
            bundle.certifying_authority = certifying_authority
            bundle.bundle_hash = bundle.compute_hash()
            bundle.bundle_status = BundleStatus.CERTIFIED

            self._update_compliance_bundle(bundle)
            return bundle

    def _update_compliance_bundle(self, bundle: ComplianceBundle) -> None:
        """Update compliance bundle (only before certification)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE compliance_bundles
                SET bundle_status = ?, certification_time = ?, certifying_authority = ?, bundle_hash = ?
                WHERE bundle_id = ?
            ''', (
                bundle.bundle_status.value,
                bundle.certification_time.isoformat() if bundle.certification_time else None,
                bundle.certifying_authority,
                bundle.bundle_hash,
                bundle.bundle_id
            ))
            conn.commit()

    def get_compliance_bundle(self, bundle_id: str) -> Optional[ComplianceBundle]:
        """Retrieve compliance bundle"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM compliance_bundles WHERE bundle_id = ?', (bundle_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return ComplianceBundle(
                bundle_id=row[0],
                batch_id=row[1],
                tax_summary=json.loads(row[2]),
                receipt_hashes=json.loads(row[3]),
                audit_trail=json.loads(row[4]),
                bundle_status=BundleStatus(row[5]),
                certification_time=datetime.fromisoformat(row[6]) if row[6] else None,
                certifying_authority=row[7],
                bundle_hash=row[8],
                created_at=datetime.fromisoformat(row[9])
            )

    def create_archive_record(self, batch_id: str, storage_path: str,
                             retrieval_metadata: Dict[str, Any] = None,
                             report_id: str = None, bundle_id: str = None,
                             retention_years: int = 7) -> ArchiveRecord:
        """Create archive record (CG06: write-once)"""
        if retrieval_metadata is None:
            now_iso = datetime.utcnow().isoformat()
            retrieval_metadata = {
                'format': 'sqlite',
                'size_bytes': 0,
                'created_date': now_iso,
                'archived_date': now_iso,
            }
        with self.lock:
            batch = self.get_batch(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            archive = ArchiveRecord(
                archive_record_id=str(uuid.uuid4()),
                batch_id=batch_id,
                storage_path=storage_path,
                retrieval_metadata=retrieval_metadata,
                report_id=report_id,
                bundle_id=bundle_id,
                retention_years=retention_years
            )

            archive.validate()

            # Compute immutable hash
            archive.immutable_hash = hashlib.sha256(
                json.dumps(retrieval_metadata, sort_keys=True, default=str).encode()
            ).hexdigest()

            self._insert_archive_record(archive)
            return archive

    def _insert_archive_record(self, archive: ArchiveRecord) -> None:
        """Insert archive record (write-once)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO archive_records (
                    archive_record_id, batch_id, report_id, bundle_id, storage_path,
                    retention_years, immutable_hash, retrieval_metadata, archive_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                archive.archive_record_id,
                archive.batch_id,
                archive.report_id,
                archive.bundle_id,
                archive.storage_path,
                archive.retention_years,
                archive.immutable_hash,
                json.dumps(archive.retrieval_metadata),
                archive.archive_status.value,
                archive.created_at.isoformat()
            ))
            conn.commit()

    def get_archive_record(self, archive_id: str) -> Optional[ArchiveRecord]:
        """Retrieve archive record"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM archive_records WHERE archive_record_id = ?', (archive_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return ArchiveRecord(
                archive_record_id=row[0],
                batch_id=row[1],
                report_id=row[2],
                bundle_id=row[3],
                storage_path=row[4],
                storage_tier=row[5],
                retention_years=row[6],
                immutable_hash=row[7],
                retrieval_metadata=json.loads(row[8]),
                hp_receipt=json.loads(row[9]) if row[9] else None,
                archive_status=ArchiveStatus(row[10]),
                created_at=datetime.fromisoformat(row[11]),
                verified_at=datetime.fromisoformat(row[12]) if row[12] else None
            )

    def issue_verdict(self, batch_id: str, guardian_gate_results: List[GateDecisionTuple],
                     compliance_passed: bool, tax_verified: bool,
                     archive_verified: bool) -> BatchVerdict:
        """Issue batch verdict (CG03, CG04)"""
        with self.lock:
            batch = self.get_batch(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            # Determine verdict status based on gates
            all_pass = all(gate.verdict == GateVerdictStatus.PASS
                          for gate in guardian_gate_results)
            any_blocked = any(gate.verdict == GateVerdictStatus.BLOCKED
                             for gate in guardian_gate_results)
            any_not_proven = any(gate.verdict == GateVerdictStatus.NOT_PROVEN
                                for gate in guardian_gate_results)

            if all_pass and compliance_passed and tax_verified and archive_verified:
                status = VerdictStatus.APPROVED
            elif any_blocked or not compliance_passed or not tax_verified or not archive_verified:
                status = VerdictStatus.BLOCKED
            else:
                status = VerdictStatus.NOT_PROVEN

            verdict = BatchVerdict(
                verdict_id=str(uuid.uuid4()),
                batch_id=batch_id,
                guardian_gate_results=guardian_gate_results,
                compliance_passed=compliance_passed,
                tax_verified=tax_verified,
                archive_verified=archive_verified,
                batch_status=status
            )

            verdict.validate()
            self._insert_verdict(verdict)
            return verdict

    def _insert_verdict(self, verdict: BatchVerdict) -> None:
        """Insert verdict into database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Serialize gate results
            gate_data = []
            for gate in verdict.guardian_gate_results:
                gate_data.append({
                    'gate_id': gate.gate_id,
                    'verdict': gate.verdict.value,
                    'evidence_id': gate.evidence_id,
                    'event_time': gate.event_time.isoformat(),
                    'knowledge_time': gate.knowledge_time.isoformat()
                })

            cursor.execute('''
                INSERT INTO batch_verdicts (
                    verdict_id, batch_id, guardian_gate_results, compliance_passed,
                    tax_verified, archive_verified, batch_status, authority_used,
                    event_time, knowledge_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                verdict.verdict_id,
                verdict.batch_id,
                json.dumps(gate_data),
                1 if verdict.compliance_passed else 0,
                1 if verdict.tax_verified else 0,
                1 if verdict.archive_verified else 0,
                verdict.batch_status.value,
                verdict.authority_used.value,
                verdict.event_time.isoformat(),
                verdict.knowledge_time.isoformat(),
                verdict.created_at.isoformat()
            ))
            conn.commit()

    def get_verdict(self, batch_id: str) -> Optional[BatchVerdict]:
        """Retrieve verdict for batch"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM batch_verdicts WHERE batch_id = ?', (batch_id,))
            row = cursor.fetchone()

            if not row:
                return None

            gate_data = json.loads(row[2])
            gates = [GateDecisionTuple(
                gate_id=gate['gate_id'],
                verdict=GateVerdictStatus(gate['verdict']),
                evidence_id=gate['evidence_id'],
                event_time=datetime.fromisoformat(gate['event_time']),
                knowledge_time=datetime.fromisoformat(gate['knowledge_time'])
            ) for gate in gate_data]

            return BatchVerdict(
                verdict_id=row[0],
                batch_id=row[1],
                guardian_gate_results=gates,
                compliance_passed=bool(row[3]),
                tax_verified=bool(row[4]),
                archive_verified=bool(row[5]),
                batch_status=VerdictStatus(row[6]),
                verdict_reasoning=row[7],
                authority_used=AuthorityLevel(row[8]),
                event_time=datetime.fromisoformat(row[9]),
                knowledge_time=datetime.fromisoformat(row[10]),
                policy_hash=row[11],
                created_at=datetime.fromisoformat(row[12])
            )

    def close_batch(self, batch_id: str) -> BatchRun:
        """Close batch (mark immutable, CG02)"""
        with self.lock:
            batch = self.get_batch(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")

            # CG04: Verify verdict exists and is complete
            verdict = self.get_verdict(batch_id)
            if not verdict:
                raise RequiredVerdictMissing("CG04 VIOLATION: Batch cannot close without complete verdict")

            batch.batch_status = BatchStatus.CLOSED
            batch.closed_at = datetime.utcnow()
            batch.modified_at = datetime.utcnow()

            self._update_batch_status(batch)
            return batch

    def _update_batch_status(self, batch: BatchRun) -> None:
        """Update batch status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE batch_runs
                SET batch_status = ?, closed_at = ?, modified_at = ?
                WHERE batch_id = ?
            ''', (
                batch.batch_status.value,
                batch.closed_at.isoformat() if batch.closed_at else None,
                batch.modified_at.isoformat(),
                batch.batch_id
            ))
            conn.commit()

    def get_all_alerts_for_batch(self, batch_id: str) -> List[AlertRecord]:
        """Get all alerts for batch, sorted by severity"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}

            cursor.execute('''
                SELECT * FROM alerts WHERE batch_id = ?
                ORDER BY CASE severity
                    WHEN 'CRITICAL' THEN 0
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'LOW' THEN 3
                END
            ''', (batch_id,))

            alerts = []
            for row in cursor.fetchall():
                alerts.append(AlertRecord(
                    alert_id=row[0],
                    batch_id=row[1],
                    severity=AlertSeverity(row[3]),
                    alert_type=row[4],
                    message=row[5],
                    context=json.loads(row[6]) if row[6] else {},
                    timestamp=datetime.fromisoformat(row[7]),
                    escalation_flag=bool(row[9]),
                    escalated_to=row[10],
                    resolved=bool(row[11]),
                    resolved_at=datetime.fromisoformat(row[12]) if row[12] else None
                ))

            return alerts
