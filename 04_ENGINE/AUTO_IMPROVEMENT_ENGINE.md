# Auto-Improvement Engine for Strategy Evolution
## FlipFlop HQ - Phase 5 Strategic AI

### Overview
The auto-improvement engine automatically analyzes backtest results, evolves strategy parameters, discovers new indicators, and promotes top performers to live trading. Built for Guardian Gate 4 compliance with immutable audit trails.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Auto-Improvement Engine                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. RESULTS ANALYSIS (strategy_analyzer.py)             │   │
│  │  ├─ Read immutable results_tracker.db                   │   │
│  │  ├─ Identify top 10 by: Sharpe, win rate, profit factor│   │
│  │  ├─ Track: strategies, parameters, market conditions   │   │
│  │  └─ Log to evolution_audit.db (append-only)            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  2. PARAMETER EVOLUTION (parameter_evolution.py)        │   │
│  │  ├─ Suggest ±10% parameter adjustments                  │   │
│  │  ├─ Generate 5-10 variants per strategy                 │   │
│  │  ├─ Include metric correlations                         │   │
│  │  └─ Log to evolution_log.db (content-addressed)         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  3. INDICATOR DEVELOPMENT (indicator_suggester.py)      │   │
│  │  ├─ Analyze winning trade patterns                      │   │
│  │  ├─ Suggest: RSI, Bollinger Bands, ADX, ATR            │   │
│  │  ├─ Calculate confidence scores (0.6-0.82)             │   │
│  │  └─ Log to indicator_audit.db                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  4. LEARNING LOOP (evolution_loop.py)                   │   │
│  │  ├─ Trigger every 1000 completed backtests              │   │
│  │  ├─ Generate 5-10 new strategy variants                 │   │
│  │  ├─ Submit to experiment queue                          │   │
│  │  ├─ Rank by recent 7-day performance                    │   │
│  │  ├─ Flag top performer as promotion candidate          │   │
│  │  └─ Guardian Gate 4: full evidence trail                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  5. LIVE PROMOTION (Authority escalation)               │   │
│  │  ├─ Readiness score = (Sharpe/2.0)*0.4 + ...           │   │
│  │  ├─ Threshold: score ≥ 0.75 → ready for live           │   │
│  │  ├─ Guardian approval: Authority=ZERO (locked)         │   │
│  │  └─ When escalated: switch to live trading              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Module Details

#### 1. strategy_analyzer.py
**Purpose:** Read immutable backtest logs, identify top performers.

**Key Classes:**
- `StrategyAnalyzer`: Main analyzer
  - `read_all_results()`: Get all backtest results (immutable read)
  - `get_top_performers(limit=10, metric="sharpe_ratio")`: Top N by metric
  - `get_by_market_condition(condition)`: Filter by market state
  - `get_win_rate_distribution()`: Win rate by strategy
  - `get_parameter_correlation(strategy)`: Which params correlate with high Sharpe

**Database:**
- Input: `results_tracker.db` (read-only)
- Output: `evolution_audit.db` (append-only audit trail)

**Example:**
```python
from strategy_analyzer import StrategyAnalyzer

analyzer = StrategyAnalyzer()

# Get top 10 by Sharpe
top = analyzer.get_top_performers(limit=10)
# Returns: [("ma_crossover", 2.1), ("rsi_mean_reversion", 1.8), ...]

# Analyze parameter correlations
corr = analyzer.get_parameter_correlation("ma_crossover")
# Returns: {"fast_ma": {"values": [...], "sharpe_ratios": [...]}, ...}
```

#### 2. parameter_evolution.py
**Purpose:** Generate parameter variants using ±10% adjustments.

**Key Classes:**
- `ParameterEvolution`: Variant generator
  - `suggest_variants(strategy, params, sharpe, count=5)`: Generate variants
  - `suggest_by_metric_correlation(strategy, correlations, params)`: Correlation-driven
  - `log_variant_result(variant_id, sharpe, win_rate, parent_sharpe)`: Record test results
  - `get_winning_variants()`: Retrieve outperformers

