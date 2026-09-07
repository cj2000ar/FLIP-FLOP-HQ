"""
NinjaTrader Batch API - FastAPI Endpoints
Authority Invariant: ZERO (immutable)
Phase 2 Production Implementation
"""

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from enum import Enum
import json
import logging

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
    ReportStatus,
    BundleStatus,
    ArchiveStatus,
    AuthorityLevel,
    GateDecisionTuple,
    ImmutabilityViolation,
    WriteOnceViolation,
    RequiredVerdictMissing,
    MissingHPReceipt,
    RetentionNotMet
)


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS (Request/Response)
# ============================================================================

class GateDecisionRequest(BaseModel):
    """Guardian gate decision request"""
    gate_id: int = Field(..., ge=1, le=8, description="Gate ID (1-8)")
    verdict: str = Field(..., regex="^(PASS|BLOCKED|NOT_PROVEN)$")
    evidence_id: str
    event_time: datetime
    knowledge_time: datetime


class CreateBatchRequest(BaseModel):
    """Create batch run request"""
    run_date: date
    market_open_time: datetime
    market_close_time: datetime
    mode: str = Field(..., regex="^(PAPER|SHADOW|ANALYSIS)$")
    correlation_id: str


class CreateDayReportRequest(BaseModel):
    """Create day report request"""
    pnl_summary: Dict[str, Any] = Field(..., description="Must have: gross_pnl, net_pnl, currency, timestamp")
    risk_metrics: Dict[str, Any] = Field(..., description="Must have: max_drawdown, var_95, sharpe_ratio, win_rate, avg_win, avg_loss")
    trade_count: int = Field(default=0, ge=0)
    alert_summary: Optional[Dict[str, int]] = None


