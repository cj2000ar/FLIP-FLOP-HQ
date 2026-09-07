"""
Private Read API - Lab & Dashboard
FlipFlop HQ Phase 2 Implementation
Authority: ZERO (read-only)
Date: 2026-09-07

Endpoints (8 total):
1. /experiments - Experiment ledger (A-G PRE_REGISTERED)
2. /queue - Queue items by state
3. /vault/items - Strategy vault items with family filter
4. /vault/families - Strategy family definitions
5. /guardian/wounds - Wound registry
6. /guardian/overrides - Override ledger
7. /guardian/calibration - Calibration ledger
8. /agenda/events - Event slots / calendar

Auth: Machine-ID + Fencing-Token headers
Bitemporal: event_time ≤ knowledge_time enforced
Port: 8000 (same as guardian_api)
"""

from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from enum import Enum
import logging
import os
import time
from uuid import uuid4
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Centralized logging (structured JSON, file rotation)
try:
    from logging_config import setup_logging, api_logger, audit_logger
    setup_logging(log_dir=os.getenv("LOG_DIR", "logs"), log_level=os.getenv("LOG_LEVEL", "INFO"))
except ImportError:
    logging.basicConfig(level=logging.INFO)
    api_logger = logging.getLogger("flipflop.api")
    audit_logger = logging.getLogger("flipflop.audit")
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class QueueState(str, Enum):
    """Queue state machine"""
    CAPTURED = "CAPTURED"
    NEEDS_EXTRACTION = "NEEDS_EXTRACTION"
    DUPLICATE_DNA = "DUPLICATE_DNA"
    READY_FOR_SPEC = "READY_FOR_SPEC"
    BLOCKED_DATA = "BLOCKED_DATA"
    READY_FOR_SHADOW_BUILD = "READY_FOR_SHADOW_BUILD"
    SHADOW_RUNNING = "SHADOW_RUNNING"
    REJECTED = "REJECTED"
    SURVIVOR = "SURVIVOR"
    PROMOTION_REVIEW = "PROMOTION_REVIEW"


class ExperimentStatus(str, Enum):
    """Experiment lifecycle status"""
    PRE_REGISTERED = "PRE_REGISTERED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HOLDOUT_CONSUMED = "HOLDOUT_CONSUMED"


class WoundStatus(str, Enum):
    """Wound registry status"""
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    CLOSED = "CLOSED"
    REFERENCE = "REFERENCE"


