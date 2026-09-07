"""
Guardian FastAPI Endpoints - Phase 2 Implementation
Authority: ZERO (LOCKED IMMUTABLE)
Date: 2026-09-07

Endpoints:
- POST /evaluate - Input candidate, machine health, evidence → GateDecisionTuple
- GET /verdict/{verdict_id} - Immutable read
- GET /gates - List 8 gates + summary
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import sqlite3
import json
import os
import logging
from pathlib import Path

from guardian_engine import (
    GuardianEngine, DeploymentCandidate, EvidenceRecord, GateVerdict,
    AuthorityLevel, VerdictType, GateID, DecisionCartridge
)

logger = logging.getLogger(__name__)


# ============================================================================
# FASTAPI REQUEST/RESPONSE MODELS
# ============================================================================

class ArtifactHashesModel(BaseModel):
    strategy: str = Field(..., description="Strategy SHA256 hash")
    engine: str = Field(..., description="Engine SHA256 hash")
    ui: str = Field(..., description="UI SHA256 hash")


class EvaluateRequestModel(BaseModel):
    """Request model for POST /evaluate"""
    candidate_id: Optional[str] = Field(None, description="Unique candidate ID (UUID)")
    correlation_id: str = Field(..., description="Traceability UUID")
    artifact_hashes: ArtifactHashesModel = Field(..., description="Artifact hashes")
    passport_hash: str = Field(..., description="CONTROL passport hash")
    side: str = Field(..., description="BUY or SELL")
    source_system: str = Field(..., description="Origin system")
    authority: str = Field("ZERO", description="Authority level (ZERO only)")
    evidence: List[Dict[str, Any]] = Field(..., description="Evidence records")
    owner_approval_id: Optional[str] = Field(None, description="Owner approval UUID")


class GateVerdictModel(BaseModel):
    """Response model for gate verdicts"""
    verdict_id: str
    gate_id: str
    correlation_id: str
    verdict: str  # PASS, BLOCKED, NOT_PROVEN
    reasoning: str
    evidence_id: Optional[str]
    event_time: str
    knowledge_time: str


class DecisionCartridgeModel(BaseModel):
    """Response model for decision cartridge"""
    cartridge_id: str
    correlation_id: str
    candidate_id: str
    gate_verdicts: List[Dict[str, Any]]
    final_verdict: str
    evidence_root_hash: str
    policy_root_hash: str
    authority: str
    created_at: str


class GateInfoModel(BaseModel):
    """Response model for gate info"""
    gate_id: str
    gate_order: int
    gate_name: str
    stale_threshold_seconds: int
    blocking_conditions: List[str]


# ============================================================================
# SQLITE DATABASE INITIALIZATION
# ============================================================================

def init_database(db_path: str = None):
    """Initialize SQLite database with immutable schemas"""
    if db_path is None:
        # Use environment variable FLIPFLOP_DB_PATH, fallback to ./databases/
        db_dir = os.getenv('FLIPFLOP_DB_PATH', './databases/')
        db_path = os.path.join(db_dir, 'guardian.db')

        # Create directory if it doesn't exist
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Guardian API: Using database path {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # gate_verdicts table (immutable, append-only)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gate_verdicts (
            verdict_id TEXT PRIMARY KEY,
            gate_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            candidate_id TEXT,
            verdict TEXT NOT NULL CHECK(verdict IN ('PASS', 'BLOCKED', 'NOT_PROVEN')),
            reasoning TEXT NOT NULL,
            evidence_id TEXT,
            event_time TEXT NOT NULL,
            knowledge_time TEXT NOT NULL,
            authority_used TEXT NOT NULL DEFAULT 'ZERO',
            policy_hash TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(gate_id, correlation_id, verdict_id)
        )
    """)

    # evidence_records table (immutable)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence_records (
            evidence_id TEXT PRIMARY KEY,
            evidence_type TEXT NOT NULL,
            source_system TEXT NOT NULL,
            observation TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            checksum TEXT NOT NULL,
            is_contradicted BOOLEAN DEFAULT 0,
            contradicted_by TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # decision_cartridge table (immutable, sealed)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_cartridge (
            cartridge_id TEXT PRIMARY KEY,
            correlation_id TEXT NOT NULL,
            candidate_id TEXT NOT NULL,
            gate_verdicts TEXT NOT NULL,
            final_verdict TEXT NOT NULL CHECK(final_verdict IN ('PASS', 'BLOCKED', 'NOT_PROVEN')),
            evidence_root_hash TEXT NOT NULL,
            policy_root_hash TEXT NOT NULL,
            authority TEXT NOT NULL DEFAULT 'ZERO',
            created_at TEXT NOT NULL,
            owner_approval_id TEXT,
            UNIQUE(correlation_id, cartridge_id)
        )
    """)

    # Create indices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gate_verdicts_correlation ON gate_verdicts(correlation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gate_verdicts_gate ON gate_verdicts(gate_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cartridge_correlation ON decision_cartridge(correlation_id)")

    conn.commit()
    conn.close()


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Guardian Enforcement Engine",
    description="8-gate sequential pipeline with fail-closed logic",
    version="1.0.0"
)

# Initialize database on startup
init_database()

# Initialize Guardian Engine
guardian = GuardianEngine()

# Get database path from environment variable (same as init_database)
_db_dir = os.getenv('FLIPFLOP_DB_PATH', './databases/')
DB_PATH = os.path.join(_db_dir, 'guardian.db')


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def save_verdict_to_db(verdict: GateVerdict, candidate_id: Optional[str] = None):
    """Save immutable verdict to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO gate_verdicts
            (verdict_id, gate_id, correlation_id, candidate_id, verdict, reasoning,
             evidence_id, event_time, knowledge_time, authority_used, policy_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(verdict.verdict_id),
            verdict.gate_id.value,
            str(verdict.correlation_id),
            candidate_id,
            verdict.verdict.value,
            verdict.reasoning,
            str(verdict.evidence_id) if verdict.evidence_id else None,
            verdict.event_time.isoformat(),
            verdict.knowledge_time.isoformat(),
            verdict.authority_used.value,
            verdict.policy_hash,
            datetime.utcnow().isoformat()
        ))
        conn.commit()
    finally:
        conn.close()


