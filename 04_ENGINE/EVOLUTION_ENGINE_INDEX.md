# Auto-Improvement Engine - Module Index

## Summary
Complete strategy evolution engine with 4 production-ready Python modules. Reads immutable backtest logs, analyzes results, evolves parameters, discovers indicators, orchestrates learning loop. Guardian Gate 4 compliant with full audit trails.

## Modules

### 1. strategy_analyzer.py (261 lines)
**Purpose:** Read-only analysis of backtest results
- Read immutable results from results_tracker.db
- Identify top 10 performers by: Sharpe ratio, win rate, profit factor
- Track market conditions and parameter correlations
- Immutable logging to evolution_audit.db
- Tests: 4 test cases (read results, top performers, market conditions, win rate distribution)

**Key Methods:**
- `read_all_results()` - Retrieve all backtest results
- `get_top_performers(limit=10, metric="sharpe_ratio")` - Top N strategies
- `get_by_market_condition(condition)` - Filter by market state
- `get_win_rate_distribution()` - Win rate by strategy
- `get_parameter_correlation(strategy)` - Parameter-Sharpe correlation

**Databases:**
- Input: `results_tracker.db` (immutable source)
- Output: `evolution_audit.db` (append-only audit trail)

---

### 2. parameter_evolution.py (303 lines)
**Purpose:** Generate parameter variants with systematic ±10% adjustments
- Suggest 5-10 variants per strategy using ±10% parameter adjustments
- Correlation-driven suggestions based on metric analysis
- Log variant results and track winners
- Immutable append-only evolution_log.db
- Tests: 4 test cases (variant generation, logging, winners, correlations)

**Key Methods:**
- `suggest_variants(strategy, params, sharpe, count=5)` - Generate ±10% variants
- `suggest_by_metric_correlation(strategy, correlations, params)` - Correlation-driven
- `log_variant_result(variant_id, sharpe, win_rate, parent_sharpe)` - Record backtest
- `get_winning_variants()` - Retrieve outperformers

**Databases:**
- Output: `evolution_log.db` (variant suggestions + results)

**Variation Types:**
- `increase` - Increase parameter by 10%
- `decrease` - Decrease parameter by 10%
- `correlation_driven` - Based on Sharpe correlation

---

### 3. indicator_suggester.py (330 lines)
**Purpose:** Analyze winning trades, suggest new indicators with confidence
- Analyze winning trade patterns (duration, momentum, volatility, trend)
- Suggest indicators: RSI, Bollinger Bands, ADX, ATR
- Calculate confidence scores (0.60 to 0.82)
- Filter by type and confidence threshold
- Immutable indicator_audit.db logging
- Tests: 4 test cases (trade analysis, suggestions, high confidence, by type)

**Key Methods:**
- `analyze_winning_trades(trades)` - Extract patterns from winners
- `suggest_indicators(strategy, analysis)` - Generate indicator suggestions
- `get_suggestions_by_type(type)` - Filter by: momentum, volatility, trend
- `get_high_confidence_suggestions(min_confidence=0.70)` - Filter by confidence

**Databases:**
- Output: `indicator_audit.db` (suggestions with evidence)

**Suggested Indicator Types:**
- `momentum` - RSI(5), MACD, Stochastic
- `volatility` - Bollinger Bands(20), ATR(14)
- `trend` - ADX(14), Moving Averages
- `moving_average` - SMA, EMA, WMA

---

### 4. evolution_loop.py (454 lines)
**Purpose:** Master orchestrator for full learning loop
- Monitor backtest completion count
- Trigger evolution every 1000 completed backtests
- Generate variants for top 10 strategies
- Discover indicators from winning trades
- Rank strategies by 7-day performance
- Flag promotion candidates for live trading
- Guardian Gate 4 compliant audit trail
- Tests: 4 test cases (count, trigger check, params, promotion)

**Key Methods:**
- `get_backtest_count()` - Total completed backtests
- `should_trigger_evolution()` - Check if ≥1000 new since last round
- `run_evolution_round()` - Execute full evolution round
- `promote_to_live(strategy)` - Prepare strategy for live
- `get_promotion_status(strategy)` - Check readiness score

**Databases:**
- Input: `results_tracker.db` (via StrategyAnalyzer)
- Output: `evolution_master.db` (rounds + candidates)

**Promotion Criteria:**
- 7-day Sharpe > 1.8
- 7-day win rate > 0.55
- Minimum 3 tests in 7 days
- Readiness score ≥ 0.75 (composite metric)

---

## Integration Flowchart