class EventImportance(str, Enum):
    """Event importance level"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class BitemporalBase(BaseModel):
    """Base model with bitemporal fields"""
    event_time: int = Field(..., description="Unix seconds: when thing happened")
    knowledge_time: str = Field(..., description="ISO 8601: when HQ learned it")


class ExperimentModel(BitemporalBase):
    """Experiment ledger entry"""
    id: str = Field(..., description="Experiment ID (A-G)")
    name: str = Field(..., description="Human-readable name")
    hypothesis: str = Field(..., description="Research question")
    parameters: Dict[str, Any] = Field(..., description="Experiment parameters")
    dataset_role: str = Field(..., description="TRAIN/HOLDOUT/RESERVE")
    runs: int = Field(..., description="Number of runs completed")
    status: ExperimentStatus = Field(..., description="Current status")
    result: Optional[str] = Field(None, description="Outcome/metric summary")
    rejection_reason: Optional[str] = Field(None, description="Why rejected (if applicable)")
    next_gate: Optional[str] = Field(None, description="Next promotion gate")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    completed_at: Optional[str] = Field(None, description="ISO 8601 completion timestamp")


class QueueItemModel(BitemporalBase):
    """Queue item"""
    id: str = Field(..., description="Queue item ID")
    title: str = Field(..., description="Brief description")
    state: QueueState = Field(..., description="Current state")
    why: str = Field(..., description="Reason for state")


class VaultItemModel(BitemporalBase):
    """Vault item (strategy, paper, video, etc.)"""
    id: str = Field(..., description="Item ID")
    kind: str = Field(..., description="TYPE: video, link, paper, script, note")
    title: str = Field(..., description="Item title")
    source: str = Field(..., description="URL or reference")
    extraction: Optional[str] = Field(None, description="Extracted idea/rules")
    evidence: Optional[str] = Field(None, description="Evidence grade/notes")
    family: str = Field(..., description="Strategy family tag")
    dna: Optional[str] = Field(None, description="DNA commonality")
    data_needs: Optional[str] = Field(None, description="Missing data/requirements")


class StrategyFamilyModel(BaseModel):
    """Strategy family definition"""
    id: str = Field(..., description="Family ID")
    name: str = Field(..., description="Family name")
    lineage: str = Field(..., description="Development lineage")
    dna: str = Field(..., description="Shared DNA/rules")


class WoundModel(BitemporalBase):
    """Wound registry entry"""
    id: str = Field(..., description="Wound ID")
    title: str = Field(..., description="Brief title")
    detail: str = Field(..., description="Full incident description")
    status: WoundStatus = Field(..., description="Investigation status")
    tone: str = Field(..., description="Tone: alert, learning, reference")


class OverrideLedgerModel(BitemporalBase):
    """Override ledger entry"""
    id: str = Field(..., description="Override ID")
    who: str = Field(..., description="Who authorized")
    reason: str = Field(..., description="Why override was needed")
    before_state: Dict[str, Any] = Field(..., description="State before override")
    after_state: Dict[str, Any] = Field(..., description="State after override")
    outcome: str = Field(..., description="Result of override")
    timestamp: str = Field(..., description="ISO 8601 when applied")


class CalibrationEntryModel(BitemporalBase):
    """Calibration ledger entry"""
    id: str = Field(..., description="Calibration ID")
    prediction: str = Field(..., description="What system predicted")
    actual: str = Field(..., description="What actually happened")
    score: float = Field(..., description="Correctness score (0-1)")
    notes: Optional[str] = Field(None, description="Analysis notes")


class EventSlotModel(BitemporalBase):
    """Event agenda slot"""
    code: str = Field(..., description="Event code (e.g., FOMC_DEC)")
    name: str = Field(..., description="Event name")
    importance: EventImportance = Field(..., description="Event importance")
    status: str = Field(..., description="Status: NOT_CONNECTED, SCHEDULED, OCCURRED")
    tone: str = Field(..., description="Tone: alert, learning, routine")
    datetime: Optional[str] = Field(None, description="ISO 8601 event time")
    actual: Optional[str] = Field(None, description="Actual value (after release)")
    forecast: Optional[str] = Field(None, description="Market forecast")
    previous: Optional[str] = Field(None, description="Previous value")
    nq_response: Optional[str] = Field(None, description="NQ market response")
    signals_emitted: Optional[List[str]] = Field(None, description="Strategy signals triggered")
    control_result: Optional[str] = Field(None, description="CONTROL strategy result")


# ============================================================================
# HARD-CODED DATA
# ============================================================================

def get_now():
    """Current time for bitemporal fields"""
    now = datetime.utcnow()
    return int(now.timestamp()), now.isoformat() + "Z"


# Experiments A-G from strategy_intelligence_master
EXPERIMENTS_DATA = [
    {
        "id": "A",
        "name": "FVG vs Pullback",
        "hypothesis": "Does FVG gap add info beyond price correction?",
        "parameters": {
            "family": "IFVG",
            "baseline": "price_structure_only",
            "treatment": "fvg_marker_added"
        },
        "dataset_role": "TRAIN",
        "runs": 1,
        "status": ExperimentStatus.PRE_REGISTERED,
        "result": None,
        "rejection_reason": None,
        "next_gate": "READY_FOR_SPEC",
        "created_at": "2026-09-01T10:00:00Z",
        "completed_at": None,
    },
    {
        "id": "B",
        "name": "Sweep Ablation",
        "hypothesis": "Each layer justified out-of-sample?",
        "parameters": {
            "family": "ICT",
            "layers": ["sweep", "displacement", "fvg", "entry_depth"],
            "methodology": "ablation_chain"
        },
        "dataset_role": "TRAIN",
        "runs": 0,
        "status": ExperimentStatus.PRE_REGISTERED,
        "result": None,
        "rejection_reason": None,
        "next_gate": "READY_FOR_SPEC",
        "created_at": "2026-09-01T10:00:00Z",
        "completed_at": None,
    },
    {
        "id": "C",
        "name": "Exit at +1R",
        "hypothesis": "Trailing activation improves net or truncates?",
        "parameters": {
            "family": "UT_NUMKI",
            "exit_trigger": "plus_1R",
            "metric": "net_profit_vs_truncation"
        },
        "dataset_role": "TRAIN",
        "runs": 0,
        "status": ExperimentStatus.PRE_REGISTERED,
        "result": None,
        "rejection_reason": None,
        "next_gate": "READY_FOR_SPEC",
        "created_at": "2026-09-01T10:00:00Z",
        "completed_at": None,
    },
    {
        "id": "D",
        "name": "Pressure w/o Progress",
        "hypothesis": "Does order aggression add beyond price?",
        "parameters": {
            "family": "ORDER_FLOW",
            "signal": "aggressive_buy_sell_no_progress",
            "control": "price_only"
        },
        "dataset_role": "TRAIN",
        "runs": 0,
        "status": ExperimentStatus.PRE_REGISTERED,
        "result": None,
        "rejection_reason": None,
        "next_gate": "READY_FOR_SPEC",
        "created_at": "2026-09-01T10:00:00Z",
        "completed_at": None,
    },
    {
        "id": "E",
        "name": "Volume Profile",
        "hypothesis": "Rejection/acceptance causality + completed candles?",
        "parameters": {
            "family": "VOLUME_PROFILE",
            "rejection": "cross_frontier_close_back_inside",
            "acceptance": "two_candles_close_beyond"
        },
        "dataset_role": "TRAIN",
        "runs": 0,
        "status": ExperimentStatus.PRE_REGISTERED,
        "result": None,
        "rejection_reason": None,
        "next_gate": "READY_FOR_SPEC",
        "created_at": "2026-09-01T10:00:00Z",
        "completed_at": None,
    },
    {
        "id": "F",
        "name": "ORB",
        "hypothesis": "Simple vs ORB+delta, flatten, costs, Monte Carlo?",
        "parameters": {
            "family": "SESSION_STRUCTURE",
            "baseline": "simple_breakout",
            "treatment": "orb_plus_delta_flatten"
        },
        "dataset_role": "TRAIN",
        "runs": 0,
        "status": ExperimentStatus.PRE_REGISTERED,
        "result": None,
        "rejection_reason": None,
        "next_gate": "READY_FOR_SPEC",
        "created_at": "2026-09-01T10:00:00Z",
        "completed_at": None,
    },
    {
        "id": "G",
        "name": "Replay-to-Paper Gap",
        "hypothesis": "1x vs accelerated produce identical Cartridges?",
        "parameters": {
            "family": "RR500",
            "replay_speed_1x": True,
            "replay_speed_accelerated": True
        },
        "dataset_role": "TRAIN",
        "runs": 0,
        "status": ExperimentStatus.PRE_REGISTERED,
        "result": None,
        "rejection_reason": None,
        "next_gate": "READY_FOR_SPEC",
        "created_at": "2026-09-01T10:00:00Z",
        "completed_at": None,
    },
    {
        "id": "R_holdout",
        "name": "RR500 Holdout Test",
        "hypothesis": "Validate V03 out-of-sample",
        "parameters": {
            "family": "RR500",
            "version": "V03",
            "dataset": "holdout_10_sessions"
        },
        "dataset_role": "HOLDOUT",
        "runs": 1,
        "status": ExperimentStatus.FAILED,
        "result": "Holdout consumed/blocked irreversibly",
        "rejection_reason": "Out-of-sample performance failed",
        "next_gate": None,
        "created_at": "2026-08-15T14:00:00Z",
        "completed_at": "2026-08-25T16:30:00Z",
    },
]


# Queue items
QUEUE_ITEMS_DATA = [
    {
        "id": "Q-CAPTURED-001",
        "title": "MNQ Scalping (JgLZZXtsk9Y)",
        "state": QueueState.CAPTURED,
        "why": "Video extracted from YouTube",
    },
    {
        "id": "Q-NEEDS_EXTRACTION-001",
        "title": "$4k/day IFVG (LIWWf0oqDNo)",
        "state": QueueState.NEEDS_EXTRACTION,
        "why": "Video pending extraction work",
    },
    {
        "id": "Q-NEEDS_EXTRACTION-002",
        "title": "Order Flow Pietro Valastro (Kq2IGPWhZlY)",
        "state": QueueState.NEEDS_EXTRACTION,
        "why": "Complex signal extraction in progress",
    },
    {
        "id": "Q-DUPLICATE_DNA-001",
        "title": "Volume Profile / NinjaTrader",
        "state": QueueState.DUPLICATE_DNA,
        "why": "DNA overlap with IFVG family",
    },
    {
        "id": "Q-READY_FOR_SPEC-001",
        "title": "ICT Silver Bullet (KML09tRtHM8)",
        "state": QueueState.READY_FOR_SPEC,
        "why": "Ablation chain ready for specification",
    },
    {
        "id": "Q-BLOCKED_DATA-001",
        "title": "Reddit Playback bot",
        "state": QueueState.BLOCKED_DATA,
        "why": "Awaiting NinjaTrader replay data feed",
    },
    {
        "id": "Q-READY_FOR_SHADOW_BUILD-001",
        "title": "Four Strategies / 671% (yW6c0K8uGvw)",
        "state": QueueState.READY_FOR_SHADOW_BUILD,
        "why": "Spec complete, build commencing",
    },
    {
        "id": "Q-SHADOW_RUNNING-001",
        "title": "Sweep Ablation SHADOW",
        "state": QueueState.SHADOW_RUNNING,
        "why": "Running ablation chain in simulation",
    },
    {
        "id": "Q-SURVIVOR-001",
        "title": "s_time_to_max_drawup_ms + s_alternation_ratio",
        "state": QueueState.SURVIVOR,
        "why": "Research survivor from RR500 (AUC 0.764)",
    },
]


# Vault items (5 families, 12 items)
VAULT_ITEMS_DATA = [
    # RR500 family
    {
        "id": "V-RR500-001",
        "kind": "script",
        "title": "RR500 V3.3.1 Quant Mirror",
        "source": "internal",
        "extraction": "NY/Asia modules, NQ/MNQ profiles, liability ladder, combined loss cap",
        "evidence": "Replay stable (4/12 trades), sensitivity untested (8/12)",
        "family": "RR500",
        "dna": "Quant Mirror lineage",
        "data_needs": "Complete replay dataset",
    },
    {
        "id": "V-RR500-002",
        "kind": "paper",
        "title": "RR500 Validation Study",
        "source": "internal",
        "extraction": "12-trade canonical, 83.3% win rate, +$2,080 gross",
        "evidence": "Historical baseline established",
        "family": "RR500",
        "dna": "Profit factor 7.5",
        "data_needs": "Live feed validation",
    },
    # IFVG family
    {
        "id": "V-IFVG-001",
        "kind": "video",
        "title": "$4k/day IFVG (LIWWf0oqDNo)",
        "source": "https://youtube.com/watch?v=LIWWf0oqDNo",
        "extraction": "EMA 50 bias (15/30/60min), pullback to FVG, intratrend reversal",
        "evidence": "HTF confirmed data",
        "family": "IFVG",
        "dna": "Fair Value Gap memory, bullish/bearish inversion",
        "data_needs": "HTF EMA confirmed historical bars",
    },
    {
        "id": "V-IFVG-002",
        "kind": "script",
        "title": "IFVG Pure Every Box V1.3",
        "source": "internal",
        "extraction": "3-candle FVG, 0.6 ATR stop, 1R target",
        "evidence": "Mobile UI tested",
        "family": "IFVG",
        "dna": "Entry at IFVG line, max age, hidden memory",
        "data_needs": None,
    },
    # UT/NUMKI family
    {
        "id": "V-UT-001",
        "kind": "video",
        "title": "MNQ Scalping (JgLZZXtsk9Y)",
        "source": "https://youtube.com/watch?v=JgLZZXtsk9Y",
        "extraction": "Trailing stop activation at +1R vs unchanged exit",
        "evidence": "Entry/target/stop preserved",
        "family": "UT_NUMKI",
        "dna": "ATR trailing stop, sensitivity/key value",
        "data_needs": "Preserved entry/stop/size time series",
    },
    {
        "id": "V-UT-002",
        "kind": "note",
        "title": "UT Reversals & Session Filters",
        "source": "internal",
        "extraction": "HTF EMA bias, ADX, Chop Guardian, peak lock",
        "evidence": "Heikin Ashi optional",
        "family": "UT_NUMKI",
        "dna": "Smart runner, scale-out, risk cap",
        "data_needs": None,
    },
    # ORDER_FLOW family
    {
        "id": "V-ORDER-001",
        "kind": "video",
        "title": "Order Flow / Pietro Valastro (Kq2IGPWhZlY)",
        "source": "https://youtube.com/watch?v=Kq2IGPWhZlY",
        "extraction": "Pressure + response adaptation",
        "evidence": "Bid/ask interaction analysis needed",
        "family": "ORDER_FLOW",
        "dna": "Heavy buy/sell without progress",
        "data_needs": "Aggression + failure cost time series",
    },
    {
        "id": "V-ORDER-002",
        "kind": "paper",
        "title": "Liquidity Persistence Framework",
        "source": "internal",
        "extraction": "Price-only vs aggression+failure comparison",
        "evidence": "Research stage",
        "family": "ORDER_FLOW",
        "dna": "Market microstructure",
        "data_needs": "Full orderbook depth replay",
    },
    # ICT/SWEEP family
    {
        "id": "V-ICT-001",
        "kind": "video",
        "title": "ICT Silver Bullet (KML09tRtHM8)",
        "source": "https://youtube.com/watch?v=KML09tRtHM8",
        "extraction": "Sweep alone, sweep+displacement, sweep+displacement+FVG",
        "evidence": "Ablation chain underway",
        "family": "ICT",
        "dna": "Entry-depth variants, time windows, HTF bias",
        "data_needs": "Clean sweep detection dataset",
    },
    # SESSION_STRUCTURE family
    {
        "id": "V-SESSION-001",
        "kind": "video",
        "title": "Four Strategies / 671% (yW6c0K8uGvw)",
        "source": "https://youtube.com/watch?v=yW6c0K8uGvw",
        "extraction": "ORB + VWAP context + volume-delta optional",
        "evidence": "Fixed stop/target + session flatten",
        "family": "SESSION_STRUCTURE",
        "dna": "Opening Range Breakout",
        "data_needs": "VWAP + volume-delta historical data",
    },
    {
        "id": "V-SESSION-002",
        "kind": "note",
        "title": "Market Structure Book",
        "source": "internal",
        "extraction": "ORB15, Initial Balance, IB75, Failed Auction, GAP_TINY, VWAP Pullback, SMT, London→NY, Opening Drive",
        "evidence": "Comprehensive session taxonomy",
        "family": "SESSION_STRUCTURE",
        "dna": "Session filtering framework",
        "data_needs": None,
    },
]


# Strategy families
STRATEGY_FAMILIES_DATA = [
    {
        "id": "F-RR500",
        "name": "RR500 / FlipFlop Quant Mirror",
        "lineage": "V2.0 Static Audit → V3.3.1–V3.3.4 Quant Mirror → Custom Lab → NY/Asia modules → NQ/MNQ profiles",
        "dna": "Liability ladder, loss cap, profit floor, survivor trail, combined logic",
    },
    {
        "id": "F-IFVG",
        "name": "IFVG / FVG (Fair Value Gap)",
        "lineage": "Sniper_V1.0 → V1.1 Mobile → V1.2 Backtest → V1.3 Pure Every Box → V1.3.1 Daily UI → V1.3.2 Mobile UI → EXECUTION-CLEAN",
        "dna": "3-candle FVG memory, bullish/bearish inversion, entry at IFVG line, market vs limit, 0.6 ATR stop",
    },
    {
        "id": "F-UT",
        "name": "UT / NUMKI",
        "lineage": "Core ATR trail → Sensitivity/key value → Heikin Ashi optional → HTF EMA bias → ADX → Chop Guardian",
        "dna": "Trailing stop, reversals, session filters, profit lock, peak lock, smart runner, scale-out",
    },
    {
        "id": "F-ORDER_FLOW",
        "name": "Order Flow / Market Microstructure",
        "lineage": "Pietro Valastro framework → Pressure + response → Aggression without progress → Bid/ask interaction",
        "dna": "Heavy buy/sell signal, liquidity persistence, price vs aggression contrast",
    },
    {
        "id": "F-ICT",
        "name": "ICT / Smart Money Concepts",
        "lineage": "Sweep → Displacement → FVG → Entry depth variants → Time windows → HTF bias confirmation",
        "dna": "Multi-layer ablation, SMT context, retest identification, liquidity memory",
    },
]


# Wounds registry
WOUNDS_DATA = [
    {
        "id": "W-001",
        "title": "Holdout Dataset Contamination Risk",
        "detail": "RR500 V03 holdout test failed. Irreversible consumption means no second holdout available for this lineage. Risk: future holdouts on same instrument may leak knowledge.",
        "status": WoundStatus.REFERENCE,
        "tone": "learning",
    },
    {
        "id": "W-002",
        "title": "Path-Dependent Signal Leakage",
        "detail": "V03 native extraction from NinjaTrader replay required. Cannot use post-decision PATH for prediction. Pre-signal state must be frozen at market time.",
        "status": WoundStatus.OPEN,
        "tone": "alert",
    },
]


# Calibration ledger
CALIBRATION_DATA = [
    {
        "id": "C-001",
        "prediction": "System ready for SHADOW deployment",
        "actual": "SHADOW_RUNNING state achieved, no blocking errors",
        "score": 0.95,
        "notes": "Minor latency tax not forecasted",
    },
    {
        "id": "C-002",
        "prediction": "Extraction feasible on video dataset",
        "actual": "50% of 7 videos extracted, 3 pending complex signal work",
        "score": 0.72,
        "notes": "Underestimated order flow complexity",
    },
]


# Agenda events
EVENTS_DATA = [
    {
        "code": "FOMC_DEC",
        "name": "FOMC Decision",
        "importance": EventImportance.CRITICAL,
        "status": "NOT_CONNECTED",
        "tone": "alert",
        "datetime": None,
        "actual": None,
        "forecast": None,
        "previous": None,
        "nq_response": None,
        "signals_emitted": None,
        "control_result": None,
    },
    {
        "code": "NFP_JAN",
        "name": "Non-Farm Payroll",
        "importance": EventImportance.CRITICAL,
        "status": "NOT_CONNECTED",
        "tone": "alert",
        "datetime": None,
        "actual": None,
        "forecast": None,
        "previous": None,
        "nq_response": None,
        "signals_emitted": None,
        "control_result": None,
    },
    {
        "code": "CPI_DEC",
        "name": "Consumer Price Index",
        "importance": EventImportance.HIGH,
        "status": "NOT_CONNECTED",
        "tone": "routine",
        "datetime": None,
        "actual": None,
        "forecast": None,
        "previous": None,
        "nq_response": None,
        "signals_emitted": None,
        "control_result": None,
    },
]


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Private Read API",
    description="Lab & Dashboard read-only endpoints (bitemporal, Authority=ZERO)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:51095"],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================================
# AUDIT LOGGING MIDDLEWARE
# ============================================================================

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        machine_id = request.headers.get("Machine-ID", "unknown")
        endpoint = request.url.path
        request_time = datetime.utcnow().isoformat()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            response = Response(content=str(e), status_code=status_code)

        audit_log = {
            "timestamp": request_time,
            "machine_id": machine_id,
            "endpoint": endpoint,
            "method": request.method,
            "status_code": status_code,
            "request_id": str(uuid4())[:8],
        }

        logger.info(json.dumps(audit_log))
        return response


app.add_middleware(AuditLoggingMiddleware)


# ============================================================================
# MIDDLEWARE & AUTH
# ============================================================================

_TOKEN_STORE = {}  # Dict[str, {"expires_at": float, "machine_id": str}]
_TOKEN_TTL_SECONDS = 86400  # 24 hours


def _validate_token_locally(token: str, machine_id: str) -> bool:
    """
    Validate token against local store (dev/test mode).

    Production: Use HP /validate_fencing_token instead.
    Token format: UUID or test token (alphanumeric, 8+ chars).
    TTL: 24 hours from issue time.
    """
    if token not in _TOKEN_STORE:
        return False

    stored = _TOKEN_STORE[token]
    if stored["machine_id"] != machine_id:
        return False

    if time.time() > stored["expires_at"]:
        del _TOKEN_STORE[token]
        return False

    return True


async def validate_auth(
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    Validate Machine-ID and Fencing-Token headers.

    Dev/Test: Uses local token store with 24-hour TTL.
    Production: Should call HP /validate_fencing_token (not yet available).
    """
    if not machine_id:
        raise HTTPException(status_code=401, detail="Missing Machine-ID header")
    if not fencing_token:
        raise HTTPException(status_code=401, detail="Missing Fencing-Token header")

    # Format validation: UUID or alphanumeric 8+ chars
    if not (len(fencing_token) >= 8 and fencing_token.replace("-", "").isalnum()):
        raise HTTPException(status_code=401, detail="Invalid Fencing-Token format")

    # Token validation with TTL check
    if not _validate_token_locally(fencing_token, machine_id):
        raise HTTPException(status_code=403, detail="Fencing-Token expired or invalid")

    logger.info(f"Auth successful for machine_id={machine_id}, token valid")
    return machine_id


