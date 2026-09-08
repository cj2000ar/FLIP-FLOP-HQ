# Experiment API - 24/7 User Script Submission System

**Authority: ZERO** - All experiment submissions logged, audited, and verified via Guardian Gates 4/5.

## Overview

The Experiment API enables users to submit custom trading strategies for automated backtesting during 24/7 operation. Features include:

- **Safe Script Submission** - User strategies validated for syntax, banned imports, and sandbox violations
- **Priority Queue** - FIFO queue (max 100) with HIGH/NORMAL/LOW priority levels
- **Isolated Execution** - Strategies run in subprocess sandboxes with resource limits (5 min timeout, 512MB memory)
- **Real-time Status** - Poll via REST or stream via WebSocket
- **Complete Results** - Backtest metrics, equity curve, trades, and Guardian verification status

## Modules

### 1. experiment_api.py (232 lines)
FastAPI application exposing REST endpoints and WebSocket streams.

**Key Endpoints:**
```
POST   /experiment/submit               Submit strategy code
GET    /experiment/{id}/status          Poll progress
GET    /experiment/{id}/results         Get final results
WS     /ws/experiment/{id}              Stream updates
GET    /experiment/queue/status         Queue depth + stats
```

### 2. experiment_queue.py (200 lines)
FIFO queue with priority levels, thread-safe operations.

**Features:**
- Max 100 experiments queued
- Priorities: HIGH (1) > NORMAL (2) > LOW (3)
- Atomic enqueue/dequeue with position tracking
- Stats by priority level

### 3. safety_sandbox.py (234 lines)
AST-based code validator + safe execution environment.

**Security Checks:**
- Syntax validation (must define `execute_strategy` function)
- Banned modules: os, sys, subprocess, socket, urllib, etc.
- Banned calls: eval, exec, compile, open, __import__
- Banned attributes: os.*, sys.*, socket.*, urllib.*, place_order()
- Banned patterns: live order placement

**Safe Imports Allowed:**
- numpy, pandas (if installed)
- math, statistics, datetime

### 4. experiment_runner.py (226 lines)
Manages experiment execution in isolated subprocess.

**Features:**
- Continuous queue processor (async)
- 5-minute timeout per experiment
- Resource limits: CPU/memory capped
- Automatic cleanup + rollback on crash
- Audit trail: all executions logged

## API Usage

### 1. Submit Strategy

```bash
curl -X POST http://localhost:8001/experiment/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RSI_Breakout_v1",
    "description": "RSI-based breakout strategy",
    "strategy_code": "def execute_strategy(context):\n    return {\"action\": \"hold\"}",
    "parameters": {"rsi_threshold": 70, "period": 14},
    "priority": "high"
  }'
```

**Response:**
```json
{
  "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "exp-20260907120000-550e8400",
  "queue_position": 2,
  "status": "queued",
  "timestamp": "2026-09-07T12:00:00Z",
  "message": "Strategy queued at position 2"
}
```

### 2. Poll Status

```bash
curl http://localhost:8001/experiment/550e8400-e29b-41d4-a716-446655440000/status
```

**Response:**
```json
{
  "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress_percent": 45,
  "eta_seconds": 120,
  "error_message": null,
  "queue_position": null
}
```

### 3. Get Results

```bash
curl http://localhost:8001/experiment/550e8400-e29b-41d4-a716-446655440000/results
```

**Response:**
```json
{
  "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "total_trades": 42,
  "win_rate": 0.64,
  "profit_factor": 1.85,
  "max_drawdown": 0.12,
  "equity_curve": [10000, 10250, 10180, ...],
  "trades": [
    {"entry": 100, "exit": 102, "pnl": 200, "type": "long"},
    ...
  ],
  "metrics": {"sharpe": 1.2, "calmar": 1.8},
  "error_messages": [],
  "verification_status": "pending",
  "timestamp": "2026-09-07T12:05:00Z"
}
```

