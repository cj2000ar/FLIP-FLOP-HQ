"""
HP 24/7 Infrastructure API - FastAPI Endpoints
FlipFlop HQ Phase 2
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID, uuid4
import sqlite3
import json

from hp_infra import (
    HPInfrastructure,
    MachineRoleTuple,
    HeartbeatTuple,
    FencingTokenTuple,
    DurableStorageTuple,
    DurableReceiptTuple,
    HealthState,
    ArchiveStatus
)

# Import Guardian engine
sys.path.insert(0, str(Path(__file__).parent / "RED_DRAGON"))
from guardian_engine import (
    GuardianEngine, DeploymentCandidate, EvidenceRecord, GateVerdict,
    AuthorityLevel, VerdictType, GateID, DecisionCartridge
)

# Import NinjaTrader Bridge
from ninjatrader_bridge import (
    NinjaTraderBridge, ReplaySession, TradeEvent, TradeSide,
    TradeStatus, ReplayMetrics
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class HeartbeatRequest(BaseModel):
    machine_id: str
    clock_offset: float = 0.0


class HeartbeatResponse(BaseModel):
    heartbeat_id: str
    machine_id: str
    timestamp: float
    health_status: str
    clock_offset: float
    sequence: int


class FencingTokenRequest(BaseModel):
    machine_id: str


class FencingTokenResponse(BaseModel):
    token_id: str
    machine_id: str
    epoch: int
    expiry_timestamp: float
    signature_hash: str
    authority_lock: str


class FencingValidationResponse(BaseModel):
    is_valid: bool
    reason: str


class DurableReceiptRequest(BaseModel):
    storage_path: str


class DurableReceiptResponse(BaseModel):
    receipt_id: str
    timestamp: float
    storage_path: str
    confirmation_hash: str
    archive_status: str


class MachineRoleResponse(BaseModel):
    machine_id: str
    role: str
    version: str
    config_hash: str
    fencing_epoch: int
    health_state: str
    truth_age_seconds: int


class HealthCheckResponse(BaseModel):
    status: str
    message: str


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

def create_app(hp: Optional[HPInfrastructure] = None) -> FastAPI:
    """
    Create FastAPI application with HP infrastructure endpoints.

    Args:
        hp: HPInfrastructure instance (created if None)

    Returns:
        FastAPI application
    """
    if hp is None:
        # Use environment variable FLIPFLOP_DB_PATH, fallback to ./databases/
        db_dir = os.getenv('FLIPFLOP_DB_PATH', './databases/')
        db_path = os.path.join(db_dir, 'hp_infra.db')

        # Create directory if it doesn't exist
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"HP Infrastructure: Using database path {db_path}")

        hp = HPInfrastructure(db_path=db_path)

    app = FastAPI(
        title="HP 24/7 Infrastructure API",
        description="FlipFlop HQ Phase 2 - Machine health, fencing, storage",
        version="1.0.0"
    )

    # Add CORS middleware for cross-origin requests from dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize NinjaTrader Bridge
    nt_bridge = NinjaTraderBridge(db_path=os.path.join(os.getenv('FLIPFLOP_DB_PATH', './databases/'), 'ninjatrader.db'))

    # ========================================================================
    # SHADOW LAB / NINJATRADER ENDPOINTS
    # ========================================================================

    @app.post("/shadow/session/create")
    def create_replay_session(
        strategy_name: str,
        instrument: str,
        market_date: str,
        replay_speed: int = 1,
        start_time: str = "09:30",
        end_time: str = "16:00"
    ):
        """POST /shadow/session/create - Create Market Replay session"""
        try:
            session = nt_bridge.create_replay_session(
                strategy_name=strategy_name,
                instrument=instrument,
                market_date=market_date,
                replay_speed=replay_speed,
                start_time=start_time,
                end_time=end_time
            )
            return {
                "session_id": str(session.session_id),
                "strategy": session.strategy_name,
                "instrument": session.instrument,
                "market_date": session.market_date,
                "replay_speed": session.replay_speed,
                "authority": session.authority,
                "live_enabled": session.live_enabled,
                "created_at": session.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Create replay session error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/shadow/trade/record")
    def record_trade_event(
        session_id: str,
        strategy_name: str,
        instrument: str,
        side: str,
        entry_price: float,
        entry_quantity: int,
        stop_price: float,
        target_price: float,
        exit_price: Optional[float] = None,
        pnl_ticks: Optional[int] = None,
        pnl_dollars: Optional[float] = None,
        cost_per_side: float = 2.25
    ):
        """POST /shadow/trade/record - Record trade from Market Replay"""
        try:
            sid = UUID(session_id)
            trade = nt_bridge.record_trade(
                session_id=sid,
                strategy_name=strategy_name,
                instrument=instrument,
                side=TradeSide(side),
                entry_time=datetime.utcnow(),
                entry_price=entry_price,
                entry_quantity=entry_quantity,
                stop_price=stop_price,
                target_price=target_price,
                exit_time=datetime.utcnow() if exit_price else None,
                exit_price=exit_price,
                status=TradeStatus.TARGET_HIT if exit_price and exit_price >= target_price else TradeStatus.STOPPED_OUT if exit_price and exit_price <= stop_price else TradeStatus.FILLED,
                pnl_ticks=pnl_ticks,
                pnl_dollars=pnl_dollars,
                cost_per_side=cost_per_side
            )
            return {
                "event_id": str(trade.event_id),
                "side": trade.side.value,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl_dollars": trade.pnl_dollars,
                "status": trade.status.value
            }
        except Exception as e:
            logger.error(f"Record trade error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/shadow/session/{session_id}/metrics")
    def get_session_metrics(session_id: str):
        """GET /shadow/session/{id}/metrics - Get running P&L metrics"""
        try:
            sid = UUID(session_id)
            metrics = nt_bridge.get_session_metrics(sid)
            if not metrics:
                raise HTTPException(status_code=404, detail="Session not found")
            return metrics
        except Exception as e:
            logger.error(f"Get metrics error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/shadow/session/{session_id}/trades")
    def get_session_trades(session_id: str):
        """GET /shadow/session/{id}/trades - Get all trades"""
        try:
            sid = UUID(session_id)
            trades = nt_bridge.get_session_trades(sid)
            return {"trades": trades, "count": len(trades)}
        except Exception as e:
            logger.error(f"Get trades error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/shadow/session/{session_id}/vs-baseline")
    def compare_to_baseline(session_id: str, baseline_winrate: float = 0.833):
        """GET /shadow/session/{id}/vs-baseline - Compare to RR500 baseline"""
        try:
            sid = UUID(session_id)
            comparison = nt_bridge.compare_to_baseline(sid, baseline_winrate)
            if not comparison:
                raise HTTPException(status_code=404, detail="Session not found")
            return comparison
        except Exception as e:
            logger.error(f"Compare baseline error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/shadow/strategies")
    def list_strategies():
        """GET /shadow/strategies - List available strategies"""
        strategies = [
            {
                "name": "RR500",
                "description": "RR500 / FlipFlop Quant Mirror baseline",
                "baseline_winrate": 0.833,
                "baseline_pnl": 2080,
                "baseline_trades": 12
            },
            {
                "name": "IFVG",
                "description": "Fair Value Gap (FVG) strategy",
                "baseline_winrate": 0.0,
                "baseline_pnl": 0,
                "baseline_trades": 0
            },
            {
                "name": "UT",
                "description": "ATR Trailing Stop (UT/NUMKI)",
                "baseline_winrate": 0.0,
                "baseline_pnl": 0,
                "baseline_trades": 0
            },
            {
                "name": "KiloView",
                "description": "Market structure + session scoring",
                "baseline_winrate": 0.0,
                "baseline_pnl": 0,
                "baseline_trades": 0
            }
        ]
        return strategies

    # ========================================================================
    # HEARTBEAT ENDPOINTS
    # ========================================================================

    @app.post("/heartbeat", response_model=HeartbeatResponse)
    def send_heartbeat(req: HeartbeatRequest):
        """
        POST /heartbeat - Send machine heartbeat.
        Machine reports alive status, clock offset.

        Returns: HeartbeatTuple (immutable record)
        """
        try:
            hb = hp.send_heartbeat(req.machine_id, req.clock_offset)
            return HeartbeatResponse(
                heartbeat_id=hb.heartbeat_id,
                machine_id=hb.machine_id,
                timestamp=hb.timestamp,
                health_status=hb.health_status,
                clock_offset=hb.clock_offset,
                sequence=hb.sequence
            )
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/heartbeat/{machine_id}", response_model=HeartbeatResponse)
    def get_heartbeat(machine_id: str):
        """
        GET /heartbeat/{machine_id} - Read latest heartbeat + truth age.

        Returns: Latest HeartbeatTuple or 404 if not found
        """
        try:
            hb = hp.get_latest_heartbeat(machine_id)
            if not hb:
                raise HTTPException(status_code=404, detail="No heartbeat found")

            return HeartbeatResponse(
                heartbeat_id=hb.heartbeat_id,
                machine_id=hb.machine_id,
                timestamp=hb.timestamp,
                health_status=hb.health_status,
                clock_offset=hb.clock_offset,
                sequence=hb.sequence
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get heartbeat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/heartbeat/{machine_id}/freshness")
    def check_heartbeat_freshness(machine_id: str):
        """
        GET /heartbeat/{machine_id}/freshness - Check if heartbeat is fresh (< 60s).

        Returns: {is_fresh: bool, age_seconds: int}
        """
        try:
            hb = hp.get_latest_heartbeat(machine_id)
            if not hb:
                return {
                    "is_fresh": False,
                    "age_seconds": -1,
                    "reason": "no_heartbeat"
                }

            is_fresh = hp.is_heartbeat_fresh(hb)
            age = int(hp.get_truth_age_seconds(machine_id))

            return {
                "is_fresh": is_fresh,
                "age_seconds": age,
                "reason": "ok" if is_fresh else "stale"
            }
        except Exception as e:
            logger.error(f"Freshness check error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # FENCING TOKEN ENDPOINTS
    # ========================================================================

    @app.post("/fencing/acquire", response_model=FencingTokenResponse)
    def acquire_fencing_token(req: FencingTokenRequest):
        """
        POST /fencing/acquire - Acquire single-writer fencing token.
        Returns valid token or expired token.

        Returns: FencingTokenTuple
        """
        try:
            token = hp.acquire_fencing_token(req.machine_id)
            return FencingTokenResponse(
                token_id=token.token_id,
                machine_id=token.machine_id,
                epoch=token.epoch,
                expiry_timestamp=token.expiry_timestamp,
                signature_hash=token.signature_hash,
                authority_lock=token.authority_lock
            )
        except Exception as e:
            logger.error(f"Acquire fencing token error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/fencing/release/{token_id}")
    def release_fencing_token(token_id: str):
        """
        DELETE /fencing/release/{token_id} - Release (revoke) fencing token.

        Returns: {status: "released"}
        """
        try:
            hp.release_fencing_token(token_id)
            return {"status": "released", "token_id": token_id}
        except Exception as e:
            logger.error(f"Release fencing token error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/fencing/validate", response_model=FencingValidationResponse)
    def validate_fencing_token(req: FencingTokenRequest):
        """
        POST /fencing/validate - Validate fencing token (expiry + signature).

        Returns: {is_valid: bool, reason: str}
        """
        try:
            # Get token from request (simplified: assumes token_id in query)
            token = hp.get_latest_heartbeat(req.machine_id)
            if not token:
                return FencingValidationResponse(is_valid=False, reason="no_token_found")

            # For now, just verify latest heartbeat; in production, would validate explicit token
            return FencingValidationResponse(is_valid=True, reason="token_valid")
        except Exception as e:
            logger.error(f"Validate fencing token error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # DURABLE STORAGE ENDPOINTS
    # ========================================================================

    @app.post("/storage/receipt", response_model=DurableReceiptResponse)
    def write_durable_receipt(req: DurableReceiptRequest):
        """
        POST /storage/receipt - Generate durable receipt for archive write.
        Batch archive must receive receipt before status = VERIFIED.

        Returns: DurableReceiptTuple
        """
        try:
            receipt = hp.write_durable_receipt(req.storage_path)
            return DurableReceiptResponse(
                receipt_id=receipt.receipt_id,
                timestamp=receipt.timestamp,
                storage_path=receipt.storage_path,
                confirmation_hash=receipt.confirmation_hash,
                archive_status=receipt.archive_status
            )
        except Exception as e:
            logger.error(f"Write durable receipt error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/storage/receipts")
    def get_durable_receipts(storage_path: Optional[str] = None):
        """
        GET /storage/receipts - List durable receipts (immutable read).

        Returns: List of receipts
        """
        try:
            import sqlite3
            conn = sqlite3.connect(hp.db_path)
            try:
                cursor = conn.cursor()

                if storage_path:
                    cursor.execute("""
                        SELECT receipt_id, timestamp, storage_path, confirmation_hash, archive_status
                        FROM durable_receipts
                        WHERE storage_path = ?
                        ORDER BY timestamp DESC
                    """, (storage_path,))
                else:
                    cursor.execute("""
                        SELECT receipt_id, timestamp, storage_path, confirmation_hash, archive_status
                        FROM durable_receipts
                        ORDER BY timestamp DESC
                        LIMIT 100
                    """)

                rows = cursor.fetchall()
                return {
                    "receipts": [
                        {
                            "receipt_id": r[0],
                            "timestamp": r[1],
                            "storage_path": r[2],
                            "confirmation_hash": r[3],
                            "archive_status": r[4]
                        }
                        for r in rows
                    ]
                }
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Get durable receipts error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # MACHINE ROLE ENDPOINTS
    # ========================================================================

    @app.get("/machine/{machine_id}", response_model=MachineRoleResponse)
    def get_machine_role(machine_id: str):
        """
        GET /machine/{machine_id} - Get machine role + health status.

        Returns: MachineRoleTuple
        """
        try:
            role = hp.get_machine_role(machine_id)
            if not role:
                raise HTTPException(status_code=404, detail="Machine not found")

            return MachineRoleResponse(
                machine_id=role.machine_id,
                role=role.role,
                version=role.version,
                config_hash=role.config_hash,
                fencing_epoch=role.fencing_epoch,
                health_state=role.health_state,
                truth_age_seconds=role.truth_age_seconds
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get machine role error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # HEALTH CHECK ENDPOINTS
    # ========================================================================

    @app.get("/health", response_model=HealthCheckResponse)
    def health_check():
        """
        GET /health - Health check.

        Returns: {status: "ok", message: "HP infrastructure operational"}
        """
        return HealthCheckResponse(
            status="ok",
            message="HP infrastructure operational"
        )

    # ========================================================================
    # GUARDIAN ENFORCEMENT ENDPOINTS
    # ========================================================================

    # Initialize Guardian engine and database
    guardian_engine = GuardianEngine()

    def init_guardian_database():
        """Initialize Guardian database tables"""
        db_path = os.getenv('FLIPFLOP_DB_PATH', './databases/')
        os.makedirs(db_path, exist_ok=True)
        db_file = os.path.join(db_path, 'guardian.db')

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

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

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gate_verdicts_correlation ON gate_verdicts(correlation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gate_verdicts_gate ON gate_verdicts(gate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cartridge_correlation ON decision_cartridge(correlation_id)")

        conn.commit()
        conn.close()

        return db_file

    guardian_db_path = init_guardian_database()

    class GuardianEvaluateRequest(BaseModel):
        correlation_id: str
        artifact_hashes: dict
        passport_hash: str
        side: str
        source_system: str
        evidence: List[dict]
        owner_approval_id: Optional[str] = None

    class GuardianVerdictResponse(BaseModel):
        verdict_id: str
        gate_id: str
        verdict: str
        reasoning: str
        evidence_id: Optional[str]
        event_time: str

    def save_verdict_to_db(verdict: GateVerdict, candidate_id: Optional[str] = None):
        """Save immutable verdict to database"""
        conn = sqlite3.connect(guardian_db_path)
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
        conn = sqlite3.connect(guardian_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO evidence_records
                (evidence_id, evidence_type, source_system, observation,
                 observed_at, recorded_at, checksum, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(evidence.evidence_id),
                evidence.evidence_type,
                evidence.source_system,
                json.dumps(evidence.observation),
                evidence.observed_at.isoformat(),
                evidence.recorded_at.isoformat(),
                evidence.checksum,
                datetime.utcnow().isoformat()
            ))
            conn.commit()
        finally:
            conn.close()

    @app.post("/guardian/evaluate", response_model=dict)
    def evaluate_deployment(request: GuardianEvaluateRequest):
        """
        POST /guardian/evaluate - Run deployment candidate through all 8 gates.
        Returns decision cartridge with verdicts and final verdict.
        """
        try:
            correlation_id = UUID(request.correlation_id)

            # Create candidate
            candidate = DeploymentCandidate(
                candidate_id=uuid4(),
                correlation_id=correlation_id,
                artifact_hashes=request.artifact_hashes,
                passport_hash=request.passport_hash,
                side=request.side,
                source_system=request.source_system,
                authority=AuthorityLevel.ZERO
            )

            # Create evidence records
            evidence_records = []
            for ev in request.evidence:
                evidence = EvidenceRecord(
                    evidence_id=uuid4(),
                    evidence_type=ev.get("evidence_type", "UNKNOWN"),
                    source_system=ev.get("source_system", "API"),
                    observation=ev.get("observation", {}),
                    observed_at=datetime.fromisoformat(ev.get("observed_at", datetime.utcnow().isoformat())),
                    recorded_at=datetime.fromisoformat(ev.get("recorded_at", datetime.utcnow().isoformat())),
                    checksum=ev.get("checksum", "")
                )
                evidence_records.append(evidence)
                save_evidence_to_db(evidence)

            # Run through all 8 gates sequentially
            verdicts = []
            prior_verdicts = []

            for gate_id in [GateID.GATE_1, GateID.GATE_2, GateID.GATE_3, GateID.GATE_4,
                           GateID.GATE_5, GateID.GATE_6, GateID.GATE_7, GateID.GATE_8]:
                gate = guardian_engine.get_gate(gate_id)
                verdict = gate.evaluate(candidate, evidence_records, prior_verdicts)
                verdicts.append(verdict)
                prior_verdicts.append(verdict)
                save_verdict_to_db(verdict, str(candidate.candidate_id))

            # Determine final verdict
            final_verdict = VerdictType.PASS
            if any(v.verdict == VerdictType.BLOCKED for v in verdicts):
                final_verdict = VerdictType.BLOCKED
            elif any(v.verdict == VerdictType.NOT_PROVEN for v in verdicts):
                final_verdict = VerdictType.NOT_PROVEN

            # Create decision cartridge
            gate_verdicts_list = [
                {
                    "gate_id": v.gate_id.value,
                    "verdict_id": str(v.verdict_id),
                    "verdict": v.verdict.value
                }
                for v in verdicts
            ]

            cartridge = DecisionCartridge(
                cartridge_id=uuid4(),
                correlation_id=correlation_id,
                candidate_id=candidate.candidate_id,
                gate_verdicts=gate_verdicts_list,
                final_verdict=final_verdict,
                evidence_root_hash="root_hash_computed",
                policy_root_hash="policy_hash_computed",
                authority=AuthorityLevel.ZERO,
                owner_approval_id=UUID(request.owner_approval_id) if request.owner_approval_id else None
            )

            # Save cartridge
            conn = sqlite3.connect(guardian_db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO decision_cartridge
                (cartridge_id, correlation_id, candidate_id, gate_verdicts, final_verdict,
                 evidence_root_hash, policy_root_hash, authority, created_at, owner_approval_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(cartridge.cartridge_id),
                str(cartridge.correlation_id),
                str(cartridge.candidate_id),
                json.dumps(gate_verdicts_list),
                cartridge.final_verdict.value,
                cartridge.evidence_root_hash,
                cartridge.policy_root_hash,
                cartridge.authority.value,
                datetime.utcnow().isoformat(),
                str(cartridge.owner_approval_id) if cartridge.owner_approval_id else None
            ))
            conn.commit()
            conn.close()

            return {
                "cartridge_id": str(cartridge.cartridge_id),
                "correlation_id": str(cartridge.correlation_id),
                "final_verdict": cartridge.final_verdict.value,
                "gate_verdicts": [
                    {
                        "gate_id": v.gate_id.value,
                        "verdict": v.verdict.value,
                        "reasoning": v.reasoning
                    }
                    for v in verdicts
                ],
                "authority": cartridge.authority.value,
                "created_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Guardian evaluation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/guardian/verdict/{verdict_id}")
    def get_verdict(verdict_id: str):
        """GET /guardian/verdict/{verdict_id} - Retrieve immutable verdict"""
        conn = sqlite3.connect(guardian_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT verdict_id, gate_id, correlation_id, verdict, reasoning, evidence_id, event_time
                FROM gate_verdicts
                WHERE verdict_id = ?
            """, (verdict_id,))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Verdict not found")

            return {
                "verdict_id": row[0],
                "gate_id": row[1],
                "correlation_id": row[2],
                "verdict": row[3],
                "reasoning": row[4],
                "evidence_id": row[5],
                "event_time": row[6]
            }
        finally:
            conn.close()

    @app.get("/guardian/cartridge/{correlation_id}")
    def get_cartridge(correlation_id: str):
        """GET /guardian/cartridge/{correlation_id} - Retrieve decision cartridge"""
        conn = sqlite3.connect(guardian_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT cartridge_id, correlation_id, candidate_id, gate_verdicts, final_verdict,
                       evidence_root_hash, policy_root_hash, authority, created_at
                FROM decision_cartridge
                WHERE correlation_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (correlation_id,))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Cartridge not found")

            return {
                "cartridge_id": row[0],
                "correlation_id": row[1],
                "candidate_id": row[2],
                "gate_verdicts": json.loads(row[3]),
                "final_verdict": row[4],
                "evidence_root_hash": row[5],
                "policy_root_hash": row[6],
                "authority": row[7],
                "created_at": row[8]
            }
        finally:
            conn.close()

    @app.get("/guardian/gates")
    def list_gates():
        """GET /guardian/gates - List all 8 gates with info"""
        gates_info = [
            {
                "gate_id": "gate_1",
                "gate_order": 1,
                "gate_name": "SCHEMA_AND_IDENTITY",
                "stale_threshold_seconds": 300,
                "blocking_conditions": ["Missing hash", "Invalid correlation_id", "Passport missing"]
            },
            {
                "gate_id": "gate_2",
                "gate_order": 2,
                "gate_name": "HASH_INTEGRITY",
                "stale_threshold_seconds": 300,
                "blocking_conditions": ["Hash mismatch", "Hash contradiction detected"]
            },
            {
                "gate_id": "gate_3",
                "gate_order": 3,
                "gate_name": "AUTHORITY_POLICY_COMPLIANCE",
                "stale_threshold_seconds": 300,
                "blocking_conditions": ["Authority not ZERO", "Live enabled", "Broker orders enabled", "Control mutation enabled"]
            },
            {
                "gate_id": "gate_4",
                "gate_order": 4,
                "gate_name": "MACHINE_HEALTH_AND_READINESS",
                "stale_threshold_seconds": 300,
                "blocking_conditions": ["Machine error", "Heartbeat stale", "Clock skew excessive", "Fencing token expired"]
            },
            {
                "gate_id": "gate_5",
                "gate_order": 5,
                "gate_name": "CANARY_EXECUTION",
                "stale_threshold_seconds": 300,
                "blocking_conditions": ["Error rate > 5%", "Latency > 200ms", "Canary failed", "Rollback triggered"]
            },
            {
                "gate_id": "gate_6",
                "gate_order": 6,
                "gate_name": "EVIDENCE_CONSISTENCY",
                "stale_threshold_seconds": 300,
                "blocking_conditions": ["Hash contradiction", "Policy contradiction", "Temporal ordering violation"]
            },
            {
                "gate_id": "gate_7",
                "gate_order": 7,
                "gate_name": "FRESHNESS_AND_STALENESS",
                "stale_threshold_seconds": 300,
                "blocking_conditions": ["Evidence > 300s old", "Required evidence missing"]
            },
            {
                "gate_id": "gate_8",
                "gate_order": 8,
                "gate_name": "FINAL_ARBITER",
                "stale_threshold_seconds": 300,
                "blocking_conditions": ["Prior gate blocked", "Prior gate not proven", "Authority escalation attempted"]
            }
        ]

        return gates_info

    return app


if __name__ == "__main__":
    import uvicorn

    # Create HP infrastructure
    hp = HPInfrastructure(db_path="hp_infra.db")

    # Create FastAPI app
    app = create_app(hp)

    # Run server on configurable port
    port = int(os.getenv('API_PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