def issue_test_token(machine_id: str) -> str:
    """Issue test token for dev/test (24-hour TTL). NOT for production."""
    import uuid
    token = str(uuid.uuid4())
    _TOKEN_STORE[token] = {
        "machine_id": machine_id,
        "expires_at": time.time() + _TOKEN_TTL_SECONDS,
    }
    logger.info(f"Issued test token for machine_id={machine_id}, expires in {_TOKEN_TTL_SECONDS}s")
    return token


def add_bitemporal_fields(data: Dict, event_time_seconds: int = None):
    """
    Add bitemporal fields to response data.

    Args:
        data: Response dict
        event_time_seconds: Unix seconds (event happened). Defaults to creation time.

    Returns:
        data with event_time and knowledge_time added
    """
    if event_time_seconds is None:
        event_time_seconds = int(datetime.utcnow().timestamp())

    knowledge_time_seconds, knowledge_time_iso = get_now()

    # Verify: event_time ≤ knowledge_time
    if event_time_seconds > knowledge_time_seconds:
        logger.warning(
            f"Bitemporal violation: event_time ({event_time_seconds}) > "
            f"knowledge_time ({knowledge_time_seconds}). Using knowledge_time."
        )
        event_time_seconds = knowledge_time_seconds

    data["event_time"] = event_time_seconds
    data["knowledge_time"] = knowledge_time_iso

    return data


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Private Read API",
        "version": "1.0.0",
        "authority": "ZERO",
        "read_only": True
    }


