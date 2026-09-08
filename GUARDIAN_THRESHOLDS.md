# Guardian Gate Thresholds (Tunable)

## Current Thresholds

### Gate 1: Authorization (FIXED)
- Requirement: Valid owner MFA
- Tunable: NO (security critical)

### Gate 2: Audit Chain (FIXED)
- Requirement: Chain integrity verified
- Tunable: NO (immutable guarantee)

### Gate 3: Replay Determinism (FIXED)
- Requirement: Holdout partition valid
- Tunable: NO (correctness critical)

### Gate 4: Market Data Quality (TUNABLE)
- Current: Quality score ≥ 0.3 (30%)
- Adjustment: Edit in market_downloader.py:
```python
QUALITY_THRESHOLD = 0.3  # Increase for stricter, decrease for lenient
```
- Impact: Blocks stale/corrupted data

### Gate 5: Canary Executor (TUNABLE)
- Current: Error rate ≤ 5%, latency ≤ 200ms
- Adjustment: Edit in job_orchestrator.py:
```python
ERROR_RATE_THRESHOLD = 0.05  # 5%
LATENCY_THRESHOLD_MS = 200   # milliseconds
```
- Impact: Stops failing jobs, triggers rollback

### Gate 6: Risk Limits (TUNABLE)
- Current: Max drawdown ≤ 8%, daily loss ≤ 5%
- Adjustment: Edit in guardian_enforcement.py:
```python
MAX_DRAWDOWN = 0.08      # 8%
MAX_DAILY_LOSS = 0.05    # 5%
MAX_POSITION_SIZE = 5    # contracts
```
- Impact: Blocks high-risk trades

### Gate 7: Data Freshness (TUNABLE)
- Current: Evidence ≤ 5 minutes old
- Adjustment: Edit in backend_api.py:
```python
FRESHNESS_THRESHOLD_SECONDS = 300  # 5 minutes = 300s
```
- Change to:
  - 600 = 10 min (lenient)
  - 300 = 5 min (current)
  - 180 = 3 min (strict)
- Impact: Blocks stale market data

### Gate 8: Authority-ZERO (FIXED)
- Requirement: No live trading allowed
- Tunable: NO (by design, immutable)

## Tuning Strategy

### Conservative (High Safety)
```
Quality: 0.5 (high)
Error rate: 0.02 (2%)
Latency: 100ms (strict)
Max drawdown: 0.05 (5%)
Daily loss: 0.02 (2%)
Data freshness: 180s (3 min)
```

### Moderate (Balanced)
```
Quality: 0.3 (current)
Error rate: 0.05 (5%)
Latency: 200ms (current)
Max drawdown: 0.08 (8%)
Daily loss: 0.05 (5%)
Data freshness: 300s (5 min) [current]
```

### Lenient (Production-Ready)
```
Quality: 0.1 (low)
Error rate: 0.10 (10%)
Latency: 500ms (relaxed)
Max drawdown: 0.15 (15%)
Daily loss: 0.10 (10%)
Data freshness: 600s (10 min)
```

## Recommendations

- **Start**: Moderate (current settings)
- **After 1 week**: Tighten data freshness to 180s if stable
- **After 1 month**: Consider raising quality threshold to 0.5
- **Live trading (if enabled)**: Use Conservative thresholds

## Monitor Impact

Check these metrics after threshold changes:

1. **Gate block rate**: How many operations get blocked?
2. **False positives**: Legitimate trades blocked?
3. **False negatives**: Bad trades got through?
4. **Execution latency**: Time to complete checks?

## Examples

### Example 1: Frequent "Data is Stale" Blocks
**Problem**: Data freshness threshold too strict (180s)
**Solution**: Increase to 300s, verify market data updating
**Command**:
```python
# backend_api.py line 19
FRESHNESS_THRESHOLD_SECONDS = 300
```

### Example 2: Risk Limits Blocking Good Trades
**Problem**: Max drawdown threshold too low (5%)
**Solution**: Increase to 10% if backtest shows valid
**Command**:
```python
# guardian_enforcement.py
MAX_DRAWDOWN = 0.10
```

### Example 3: Too Many Execution Errors
**Problem**: Error rate threshold too strict (2%)
**Solution**: Increase to 5% if errors are transient
**Command**:
```python
# job_orchestrator.py
ERROR_RATE_THRESHOLD = 0.05
```

## Verification

After changing thresholds:

```bash
# Restart scheduler
Restart-ScheduledTask -TaskName "FlipFlop-Scheduler"

# Monitor logs
Get-Content "C:\ProgramData\FlipFlop\logs\scheduler.log" -Tail 20

# Check gate activity
curl http://localhost:8000/guardian/wounds
```

Authority-ZERO gates can be tuned for strictness,  
but never disabled or bypassed.