**Database:**
- Output: `evolution_log.db` (append-only, content-addressed)

**Example:**
```python
from parameter_evolution import ParameterEvolution

evolver = ParameterEvolution()

# Suggest variants
current = {"fast_ma": 10, "slow_ma": 50, "stop_pct": 0.02}
variants = evolver.suggest_variants("ma_crossover", current, 1.8, count=5)

# Log results after backtesting
for variant in variants:
    backtest_sharpe = 1.95  # After running
    evolver.log_variant_result(variant.variant_id, backtest_sharpe, 0.65, 1.8)

# Get winners
winners = evolver.get_winning_variants()
```

**Variation Types:**
- `increase`: Increase parameter by 10%
- `decrease`: Decrease parameter by 10%
- `correlation_driven`: Based on metric correlation analysis

#### 3. indicator_suggester.py
**Purpose:** Analyze winning trades, suggest indicators with confidence scores.

**Key Classes:**
- `IndicatorSuggester`: Indicator discovery
  - `analyze_winning_trades(trades)`: Extract patterns
  - `suggest_indicators(strategy, analysis)`: Generate suggestions
  - `get_suggestions_by_type(type)`: Filter by indicator type
  - `get_high_confidence_suggestions(min_confidence=0.70)`: High-confidence only

**Database:**
- Output: `indicator_audit.db` (immutable logging)

**Example:**
```python
from indicator_suggester import IndicatorSuggester

suggester = IndicatorSuggester()

# Analyze winning trades
trades = [
    {"duration_bars": 15, "price_momentum": 0.02, "volatility": 1.2,
     "trend_at_entry": "up", "profit_factor": 2.1, "profit": 100},
    # ... more trades
]
analysis = suggester.analyze_winning_trades(trades)

# Suggest indicators
suggestions = suggester.suggest_indicators("ma_crossover", analysis)
# Returns: [
#   IndicatorSuggestion(indicator_name="Fast_RSI_5", confidence=0.82, ...),
#   IndicatorSuggestion(indicator_name="Bollinger_Bands_20", confidence=0.75, ...),
#   ...
# ]

# Get high-confidence suggestions
high_conf = suggester.get_high_confidence_suggestions(min_confidence=0.75)
```

**Suggested Indicator Types:**
- `momentum`: RSI, MACD, Stochastic
- `volatility`: Bollinger Bands, ATR
- `trend`: ADX, MACD, Moving Averages
- `moving_average`: SMA, EMA, WMA

**Confidence Calculation:**
- 0.60-0.70: Low evidence (single pattern match)
- 0.70-0.80: Moderate evidence (multiple patterns)
- 0.80+: High confidence (strong pattern alignment)

#### 4. evolution_loop.py
**Purpose:** Master orchestrator for the full learning loop.

**Key Classes:**
- `EvolutionLoop`: Master controller
  - `get_backtest_count()`: Total completed backtests
  - `should_trigger_evolution()`: Check if ≥1000 new since last round
  - `run_evolution_round()`: Execute full round
  - `promote_to_live(strategy)`: Mark for live promotion
  - `get_promotion_status(strategy)`: Check readiness

**Trigger Condition:**
- Automatically triggered every 1000 completed backtests
- Generates 5-10 new variants per top strategy
- Submits to experiment queue for testing

**Example:**
```python
from evolution_loop import EvolutionLoop

loop = EvolutionLoop()

# Check if should trigger
if loop.should_trigger_evolution():
    # Run evolution round
    round_summary = loop.run_evolution_round()
    print(f"Generated {round_summary.variants_generated} variants")
    print(f"Suggested {round_summary.indicators_suggested} indicators")
    print(f"Promotion candidate: {round_summary.promotion_candidate}")

# Check promotion status
promo = loop.get_promotion_status("ma_crossover")
if promo and promo.readiness_score > 0.75:
    # Ready for live trading
    pass
```

