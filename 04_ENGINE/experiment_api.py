"""
Experiment Submission API - FastAPI Endpoints
FlipFlop HQ 24/7 User Script Execution
Authority: ZERO (all submissions logged)
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import json
from datetime import datetime
from uuid import uuid4
import asyncio
from contextlib import asynccontextmanager

from experiment_queue import ExperimentQueue, QueuePriority
from experiment_runner import ExperimentRunner, ExperimentStatus
from safety_sandbox import SafetyValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL STATE
# ============================================================================

queue = ExperimentQueue(max_size=100)
runner = None
active_ws_connections: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle"""
    global runner
    runner = ExperimentRunner(queue=queue)
    asyncio.create_task(runner.process_queue())
    logger.info("Experiment runner started")
    yield
    logger.info("Experiment runner stopping")
    runner.stop()

app = FastAPI(lifespan=lifespan, title="FlipFlop Experiment API")

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StrategySubmission(BaseModel):
    """User-submitted strategy code"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    strategy_code: str = Field(..., min_length=10)
    parameters: Optional[dict] = None
    priority: str = Field(default="normal", pattern="^(normal|high|low)$")

class ExperimentSubmissionResponse(BaseModel):
    """Response after submission"""
    experiment_id: str
    correlation_id: str
    queue_position: int
    status: str
    timestamp: str
    message: str

class ExperimentStatusResponse(BaseModel):
    """Status of running/completed experiment"""
    experiment_id: str
    status: str
    progress_percent: int
    eta_seconds: Optional[int]
    error_message: Optional[str] = None
    queue_position: Optional[int] = None

class ExperimentResultsResponse(BaseModel):
    """Complete results from backtest"""
    experiment_id: str
    status: str
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    equity_curve: List[float]
    trades: List[dict]
    metrics: dict
    error_messages: List[str]
    verification_status: str
    timestamp: str

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/experiment/submit", response_model=ExperimentSubmissionResponse)
async def submit_experiment(submission: StrategySubmission):
    """
    POST /experiment/submit - Submit user strategy for backtesting
    - Validates syntax and sandboxing rules
    - Enqueues to FIFO queue with priority
    - Returns experiment_id + correlation_id for polling
    """
    experiment_id = str(uuid4())
    correlation_id = f"exp-{datetime.now().strftime('%Y%m%d%H%M%S')}-{experiment_id[:8]}"

    # Validate strategy code
    validator = SafetyValidator()
    is_valid, errors = validator.validate_strategy(submission.strategy_code)
    if not is_valid:
        logger.warning(f"Invalid strategy: {errors}")
        raise HTTPException(status_code=400, detail=f"Syntax errors: {errors}")

    # Check sandbox rules
    sandbox_ok, sandbox_errors = validator.check_sandbox_rules(submission.strategy_code)
    if not sandbox_ok:
        logger.warning(f"Sandbox violation: {sandbox_errors}")
        raise HTTPException(status_code=403, detail=f"Sandbox violation: {sandbox_errors}")

    # Enqueue
    priority = QueuePriority[submission.priority.upper()]
    position = queue.enqueue(
        experiment_id=experiment_id,
        correlation_id=correlation_id,
        name=submission.name,
        strategy_code=submission.strategy_code,
        parameters=submission.parameters or {},
        priority=priority
    )

    if position is None:
        raise HTTPException(status_code=429, detail="Queue full (max 100 experiments)")

    logger.info(f"Experiment {experiment_id} queued at position {position}")

    return ExperimentSubmissionResponse(
        experiment_id=experiment_id,
        correlation_id=correlation_id,
        queue_position=position,
        status="queued",
        timestamp=datetime.now().isoformat(),
        message=f"Strategy queued at position {position}"
    )

@app.get("/experiment/{experiment_id}/status", response_model=ExperimentStatusResponse)
async def get_experiment_status(experiment_id: str):
    """
    GET /experiment/{id}/status - Poll progress
    - Returns: queued/running/complete/failed
    - ETA in seconds
    - Current progress %
    """
    exp = runner.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return ExperimentStatusResponse(
        experiment_id=experiment_id,
        status=exp["status"],
        progress_percent=exp.get("progress", 0),
        eta_seconds=exp.get("eta_seconds"),
        error_message=exp.get("error"),
        queue_position=queue.get_position(experiment_id)
    )

@app.get("/experiment/{experiment_id}/results", response_model=ExperimentResultsResponse)
async def get_experiment_results(experiment_id: str):
    """
    GET /experiment/{id}/results - Fetch complete backtest results
    - Trades list, equity curve, metrics
    - Links to Guardian verification (Gate 4/5)
    """
    exp = runner.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if exp["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail=f"Experiment still {exp['status']}")

    results = exp.get("results", {})
    return ExperimentResultsResponse(
        experiment_id=experiment_id,
        status=exp["status"],
        total_trades=results.get("total_trades", 0),
        win_rate=results.get("win_rate", 0.0),
        profit_factor=results.get("profit_factor", 0.0),
        max_drawdown=results.get("max_drawdown", 0.0),
        equity_curve=results.get("equity_curve", []),
        trades=results.get("trades", []),
        metrics=results.get("metrics", {}),
        error_messages=results.get("errors", []),
        verification_status=results.get("verification_status", "pending"),
        timestamp=datetime.now().isoformat()
    )

@app.websocket("/ws/experiment/{experiment_id}")
async def websocket_experiment_stream(websocket: WebSocket, experiment_id: str):
    """WebSocket stream for real-time progress updates"""
    await websocket.accept()
    active_ws_connections[experiment_id] = websocket
    try:
        while True:
            exp = runner.get_experiment(experiment_id)
            if not exp:
                await websocket.send_json({"error": "Not found"})
                break
            await websocket.send_json({
                "id": experiment_id,
                "status": exp["status"],
                "progress": exp.get("progress", 0)
            })
            if exp["status"] in ["completed", "failed"]:
                if exp["status"] == "completed":
                    await websocket.send_json({
                        "event": "results",
                        "data": exp.get("results", {})
                    })
                break
            await asyncio.sleep(1)
    except (WebSocketDisconnect, Exception):
        active_ws_connections.pop(experiment_id, None)

@app.get("/experiment/queue/status")
async def get_queue_status():
    """GET /experiment/queue/status - Queue depth and stats"""
    return {
        "total_queued": queue.size(),
        "max_capacity": queue.max_size,
        "utilization_percent": (queue.size() / queue.max_size) * 100,
        "priority_breakdown": queue.get_stats()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