def save_evidence_to_db(evidence: EvidenceRecord):
    """Save immutable evidence to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO evidence_records
            (evidence_id, evidence_type, source_system, observation, observed_at,
             recorded_at, checksum, is_contradicted, contradicted_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(evidence.evidence_id),
            evidence.evidence_type,
            evidence.source_system,
            json.dumps(evidence.observation),
            evidence.observed_at.isoformat(),
            evidence.recorded_at.isoformat(),
            evidence.checksum,
            1 if evidence.is_contradicted else 0,
            json.dumps([str(x) for x in evidence.contradicted_by]) if evidence.contradicted_by else None,
            datetime.utcnow().isoformat()
        ))
        conn.commit()
    finally:
        conn.close()


def save_cartridge_to_db(cartridge: DecisionCartridge):
    """Save immutable decision cartridge to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO decision_cartridge
            (cartridge_id, correlation_id, candidate_id, gate_verdicts, final_verdict,
             evidence_root_hash, policy_root_hash, authority, created_at, owner_approval_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(cartridge.cartridge_id),
            str(cartridge.correlation_id),
            str(cartridge.candidate_id),
            json.dumps(cartridge.gate_verdicts),
            cartridge.final_verdict.value,
            cartridge.evidence_root_hash,
            cartridge.policy_root_hash,
            cartridge.authority.value,
            cartridge.created_at.isoformat(),
            str(cartridge.owner_approval_id) if cartridge.owner_approval_id else None
        ))
        conn.commit()
    finally:
        conn.close()