**Promotion Criteria:**
- Sharpe ratio (7-day): > 1.8
- Win rate (7-day): > 0.55
- Minimum tests: ≥ 3 in last 7 days
- Readiness score calculation:
  ```
  score = (sharpe/2.0)*0.4 + (win_rate/0.7)*0.3 + (profit_factor/2.0)*0.3
  ```
- Ready for live: score ≥ 0.75

### Database Schema

#### results_tracker.db (Input)
```sql
CREATE TABLE backtest_results (
    test_id TEXT PRIMARY KEY,
    strategy_name TEXT,
    parameters TEXT,  -- JSON
    sharpe_ratio REAL,
    win_rate REAL,
    profit_factor REAL,
    max_drawdown REAL,
    total_return REAL,
    num_trades INTEGER,
    market_condition TEXT,  -- "trending", "range", "volatility", etc.
    test_date TEXT  -- ISO format
)
```

#### evolution_audit.db (Immutable Log)
```sql
CREATE TABLE analysis_log (
    analysis_id TEXT PRIMARY KEY,
    timestamp REAL,
    analyzer_version TEXT,
    findings_hash TEXT,  -- SHA256 of findings
    top_performers JSON,
    market_condition_stats JSON,
    audit_proof TEXT  -- Guardian:gate4:evidence reference
)
```

#### evolution_log.db (Parameter Evolution)
```sql
CREATE TABLE evolution_log (
    evolution_id TEXT PRIMARY KEY,
    timestamp REAL,
    parent_strategy TEXT,
    parent_params JSON,
    variant_id TEXT,
    suggested_params JSON,
    variation_type TEXT,  -- "increase", "decrease", "correlation_driven"
    confidence REAL,
    reasoning TEXT,
    content_hash TEXT,  -- SHA256 for immutability
    authority_lock TEXT  -- "ZERO" (locked)
)

CREATE TABLE variant_results (
    result_id TEXT PRIMARY KEY,
    variant_id TEXT,
    backtest_date TEXT,
    sharpe_ratio REAL,
    win_rate REAL,
    outperformed_parent INTEGER,
    profit_improvement REAL
)
```

#### indicator_audit.db (Suggestions)
```sql
CREATE TABLE indicator_suggestions (
    suggestion_id TEXT PRIMARY KEY,
    timestamp REAL,
    source_strategy TEXT,
    indicator_name TEXT,
    indicator_type TEXT,  -- "momentum", "volatility", "trend", "moving_average"
    calculation TEXT,
    parameters JSON,
    confidence REAL,
    evidence_points INTEGER,
    reasoning TEXT,
    content_hash TEXT
)
```

#### evolution_master.db (Master Log)
```sql
CREATE TABLE evolution_rounds (
    round_id TEXT PRIMARY KEY,
    timestamp REAL,
    trigger_backtest_count INTEGER,
    top_performers JSON,
    variants_generated INTEGER,
    indicators_suggested INTEGER,
    promotion_candidate TEXT,
    round_status TEXT,  -- "COMPLETED", "RUNNING"
    content_hash TEXT
)

CREATE TABLE promotion_candidates (
    candidate_id TEXT PRIMARY KEY,
    timestamp REAL,
    strategy_name TEXT,
    avg_sharpe_7d REAL,
    win_rate_7d REAL,
    profit_factor_7d REAL,
    total_variants INTEGER,
    outperformance REAL,
    readiness_score REAL,
    promotion_gate_status TEXT,  -- "READY", "EVALUATING"
    authority_lock TEXT  -- "ZERO"
)
```

### Integration with FlipFlop HQ

#### Setup
1. Place all 4 modules in `04_ENGINE/`
2. Create `results_tracker.db` with backtest results
3. Initialize databases on first run

```python
from evolution_loop import EvolutionLoop

# Initialize
loop = EvolutionLoop(
    tracker_db="04_ENGINE/results_tracker.db",
    evolution_db="04_ENGINE/evolution_master.db"
)

# First run initializes all DBs
```