### 4. Stream WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/experiment/550e8400-e29b-41d4-a716-446655440000');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}% - ${data.status}`);
  if (data.event === 'results') {
    console.log('Backtest complete:', data.data);
  }
};
```

### 5. Queue Status

```bash
curl http://localhost:8001/experiment/queue/status
```

**Response:**
```json
{
  "total_queued": 5,
  "max_capacity": 100,
  "utilization_percent": 5.0,
  "priority_breakdown": {
    "high": 1,
    "normal": 3,
    "low": 1
  }
}
```

## Strategy Code Example

Users must define an `execute_strategy(context)` function:

```python
def execute_strategy(context):
    """
    context.params - Dict of submission parameters
    context.get_prices() - Returns list of mock prices
    context.trades - Executed trades (populated by strategy)
    context.equity_curve - Running equity (populated by strategy)
    """
    prices = context.get_prices()
    
    # Calculate simple moving average
    sma_20 = sum(p["close"] for p in prices[-20:]) / 20
    
    # Buy/sell logic
    if prices[-1]["close"] > sma_20:
        return {"action": "buy", "quantity": 100}
    else:
        return {"action": "sell", "quantity": 100}
```

## Security Model

### Submission Phase (Safety Validator)
1. **Syntax Check** - Verify valid Python, require `execute_strategy` function
2. **Sandbox Check** - Reject banned modules/calls/attributes
3. **Pattern Match** - Detect live order attempts (place_order, submit_order)
4. **Return** - Accept/reject with specific error messages

### Execution Phase (Experiment Runner)
1. **Subprocess Isolation** - Run in fresh process, no access to parent
2. **Resource Limits** - 5-minute timeout, CPU/memory caps
3. **I/O Sandboxing** - No file/network access via wrapper
4. **Crash Recovery** - Automatic rollback on timeout/exception
5. **Audit Logging** - All submissions + results logged to database

### Verification Phase (Guardian)
1. **Gate 4** - Verify execution integrity (time bounds, resource limits)
2. **Gate 5** - Canary execution on subset of data
3. **Authority Check** - ZERO-level authority required for any modifications
4. **Audit Trail** - Immutable record of all decisions

## Deployment

### Start API Server
```bash
cd /path/to/04_ENGINE
python -m uvicorn experiment_api:app --host 0.0.0.0 --port 8001 --workers 1
```

### Environment Variables
```bash
# Optional: Set queue size
export EXPERIMENT_MAX_QUEUE=100

# Optional: Set timeout (seconds)
export EXPERIMENT_MAX_TIME=300

# Optional: Set memory limit (MB)
export EXPERIMENT_MAX_MEMORY=512
```

### Docker
```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY experiment_*.py .
EXPOSE 8001
CMD ["python", "-m", "uvicorn", "experiment_api:app", "--host", "0.0.0.0"]
```

## Testing

Run all tests:
```bash
python -m pytest test_experiment_api.py -v
```

**Coverage:**
- Queue: FIFO ordering, priority, capacity, removal
- Sandbox: Syntax validation, banned imports/calls, safe environment
- Runner: Strategy wrapping, subprocess execution, error handling
- Integration: End-to-end submission → status → results flow

## Performance

- **Queue Enqueue/Dequeue**: O(n) insertion for priority ordering, O(1) dequeue
- **Validation**: ~10ms per strategy (AST parse + pattern matching)
- **Execution**: 5 min max per experiment
- **Throughput**: 1 experiment every 5 minutes (sequential mode), 12 per hour

## Monitoring

### Prometheus Metrics
- `experiment_submissions_total` - Total strategies submitted
- `experiment_queue_size` - Current queue depth
- `experiment_duration_seconds` - Execution time histogram
- `experiment_errors_total` - Failed executions

### Audit Logging
Every submission logged with:
- `experiment_id`, `correlation_id`, `timestamp`
- User/API key
- Strategy code hash
- Validation results
- Execution status + time
- Results summary

## Limitations & Future Work

### Current Limitations
- Sequential execution (1 experiment at a time)
- 5-minute timeout per experiment
- Limited to backtest data (no live market access)
- No ML/PyTorch (heavy dependencies not allowed)

### Roadmap
1. Parallel execution (4+ simultaneous experiments)
2. Tiered resource limits (normal/high/enterprise)
3. Strategy versioning + rollback
4. Experiment scheduling (run daily/weekly)
5. Guardian Gate 4 integration for real-time verification
6. Performance profiling per strategy

## Support

For issues:
1. Check `experiment_id` in /experiment/{id}/status
2. Review error_message field
3. Validate strategy syntax locally
4. Check /experiment/queue/status for queue health
5. Contact ops team with correlation_id