@app.post("/dev/issue-token")
async def dev_issue_token(machine_id: str = Query(None, description="Machine ID to issue token for")):
    """
    DEV ONLY: Issue test token with 24-hour TTL.

    Usage: POST /dev/issue-token?machine_id=test-machine
    Returns: {"token": "...", "expires_in_seconds": 86400}

    Production: Remove this endpoint and integrate with HP /validate_fencing_token.
    """
    if not machine_id:
        raise HTTPException(status_code=400, detail="machine_id required")

    token = issue_test_token(machine_id)
    return {
        "token": token,
        "machine_id": machine_id,
        "expires_in_seconds": _TOKEN_TTL_SECONDS,
        "note": "Dev/test token only - 24 hour TTL"
    }


@app.get("/experiments", response_model=List[ExperimentModel])
async def get_experiments(
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    GET /experiments - Experiment ledger (A-G PRE_REGISTERED, R holdout, reserve closed)

    Returns hard-coded experiments from strategy_intelligence_master.
    """
    await validate_auth(machine_id, fencing_token)

    results = []
    now_seconds, now_iso = get_now()

    for exp in EXPERIMENTS_DATA:
        exp_copy = exp.copy()

        # Parse created_at to get event_time
        created_dt = datetime.fromisoformat(exp_copy["created_at"].replace("Z", "+00:00"))
        event_time = int(created_dt.timestamp())

        exp_copy = add_bitemporal_fields(exp_copy, event_time)
        results.append(ExperimentModel(**exp_copy))

    return results


@app.get("/queue", response_model=List[QueueItemModel])
async def get_queue(
    state: Optional[QueueState] = Query(None, description="Filter by state"),
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    GET /queue?state={state} - Queue items by QueueState

    States: CAPTURED, NEEDS_EXTRACTION, DUPLICATE_DNA, READY_FOR_SPEC,
            BLOCKED_DATA, READY_FOR_SHADOW_BUILD, SHADOW_RUNNING, REJECTED,
            SURVIVOR, PROMOTION_REVIEW
    """
    await validate_auth(machine_id, fencing_token)

    now_seconds, now_iso = get_now()

    items = QUEUE_ITEMS_DATA
    if state:
        items = [item for item in items if item["state"] == state]

    results = []
    for item in items:
        item_copy = item.copy()
        item_copy = add_bitemporal_fields(item_copy, now_seconds)
        results.append(QueueItemModel(**item_copy))

    return results


@app.get("/vault/items", response_model=List[VaultItemModel])
async def get_vault_items(
    family: Optional[str] = Query(None, description="Filter by strategy family"),
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    GET /vault/items?family={fam} - Vault items with optional family filter

    Families: RR500, IFVG, UT_NUMKI, ORDER_FLOW, ICT, SESSION_STRUCTURE
    """
    await validate_auth(machine_id, fencing_token)

    now_seconds, now_iso = get_now()

    items = VAULT_ITEMS_DATA
    if family:
        items = [item for item in items if item["family"] == family]

    results = []
    for item in items:
        item_copy = item.copy()
        item_copy = add_bitemporal_fields(item_copy, now_seconds)
        results.append(VaultItemModel(**item_copy))

    return results


@app.get("/vault/families", response_model=List[StrategyFamilyModel])
async def get_vault_families(
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    GET /vault/families - Strategy family definitions (5 families)
    """
    await validate_auth(machine_id, fencing_token)

    return [StrategyFamilyModel(**family) for family in STRATEGY_FAMILIES_DATA]


@app.get("/guardian/wounds", response_model=List[WoundModel])
async def get_guardian_wounds(
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    GET /guardian/wounds - Wound registry (permanent incident reference)
    """
    await validate_auth(machine_id, fencing_token)

    now_seconds, now_iso = get_now()

    results = []
    for wound in WOUNDS_DATA:
        wound_copy = wound.copy()
        wound_copy = add_bitemporal_fields(wound_copy, now_seconds)
        results.append(WoundModel(**wound_copy))

    return results


@app.get("/guardian/overrides", response_model=List[OverrideLedgerModel])
async def get_guardian_overrides(
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    GET /guardian/overrides - Override ledger (empty until manual intervention)

    Schema: id, who, reason, before_state, after_state, outcome, timestamp
    """
    await validate_auth(machine_id, fencing_token)

    # Empty list for now - will populate when overrides occur
    return []


@app.get("/guardian/calibration", response_model=List[CalibrationEntryModel])
async def get_guardian_calibration(
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    GET /guardian/calibration - Calibration ledger (predictions scored)

    Measures false-green readiness: "seemed ready" has consequence
    """
    await validate_auth(machine_id, fencing_token)

    now_seconds, now_iso = get_now()

    results = []
    for cal in CALIBRATION_DATA:
        cal_copy = cal.copy()
        cal_copy = add_bitemporal_fields(cal_copy, now_seconds)
        results.append(CalibrationEntryModel(**cal_copy))

    return results


@app.get("/agenda/events", response_model=List[EventSlotModel])
async def get_agenda_events(
    machine_id: str = Header(None, alias="Machine-ID"),
    fencing_token: str = Header(None, alias="Fencing-Token"),
):
    """
    GET /agenda/events - Event slots / calendar

    Status: NOT_CONNECTED (until feed live), SCHEDULED, OCCURRED
    Tone: alert, learning, routine
    """
    await validate_auth(machine_id, fencing_token)

    now_seconds, now_iso = get_now()

    results = []
    for event in EVENTS_DATA:
        event_copy = event.copy()
        event_copy = add_bitemporal_fields(event_copy, now_seconds)
        results.append(EventSlotModel(**event_copy))

    return results


@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    """Handle CORS preflight requests"""
    return {"status": "ok"}


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