```
results_tracker.db (backtest results)
        ↓
strategy_analyzer.py
    (identify top performers)
        ↓
    ┌───┴───────────────────┬──────────────┐
    ↓                        ↓              ↓
parameter_evolution.py   indicator_suggester.py
    (variants)              (indicators)
    ↓                        ↓
evolution_log.db ←────────────┘
    ↓
evolution_loop.py
    (orchestrator)
    ↓
evolution_master.db
    (master log + promotion candidates)
```

---

## Database Statistics

| Database | Purpose | Append-Only | Content Hash | Records/Round |
|----------|---------|-------------|--------------|---------------|
| results_tracker | Backtest results (input) | No | N/A | +1000 |
| evolution_audit | Analysis audit trail | Yes | SHA256 | ~10 |
| evolution_log | Parameter variants | Yes | SHA256 | 50-100 |
| indicator_audit | Indicator suggestions | Yes | SHA256 | 40-60 |
| evolution_master | Master round log | Yes | SHA256 | 1 + 1-3 |

**Typical Growth (per 10,000 backtests = 10 rounds):**
- evolution_log.db: ~500 KB
- indicator_audit.db: ~300 KB
- evolution_master.db: ~200 KB
- **Total: ~1 MB per 10,000 backtests**

---

## Testing

All modules include embedded unit tests:

```bash
# Test strategy analyzer
python strategy_analyzer.py

# Test parameter evolution
python parameter_evolution.py

# Test indicator suggester
python indicator_suggester.py

# Test evolution loop orchestrator
python evolution_loop.py
```

**Coverage:**
- ✅ Data reading and filtering
- ✅ Statistical calculations
- ✅ Immutable logging
- ✅ Database transactions
- ✅ Edge cases (empty results, missing data)

---

## Guardian Gate 4 Compliance

**Security Features:**
- ✅ Content hashes (SHA256) on all ML-generated data
- ✅ Immutable append-only databases
- ✅ `authority_lock="ZERO"` on all machine-learning records
- ✅ Full reasoning + evidence for each suggestion
- ✅ Tamper detection via content hash validation

**Audit Trail Example:**
```
evolution_id → (hash) → variant_id → (hash) → backtest_result
                                     (with reasoning)
```

**For Manual Review:**
- Check `reasoning` field in every suggestion
- Monitor `confidence` scores
- Manually approve promotion candidates
- Weekly audit of variant performance

---

## Quick Start

### 1. Initialize
```python
from evolution_loop import EvolutionLoop

loop = EvolutionLoop(
    tracker_db="04_ENGINE/results_tracker.db",
    evolution_db="04_ENGINE/evolution_master.db"
)
```

### 2. Run Evolution (when 1000+ new backtests)
```python
if loop.should_trigger_evolution():
    summary = loop.run_evolution_round()
    print(f"Variants: {summary.variants_generated}")
    print(f"Indicators: {summary.indicators_suggested}")
```

### 3. Check Promotion Candidates
```python
candidate = loop.get_promotion_status("ma_crossover")
if candidate and candidate.readiness_score >= 0.75:
    # Ready for live (Authority approval needed)
    pass
```

---

## Files

| File | Lines | Role |
|------|-------|------|
| strategy_analyzer.py | 261 | Read results, identify top performers |
| parameter_evolution.py | 303 | Generate parameter variants |
| indicator_suggester.py | 330 | Analyze trades, suggest indicators |
| evolution_loop.py | 454 | Master orchestrator |
| AUTO_IMPROVEMENT_ENGINE.md | Reference documentation |
| EVOLUTION_ENGINE_INDEX.md | This file |

**Total Production Code:** ~1,350 lines (including tests, docs, comments)

---

## Performance

**Typical Evolution Round (1000 backtests → 1000 tests completed):**
- Execution time: 2-5 seconds
- Variants generated: 50-100
- Indicators suggested: 40-60
- New experiment jobs: 50-100
- Promotion candidates: 1-3

**Resource Usage:**
- Memory: ~50 MB (in-memory analysis)
- CPU: Single-threaded (can be parallelized)
- Database I/O: ~1-2 seconds

---

## Limitations & Future Work

**Current Limitations:**
1. Only adjusts numeric parameters (ignores categorical)
2. Indicator confidence based on simplified pattern matching
3. 7-day promotion window (adjust for slow strategies)
4. No variant culling (keep all for audit trail)
5. Market condition not used in suggestions

**Future Enhancements:**
1. ML-based variant ranking (gradient boosting)
2. Portfolio optimization (combine strategies)
3. Adaptive adjustment sizes (±5% to ±20%)
4. Live feedback loop (incorporate actual trading)
5. Genetic algorithms (evolve strategy logic)

---

**Version:** 1.0  
**Status:** Production Ready  
**Authority:** ZERO (locked, non-negotiable)  
**Last Updated:** 2026-09-07