class CreateAlertRequest(BaseModel):
    """Create alert record request"""
    severity: str = Field(..., regex="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    alert_type: str
    message: str
    context: Optional[Dict[str, Any]] = None


class CreateComplianceBundleRequest(BaseModel):
    """Create compliance bundle request"""
    tax_summary: Dict[str, Any] = Field(..., description="Must have: gains, losses, wash_sales, adjustments, total_taxable_income")
    receipt_hashes: List[str] = Field(..., min_items=1)


class CreateArchiveRecordRequest(BaseModel):
    """Create archive record request"""
    storage_path: str
    retrieval_metadata: Dict[str, Any] = Field(..., description="Must have: format, size_bytes, created_date, archived_date")
    report_id: Optional[str] = None
    bundle_id: Optional[str] = None
    retention_years: int = Field(default=7, ge=7)


class IssueBatchVerdictRequest(BaseModel):
    """Issue batch verdict request"""
    guardian_gate_results: List[GateDecisionRequest] = Field(..., min_items=8, max_items=8)
    compliance_passed: bool
    tax_verified: bool
    archive_verified: bool


class VerifyArchiveRequest(BaseModel):
    """Verify archive with HP receipt"""
    hp_receipt: Dict[str, Any] = Field(..., description="Must have: receipt_id, timestamp, confirmation_hash")


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class BatchRunResponse(BaseModel):
    """Batch run response"""
    batch_id: str
    run_date: str
    market_open_time: str
    market_close_time: str
    mode: str
    correlation_id: str
    batch_status: str
    initiated_at: str
    closed_at: Optional[str] = None
    created_at: str
    modified_at: str

    @classmethod
    def from_entity(cls, batch: BatchRun):
        return cls(
            batch_id=batch.batch_id,
            run_date=batch.run_date.isoformat(),
            market_open_time=batch.market_open_time.isoformat(),
            market_close_time=batch.market_close_time.isoformat(),
            mode=batch.mode.value,
            correlation_id=batch.correlation_id,
            batch_status=batch.batch_status.value,
            initiated_at=batch.initiated_at.isoformat(),
            closed_at=batch.closed_at.isoformat() if batch.closed_at else None,
            created_at=batch.created_at.isoformat(),
            modified_at=batch.modified_at.isoformat()
        )


class DayReportResponse(BaseModel):
    """Day report response"""
    report_id: str
    batch_id: str
    report_date: str
    trade_count: int
    pnl_summary: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    alert_count: int
    alert_summary: Dict[str, int]
    export_time: str
    report_status: str
    created_at: str
    finalized_at: Optional[str] = None

    @classmethod
    def from_entity(cls, report: DayReport):
        return cls(
            report_id=report.report_id,
            batch_id=report.batch_id,
            report_date=report.report_date.isoformat(),
            trade_count=report.trade_count,
            pnl_summary=report.pnl_summary,
            risk_metrics=report.risk_metrics,
            alert_count=report.alert_count,
            alert_summary=report.alert_summary,
            export_time=report.export_time.isoformat(),
            report_status=report.report_status.value,
            created_at=report.created_at.isoformat(),
            finalized_at=report.finalized_at.isoformat() if report.finalized_at else None
        )


class AlertRecordResponse(BaseModel):
    """Alert record response"""
    alert_id: str
    batch_id: str
    severity: str
    alert_type: str
    message: str
    timestamp: str
    context: Dict[str, Any]
    escalation_flag: bool
    escalated_to: Optional[str] = None
    resolved: bool
    resolved_at: Optional[str] = None

    @classmethod
    def from_entity(cls, alert: AlertRecord):
        return cls(
            alert_id=alert.alert_id,
            batch_id=alert.batch_id,
            severity=alert.severity.value,
            alert_type=alert.alert_type,
            message=alert.message,
            timestamp=alert.timestamp.isoformat(),
            context=alert.context,
            escalation_flag=alert.escalation_flag,
            escalated_to=alert.escalated_to,
            resolved=alert.resolved,
            resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None
        )


class ComplianceBundleResponse(BaseModel):
    """Compliance bundle response"""
    bundle_id: str
    batch_id: str
    tax_summary: Dict[str, Any]
    receipt_hashes: List[str]
    audit_trail: List[Dict[str, Any]]
    bundle_status: str
    certification_time: Optional[str] = None
    certifying_authority: Optional[str] = None
    bundle_hash: Optional[str] = None
    created_at: str

    @classmethod
    def from_entity(cls, bundle: ComplianceBundle):
        return cls(
            bundle_id=bundle.bundle_id,
            batch_id=bundle.batch_id,
            tax_summary=bundle.tax_summary,
            receipt_hashes=bundle.receipt_hashes,
            audit_trail=bundle.audit_trail,
            bundle_status=bundle.bundle_status.value,
            certification_time=bundle.certification_time.isoformat() if bundle.certification_time else None,
            certifying_authority=bundle.certifying_authority,
            bundle_hash=bundle.bundle_hash,
            created_at=bundle.created_at.isoformat()
        )


class ArchiveRecordResponse(BaseModel):
    """Archive record response"""
    archive_record_id: str
    batch_id: str
    storage_path: str
    retention_years: int
    immutable_hash: str
    retrieval_metadata: Dict[str, Any]
    archive_status: str
    hp_receipt: Optional[Dict[str, Any]] = None
    created_at: str
    verified_at: Optional[str] = None

    @classmethod
    def from_entity(cls, archive: ArchiveRecord):
        return cls(
            archive_record_id=archive.archive_record_id,
            batch_id=archive.batch_id,
            storage_path=archive.storage_path,
            retention_years=archive.retention_years,
            immutable_hash=archive.immutable_hash,
            retrieval_metadata=archive.retrieval_metadata,
            archive_status=archive.archive_status.value,
            hp_receipt=archive.hp_receipt,
            created_at=archive.created_at.isoformat(),
            verified_at=archive.verified_at.isoformat() if archive.verified_at else None
        )


class GateDecisionResponse(BaseModel):
    """Gate decision response"""
    gate_id: int
    verdict: str
    evidence_id: str
    event_time: str
    knowledge_time: str

    @classmethod
    def from_tuple(cls, gate: GateDecisionTuple):
        return cls(
            gate_id=gate.gate_id,
            verdict=gate.verdict.value,
            evidence_id=gate.evidence_id,
            event_time=gate.event_time.isoformat(),
            knowledge_time=gate.knowledge_time.isoformat()
        )


class BatchVerdictResponse(BaseModel):
    """Batch verdict response"""
    verdict_id: str
    batch_id: str
    guardian_gate_results: List[GateDecisionResponse]
    compliance_passed: bool
    tax_verified: bool
    archive_verified: bool
    batch_status: str
    verdict_reasoning: Optional[str] = None
    authority_used: str = "ZERO"
    event_time: str
    knowledge_time: str
    policy_hash: Optional[str] = None
    created_at: str

    @classmethod
    def from_entity(cls, verdict: BatchVerdict):
        return cls(
            verdict_id=verdict.verdict_id,
            batch_id=verdict.batch_id,
            guardian_gate_results=[GateDecisionResponse.from_tuple(g) for g in verdict.guardian_gate_results],
            compliance_passed=verdict.compliance_passed,
            tax_verified=verdict.tax_verified,
            archive_verified=verdict.archive_verified,
            batch_status=verdict.batch_status.value,
            verdict_reasoning=verdict.verdict_reasoning,
            authority_used=verdict.authority_used.value,
            event_time=verdict.event_time.isoformat(),
            knowledge_time=verdict.knowledge_time.isoformat(),
            policy_hash=verdict.policy_hash,
            created_at=verdict.created_at.isoformat()
        )


class BatchStatusResponse(BaseModel):
    """Complete batch status snapshot"""
    batch: BatchRunResponse
    verdict: Optional[BatchVerdictResponse] = None
    report: Optional[DayReportResponse] = None
    alerts: List[AlertRecordResponse] = []


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="NinjaTrader Batch Engine",
    description="Phase 2 Production Implementation (Authority=ZERO, Immutable)",
    version="1.0.0"
)