#### Continuous Operation
```python
# Background task (cron job, scheduler, or polling loop)
import time

while True:
    if loop.should_trigger_evolution():
        round_summary = loop.run_evolution_round()
        
        # Process variants
        for variant in round_summary.variants_generated:
            # Submit to experiment queue
            pass
    
    # Check promotion candidates
    if round_summary.promotion_candidate:
        promo = loop.get_promotion_status(round_summary.promotion_candidate)
        if promo.readiness_score >= 0.75:
            # Alert: Ready for live (Authority must escalate)
            pass
    
    time.sleep(60)  # Check every minute
```

### Guardian Gate 4 Compliance

**Audit Trail Features:**
- ✅ All analyses logged with content hashes (SHA256)
- ✅ Immutable append-only databases
- ✅ `authority_lock="ZERO"` on all machine-learning records
- ✅ Reasoning + evidence for each suggestion
- ✅ Full traceability: evolution_id → variant_id → backtest_result

**Example Audit Query:**
```python
# Retrieve evidence for Gate 4
with sqlite3.connect("evolution_master.db") as conn:
    cursor = conn.execute("""
        SELECT round_id, timestamp, top_performers, variants_generated,
               content_hash, authority_lock
        FROM evolution_rounds
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    
    for row in cursor:
        print(f"Round: {row[0]}")
        print(f"Hash: {row[4]} (immutable proof)")
        print(f"Authority: {row[5]} (ZERO = locked)")
```

### Performance Metrics

**Typical Evolution Round (1000 backtests):**
- Time: 2-5 seconds
- Variants generated: 5-10 per top strategy × 10 strategies = 50-100 variants
- Indicators suggested: 4-6 per strategy = 40-60 indicators
- New experiment queue jobs: 50-100
- Promotion candidates: 1-3

**Database Growth (per 10,000 backtests):**
- evolution_log.db: ~500 KB (50-100 variants × 10 rounds)
- indicator_audit.db: ~300 KB (suggestions)
- evolution_master.db: ~200 KB (master logs)
- Total: ~1 MB per 10,000 backtests

### Caveats & Limitations

1. **Parameter Space:** Only adjusts numeric parameters (ignores categorical)
2. **Indicator Confidence:** Based on simplified pattern matching; adjust thresholds for your domain
3. **7-Day Window:** Promotion uses recent 7-day performance; adjust for slower strategies
4. **Variant Culling:** Should implement logic to keep only winners; currently all variants logged
5. **Market Condition:** Suggestions don't filter by market condition; could add if needed

### Future Enhancements

1. **Machine Learning Ranking:** Use gradient boosting to rank variants by expected Sharpe
2. **Portfolio Optimization:** Combine multiple strategies into optimal weights
3. **Adaptive Parameters:** Adjust ±10% based on sensitivity analysis
4. **Live Feedback Loop:** Incorporate actual live trading results
5. **Genetic Algorithms:** Evolve full strategy logic (not just parameters)

### Testing

Each module includes embedded tests:
```bash
python strategy_analyzer.py      # Tests: read results, top performers, correlations
python parameter_evolution.py    # Tests: variants, correlation-driven, winners
python indicator_suggester.py    # Tests: analyze trades, suggest, filter
python evolution_loop.py         # Tests: backtest count, promotion, status
```

**Test Coverage:**
- ✅ Data reading and filtering
- ✅ Analysis calculations
- ✅ Immutable logging
- ✅ Database transactions
- ✅ Edge cases (empty results, missing data)

### Author Notes

**For Human Review:**
- Review all `reasoning` fields in suggestion logs
- Monitor `confidence` scores to adjust thresholds
- Manually approve promotion candidates before live deployment
- Weekly audit of variant performance vs. parent

**For Automation:**
- `authority_lock="ZERO"` prevents unauthorized modifications
- All logs are append-only (immutable)
- Content hashes enable tamper detection
- Guardian Gate 4 has full evidence trail

---

**Version:** 1.0  
**Created:** 2026-09-07  
**Authority:** ZERO (locked, non-negotiable)