def get_verdict_from_db(verdict_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve immutable verdict from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT verdict_id, gate_id, correlation_id, candidate_id, verdict, reasoning,
                   evidence_id, event_time, knowledge_time, authority_used, policy_hash, created_at
            FROM gate_verdicts
            WHERE verdict_id = ?
        """, (verdict_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "verdict_id": row[0],
            "gate_id": row[1],
            "correlation_id": row[2],
            "candidate_id": row[3],
            "verdict": row[4],
            "reasoning": row[5],
            "evidence_id": row[6],
            "event_time": row[7],
            "knowledge_time": row[8],
            "authority_used": row[9],
            "policy_hash": row[10],
            "created_at": row[11]
        }
    finally:
        conn.close()


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Guardian Enforcement Engine",
        "version": "1.0.0",
        "authority": "ZERO"
    }


@app.post("/evaluate", response_model=DecisionCartridgeModel)
async def evaluate_candidate(request: EvaluateRequestModel = Body(...)):
    """
    POST /evaluate - Evaluate deployment candidate through all 8 gates.

    Input: Strategy artifact, machine health, evidence
    Output: GateDecisionTuple (immutable decision cartridge)
    """
    try:
        # Create deployment candidate
        candidate_id = UUID(request.candidate_id) if request.candidate_id else uuid4()
        correlation_id = UUID(request.correlation_id)

        candidate = DeploymentCandidate(
            candidate_id=candidate_id,
            correlation_id=correlation_id,
            artifact_hashes={
                "strategy": request.artifact_hashes.strategy,
                "engine": request.artifact_hashes.engine,
                "ui": request.artifact_hashes.ui,
            },
            passport_hash=request.passport_hash,
            side=request.side,
            source_system=request.source_system,
            authority=AuthorityLevel.ZERO,
            owner_approval_id=UUID(request.owner_approval_id) if request.owner_approval_id else None,
        )

        # Convert request evidence to EvidenceRecord objects
        evidence_records = []
        for evidence_input in request.evidence:
            evidence = EvidenceRecord(
                evidence_id=UUID(evidence_input.get("evidence_id", str(uuid4()))),
                evidence_type=evidence_input.get("evidence_type"),
                source_system=evidence_input.get("source_system"),
                observation=evidence_input.get("observation", {}),
                observed_at=datetime.fromisoformat(evidence_input.get("observed_at", datetime.utcnow().isoformat())),
                recorded_at=datetime.fromisoformat(evidence_input.get("recorded_at", datetime.utcnow().isoformat())),
                checksum=evidence_input.get("checksum", ""),
                is_contradicted=evidence_input.get("is_contradicted", False),
                contradicted_by=[UUID(x) for x in evidence_input.get("contradicted_by", [])],
            )
            evidence_records.append(evidence)
            save_evidence_to_db(evidence)

        # Evaluate through all 8 gates
        cartridge = guardian.evaluate(candidate, evidence_records)

        # Save verdict records to database
        for gate_verdict_dict in cartridge.gate_verdicts:
            # We need to get the actual verdict objects - for now, reconstruct them
            pass

        # Save decision cartridge to database
        save_cartridge_to_db(cartridge)

        # Return decision cartridge
        return DecisionCartridgeModel(
            cartridge_id=str(cartridge.cartridge_id),
            correlation_id=str(cartridge.correlation_id),
            candidate_id=str(cartridge.candidate_id),
            gate_verdicts=cartridge.gate_verdicts,
            final_verdict=cartridge.final_verdict.value,
            evidence_root_hash=cartridge.evidence_root_hash,
            policy_root_hash=cartridge.policy_root_hash,
            authority=cartridge.authority.value,
            created_at=cartridge.created_at.isoformat(),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.get("/verdict/{verdict_id}", response_model=GateVerdictModel)
async def get_verdict(verdict_id: str):
    """
    GET /verdict/{verdict_id} - Immutable read of gate verdict.
    """
    verdict = get_verdict_from_db(verdict_id)

    if not verdict:
        raise HTTPException(status_code=404, detail=f"Verdict {verdict_id} not found")

    return GateVerdictModel(
        verdict_id=verdict["verdict_id"],
        gate_id=verdict["gate_id"],
        correlation_id=verdict["correlation_id"],
        verdict=verdict["verdict"],
        reasoning=verdict["reasoning"],
        evidence_id=verdict["evidence_id"],
        event_time=verdict["event_time"],
        knowledge_time=verdict["knowledge_time"],
    )


@app.get("/gates", response_model=List[GateInfoModel])
async def list_gates():
    """
    GET /gates - List all 8 gates with summary information.
    """
    gates_info = [
        {
            "gate_id": "gate_1",
            "gate_order": 1,
            "gate_name": "SCHEMA_AND_IDENTITY",
            "stale_threshold_seconds": 300,
            "blocking_conditions": [
                "Schema validation fails",
                "Missing artifact hash",
                "Duplicate correlation_id"
            ]
        },
        {
            "gate_id": "gate_2",
            "gate_order": 2,
            "gate_name": "HASH_INTEGRITY",
            "stale_threshold_seconds": 300,
            "blocking_conditions": [
                "Hash mismatch",
                "Hash contradiction",
                "Passport mismatch"
            ]
        },
        {
            "gate_id": "gate_3",
            "gate_order": 3,
            "gate_name": "AUTHORITY_POLICY_COMPLIANCE",
            "stale_threshold_seconds": 300,
            "blocking_conditions": [
                "authority != ZERO",
                "live_enabled = true",
                "broker_orders_allowed = true",
                "control_mutation_allowed = true"
            ]
        },
        {
            "gate_id": "gate_4",
            "gate_order": 4,
            "gate_name": "MACHINE_HEALTH_AND_READINESS",
            "stale_threshold_seconds": 60,
            "blocking_conditions": [
                "Machine in error state",
                "Heartbeat stale > 60s",
                "Clock skew > 5s",
                "Fencing token expired"
            ]
        },
        {
            "gate_id": "gate_5",
            "gate_order": 5,
            "gate_name": "CANARY_EXECUTION",
            "stale_threshold_seconds": 300,
            "blocking_conditions": [
                "error_rate > 5%",
                "latency_p99 > 200ms",
                "rollback_triggered = true"
            ]
        },
        {
            "gate_id": "gate_6",
            "gate_order": 6,
            "gate_name": "EVIDENCE_CONSISTENCY",
            "stale_threshold_seconds": 300,
            "blocking_conditions": [
                "Hash contradiction",
                "Policy contradiction",
                "Temporal ordering violation",
                "Evidence marked contradicted"
            ]
        },
        {
            "gate_id": "gate_7",
            "gate_order": 7,
            "gate_name": "FRESHNESS_AND_STALENESS",
            "stale_threshold_seconds": 300,
            "blocking_conditions": [
                "Evidence > 300s old (HARD LIMIT)",
                "Required evidence missing"
            ]
        },
        {
            "gate_id": "gate_8",
            "gate_order": 8,
            "gate_name": "FINAL_ARBITER",
            "stale_threshold_seconds": 300,
            "blocking_conditions": [
                "Any prior gate = BLOCKED",
                "Any prior gate = NOT_PROVEN",
                "Authority escalation attempted",
                "Owner approval missing when required"
            ]
        }
    ]

    return [GateInfoModel(**gate) for gate in gates_info]


@app.get("/cartridge/{correlation_id}")
async def get_decision_cartridge(correlation_id: str):
    """
    GET /cartridge/{correlation_id} - Retrieve decision cartridge for candidate.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT cartridge_id, correlation_id, candidate_id, gate_verdicts, final_verdict,
                   evidence_root_hash, policy_root_hash, authority, created_at, owner_approval_id
            FROM decision_cartridge
            WHERE correlation_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (correlation_id,))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Cartridge for {correlation_id} not found")

        return {
            "cartridge_id": row[0],
            "correlation_id": row[1],
            "candidate_id": row[2],
            "gate_verdicts": json.loads(row[3]),
            "final_verdict": row[4],
            "evidence_root_hash": row[5],
            "policy_root_hash": row[6],
            "authority": row[7],
            "created_at": row[8],
            "owner_approval_id": row[9],
        }
    finally:
        conn.close()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