# Global engine instance
engine = BatchEngine()


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(ImmutabilityViolation)
async def immutability_violation_handler(request: Request, exc: ImmutabilityViolation):
    return {
        "error": "immutability_violation",
        "detail": str(exc),
        "constraint": "CG02"
    }


@app.exception_handler(WriteOnceViolation)
async def write_once_violation_handler(request: Request, exc: WriteOnceViolation):
    return {
        "error": "write_once_violation",
        "detail": str(exc),
        "constraint": "CG06"
    }


@app.exception_handler(RequiredVerdictMissing)
async def required_verdict_missing_handler(request: Request, exc: RequiredVerdictMissing):
    return {
        "error": "required_verdict_missing",
        "detail": str(exc),
        "constraint": "CG04"
    }


@app.exception_handler(MissingHPReceipt)
async def missing_hp_receipt_handler(request: Request, exc: MissingHPReceipt):
    return {
        "error": "missing_hp_receipt",
        "detail": str(exc),
        "constraint": "CG07"
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.post("/batch/create", response_model=BatchRunResponse, status_code=201)
async def create_batch(request: CreateBatchRequest):
    """
    Create new batch run (CG01: mode validated)
    Starts batch lifecycle: PENDING → PROCESSING → CLOSED → ARCHIVED
    """
    try:
        mode = BatchMode(request.mode)
        batch = engine.create_batch(
            run_date=request.run_date,
            market_open_time=request.market_open_time,
            market_close_time=request.market_close_time,
            mode=mode,
            correlation_id=request.correlation_id
        )
        logger.info(f"Created batch {batch.batch_id} with mode {mode.value}")
        return BatchRunResponse.from_entity(batch)
    except ValueError as e:
        logger.error(f"Batch creation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/batch/{batch_id}/process", response_model=Dict[str, Any], status_code=202)
async def process_batch(batch_id: str, report_request: CreateDayReportRequest):
    """
    Process batch: receive NinjaTrader export data, generate report + alerts
    Returns report_id for tracking
    """
    try:
        batch = engine.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        if batch.batch_status != BatchStatus.PENDING:
            raise HTTPException(status_code=409,
                              detail=f"Batch must be PENDING, got {batch.batch_status.value}")

        # Create day report
        report = engine.create_day_report(
            batch_id=batch_id,
            pnl_summary=report_request.pnl_summary,
            risk_metrics=report_request.risk_metrics,
            trade_count=report_request.trade_count,
            alert_summary=report_request.alert_summary
        )

        logger.info(f"Created report {report.report_id} for batch {batch_id}")
        return {"report_id": report.report_id, "status": "processing"}

    except ValueError as e:
        logger.error(f"Batch processing error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except ImmutabilityViolation as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/batch/{batch_id}/verdict", response_model=BatchVerdictResponse, status_code=201)
async def issue_verdict(batch_id: str, request: IssueBatchVerdictRequest):
    """
    Issue batch verdict based on Guardian gate results (CG03, CG04)
    Requires all 8 gates: APPROVED only if ALL gates PASS + compliance + tax + archive verified
    Verdict status logic:
    - APPROVED: all 8 gates PASS AND compliance_passed AND tax_verified AND archive_verified
    - BLOCKED: any gate BLOCKED OR any verification failed
    - NOT_PROVEN: any gate NOT_PROVEN
    """
    try:
        batch = engine.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        # Convert gate requests to tuples
        gates = []
        for gate_req in request.guardian_gate_results:
            gate = GateDecisionTuple(
                gate_id=gate_req.gate_id,
                verdict=GateVerdictStatus(gate_req.verdict),
                evidence_id=gate_req.evidence_id,
                event_time=gate_req.event_time,
                knowledge_time=gate_req.knowledge_time
            )
            gates.append(gate)

        # Issue verdict
        verdict = engine.issue_verdict(
            batch_id=batch_id,
            guardian_gate_results=gates,
            compliance_passed=request.compliance_passed,
            tax_verified=request.tax_verified,
            archive_verified=request.archive_verified
        )

        logger.info(f"Issued verdict {verdict.verdict_id} for batch {batch_id}: {verdict.batch_status.value}")
        return BatchVerdictResponse.from_entity(verdict)

    except ValueError as e:
        logger.error(f"Verdict issuance error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/batch/{batch_id}/archive", response_model=ArchiveRecordResponse, status_code=201)
async def create_archive(batch_id: str, request: CreateArchiveRecordRequest):
    """
    Save batch data to durable storage (HP 24/7 Infrastructure)
    Creates write-once ArchiveRecord with immutable hash
    Returns ArchiveRecord with storage path and immutable seal
    """
    try:
        batch = engine.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        # Create archive record
        archive = engine.create_archive_record(
            batch_id=batch_id,
            storage_path=request.storage_path,
            retrieval_metadata=request.retrieval_metadata,
            report_id=request.report_id,
            bundle_id=request.bundle_id,
            retention_years=request.retention_years
        )

        logger.info(f"Created archive {archive.archive_record_id} for batch {batch_id}")
        return ArchiveRecordResponse.from_entity(archive)

    except ValueError as e:
        logger.error(f"Archive creation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/batch/{batch_id}/archive/{archive_id}/verify", response_model=ArchiveRecordResponse)
async def verify_archive(batch_id: str, archive_id: str, request: VerifyArchiveRequest):
    """
    Verify archive with HP receipt (CG07: HP_DURABLE_RECEIPT)
    Updates archive status to VERIFIED when HP confirms write
    """
    try:
        archive = engine.get_archive_record(archive_id)
        if not archive:
            raise HTTPException(status_code=404, detail=f"Archive {archive_id} not found")

        if archive.batch_id != batch_id:
            raise HTTPException(status_code=400, detail="Archive does not belong to this batch")

        # Update with HP receipt
        archive.hp_receipt = request.hp_receipt
        archive.archive_status = ArchiveStatus.VERIFIED
        archive.verified_at = datetime.utcnow()

        logger.info(f"Verified archive {archive_id} for batch {batch_id}")
        return ArchiveRecordResponse.from_entity(archive)

    except ValueError as e:
        logger.error(f"Archive verification error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/batch/{batch_id}/close", response_model=BatchRunResponse)
async def close_batch(batch_id: str):
    """
    Close batch (mark immutable, CG02)
    Requires complete verdict to exist (CG04)
    After closure, no further mutations allowed (data locked)
    """
    try:
        batch = engine.close_batch(batch_id)
        logger.info(f"Closed batch {batch_id}")
        return BatchRunResponse.from_entity(batch)

    except RequiredVerdictMissing as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        logger.error(f"Batch close error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/batch/{batch_id}", response_model=BatchRunResponse)
async def get_batch(batch_id: str):
    """
    Retrieve batch run (immutable read)
    Once closed, all data is read-only and locked
    """
    batch = engine.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    return BatchRunResponse.from_entity(batch)


@app.get("/batch/{batch_id}/verdict", response_model=BatchVerdictResponse)
async def get_verdict(batch_id: str):
    """
    Retrieve BatchVerdictTuple (all-or-nothing authorization)
    Returns APPROVED, BLOCKED, or NOT_PROVEN status
    """
    verdict = engine.get_verdict(batch_id)
    if not verdict:
        raise HTTPException(status_code=404, detail=f"Verdict for batch {batch_id} not found")

    return BatchVerdictResponse.from_entity(verdict)


@app.get("/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """
    Get complete batch status snapshot
    Includes: batch info, verdict, report, alerts
    """
    batch = engine.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    verdict = engine.get_verdict(batch_id)
    alerts = engine.get_all_alerts_for_batch(batch_id)

    # Get report from database
    day_report = engine.get_day_report(batch_id)
    report = DayReportResponse.from_entity(day_report) if day_report else None

    return BatchStatusResponse(
        batch=BatchRunResponse.from_entity(batch),
        verdict=BatchVerdictResponse.from_entity(verdict) if verdict else None,
        report=report,
        alerts=[AlertRecordResponse.from_entity(a) for a in alerts]
    )


@app.post("/batch/{batch_id}/alert", response_model=AlertRecordResponse, status_code=201)
async def create_alert(batch_id: str, request: CreateAlertRequest):
    """
    Create alert record
    Severity ranked: CRITICAL > HIGH > MEDIUM > LOW
    """
    try:
        alert = engine.create_alert(
            batch_id=batch_id,
            severity=AlertSeverity(request.severity),
            alert_type=request.alert_type,
            message=request.message,
            context=request.context
        )
        logger.info(f"Created alert {alert.alert_id} ({request.severity}) for batch {batch_id}")
        return AlertRecordResponse.from_entity(alert)

    except ValueError as e:
        logger.error(f"Alert creation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except ImmutabilityViolation as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/batch/{batch_id}/compliance", response_model=ComplianceBundleResponse, status_code=201)
async def create_compliance_bundle(batch_id: str, request: CreateComplianceBundleRequest):
    """
    Create compliance bundle (tax summary + receipt hashes + audit trail)
    """
    try:
        bundle = engine.create_compliance_bundle(
            batch_id=batch_id,
            tax_summary=request.tax_summary,
            receipt_hashes=request.receipt_hashes
        )
        logger.info(f"Created compliance bundle {bundle.bundle_id} for batch {batch_id}")
        return ComplianceBundleResponse.from_entity(bundle)

    except ValueError as e:
        logger.error(f"Compliance bundle creation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except ImmutabilityViolation as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/batch/{batch_id}/compliance/{bundle_id}/certify", response_model=ComplianceBundleResponse)
async def certify_compliance_bundle(batch_id: str, bundle_id: str):
    """
    Certify compliance bundle (CG05: locks immutability)
    Once certified, bundle is locked and cannot be modified
    """
    try:
        bundle = engine.certify_compliance_bundle(bundle_id, certifying_authority="BATCH_ENGINE")
        logger.info(f"Certified compliance bundle {bundle_id} for batch {batch_id}")
        return ComplianceBundleResponse.from_entity(bundle)

    except ImmutabilityViolation as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        logger.error(f"Compliance bundle certification error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "authority": "ZERO",
        "live_enabled": "false",
        "failure_policy": "FAIL_CLOSED"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
