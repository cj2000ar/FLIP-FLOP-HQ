"""
NinjaTrader Batch Engine - Phase 2 Production Implementation
Authority Invariant: ZERO (immutable)
Failure Policy: FAIL_CLOSED
"""

from .batch_engine import (
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
    ReportStatus,
    BundleStatus,
    ArchiveStatus,
    AuthorityLevel,
    GateDecisionTuple,
    BatchRunTuple,
    DayReportTuple,
    AlertRecordTuple,
    ComplianceBundleTuple,
    ArchiveRecordTuple,
    BatchVerdictTuple,
    ImmutabilityViolation,
    WriteOnceViolation,
    RequiredVerdictMissing,
    MissingHPReceipt,
    RetentionNotMet
)

__all__ = [
    'BatchEngine',
    'BatchRun',
    'BatchVerdict',
    'DayReport',
    'AlertRecord',
    'ComplianceBundle',
    'ArchiveRecord',
    'BatchMode',
    'BatchStatus',
    'VerdictStatus',
    'GateVerdictStatus',
    'AlertSeverity',
    'ReportStatus',
    'BundleStatus',
    'ArchiveStatus',
    'AuthorityLevel',
    'GateDecisionTuple',
    'BatchRunTuple',
    'DayReportTuple',
    'AlertRecordTuple',
    'ComplianceBundleTuple',
    'ArchiveRecordTuple',
    'BatchVerdictTuple',
    'ImmutabilityViolation',
    'WriteOnceViolation',
    'RequiredVerdictMissing',
    'MissingHPReceipt',
    'RetentionNotMet'
]

__version__ = "1.0.0"
__authority__ = "ZERO"
__live_enabled__ = False
__failure_policy__ = "FAIL_CLOSED"
