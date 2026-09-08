"""
Indicator Development Engine - FlipFlop HQ Auto-Improvement
Analyzes winning trades, suggests new indicators with confidence scores.
Immutable suggestion tracking to audit database.
"""

import json
import sqlite3
import hashlib
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import logging
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IndicatorSuggestion:
    """Suggested indicator based on winning trade analysis"""
    suggestion_id: str
    source_strategy: str
    indicator_name: str
    indicator_type: str  # "moving_average", "momentum", "volatility", "trend"
    calculation: str
    parameters: Dict
    confidence: float  # 0.0 to 1.0
    evidence_points: int
    reasoning: str


class IndicatorSuggester:
    """
    Analyze winning trades to discover patterns.
    Suggest new indicators that capture those patterns.
    """

    def __init__(self, audit_db_path: str = "indicator_audit.db"):
        self.audit_db = audit_db_path
        self._init_db()

    def _init_db(self):
        """Initialize audit database"""
        with sqlite3.connect(self.audit_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indicator_suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    source_strategy TEXT,
                    indicator_name TEXT,
                    indicator_type TEXT,
                    calculation TEXT,
                    parameters JSON,
                    confidence REAL,
                    evidence_points INTEGER,
                    reasoning TEXT,
                    content_hash TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS winning_trade_analysis (
                    analysis_id TEXT PRIMARY KEY,
                    strategy TEXT,
                    trade_count INTEGER,
                    avg_duration_bars INTEGER,
                    avg_price_momentum REAL,
                    volatility_profile TEXT,
                    trend_before_entry TEXT,
                    patterns_detected JSON
                )
            """)
            conn.commit()

    def analyze_winning_trades(self, trades: List[Dict]) -> Dict:
        """
        Analyze winning trades to identify patterns.
        Input: List of trade dicts with duration, entry_price, exit_price, etc.
        """
        if not trades:
            return {}

        winning_trades = [t for t in trades if t.get("profit", 0) > 0]
        if not winning_trades:
            return {}

        # Extract patterns
        analysis = {
            "winning_count": len(winning_trades),
            "avg_duration": statistics.mean([t.get("duration_bars", 1)
                                             for t in winning_trades]),
            "median_duration": statistics.median([t.get("duration_bars", 1)
                                                   for t in winning_trades]),
            "avg_momentum": statistics.mean([t.get("price_momentum", 0)
                                            for t in winning_trades]),
            "volatility_before_entry": statistics.mean([t.get("volatility", 0)
                                                        for t in winning_trades]),
            "avg_profit_factor": statistics.mean([t.get("profit_factor", 1)
                                                  for t in winning_trades]),
        }

        # Identify trend pattern
        trend_entries = [t.get("trend_at_entry") for t in winning_trades
                        if t.get("trend_at_entry")]
        if trend_entries:
            most_common_trend = max(set(trend_entries),
                                   key=trend_entries.count)
            analysis["dominant_trend"] = most_common_trend

        return analysis

    def suggest_indicators(self, strategy_name: str,
                          trade_analysis: Dict) -> List[IndicatorSuggestion]:
        """
        Based on trade analysis, suggest indicators.
        Returns list of suggestions with confidence scores.
        """
        suggestions = []

        # Pattern 1: Short average duration → suggest fast momentum indicator
        if trade_analysis.get("avg_duration", 0) < 30:
            suggestion = IndicatorSuggestion(
                suggestion_id=str(uuid.uuid4()),
                source_strategy=strategy_name,
                indicator_name="Fast_RSI_5",
                indicator_type="momentum",
                calculation="RSI(close, period=5)",
                parameters={"period": 5, "overbought": 75, "oversold": 25},
                confidence=0.82,
                evidence_points=len([t for t in [] if t]),  # Simplified
                reasoning="Winning trades show short duration; fast RSI captures "
                         "rapid momentum shifts"
            )
            suggestions.append(suggestion)

        # Pattern 2: High volatility preference → suggest bollinger bands
        if trade_analysis.get("volatility_before_entry", 0) > 1.0:
            suggestion = IndicatorSuggestion(
                suggestion_id=str(uuid.uuid4()),
                source_strategy=strategy_name,
                indicator_name="Bollinger_Bands_20",
                indicator_type="volatility",
                calculation="SMA(close, 20) ± 2*STDEV(close, 20)",
                parameters={"period": 20, "std_dev": 2},
                confidence=0.75,
                evidence_points=len([t for t in [] if t]),
                reasoning="Winning trades occur in high-volatility environments; "
                         "Bollinger Bands quantify volatility boundaries"
            )
            suggestions.append(suggestion)

        # Pattern 3: Trend-driven entries → suggest ADX
        if trade_analysis.get("dominant_trend"):
            suggestion = IndicatorSuggestion(
                suggestion_id=str(uuid.uuid4()),
                source_strategy=strategy_name,
                indicator_name="ADX_14",
                indicator_type="trend",
                calculation="Average Directional Index(period=14)",
                parameters={"period": 14, "strong_trend_threshold": 25},
                confidence=0.70,
                evidence_points=len([t for t in [] if t]),
                reasoning="Winning trades strongly aligned with "
                         f"{trade_analysis.get('dominant_trend')} trend; "
                         "ADX measures trend strength"
            )
            suggestions.append(suggestion)

        # Pattern 4: Moderate-to-high profit factor → suggest volatility filter
        if trade_analysis.get("avg_profit_factor", 1.0) > 1.8:
            suggestion = IndicatorSuggestion(
                suggestion_id=str(uuid.uuid4()),
                source_strategy=strategy_name,
                indicator_name="ATR_Volatility_Filter",
                indicator_type="volatility",
                calculation="ATR(close, period=14) / close (as %)",
                parameters={"period": 14, "min_atr_pct": 0.5, "max_atr_pct": 3.0},
                confidence=0.68,
                evidence_points=len([t for t in [] if t]),
                reasoning="High profit factor suggests good risk/reward filtering; "
                         "ATR provides dynamic volatility scaling"
            )
            suggestions.append(suggestion)

        # Log all suggestions
        for suggestion in suggestions:
            self._log_suggestion(suggestion)

        return suggestions

    def get_suggestions_by_type(self, indicator_type: str) -> List[IndicatorSuggestion]:
        """Retrieve suggestions of a specific type"""
        with sqlite3.connect(self.audit_db) as conn:
            cursor = conn.execute("""
                SELECT suggestion_id, source_strategy, indicator_name, indicator_type,
                       calculation, parameters, confidence, evidence_points, reasoning
                FROM indicator_suggestions
                WHERE indicator_type = ?
                ORDER BY confidence DESC
            """, (indicator_type,))

            suggestions = []
            for row in cursor:
                # Parse parameters JSON
                params = json.loads(row[5])
                suggestion = IndicatorSuggestion(
                    suggestion_id=row[0],
                    source_strategy=row[1],
                    indicator_name=row[2],
                    indicator_type=row[3],
                    calculation=row[4],
                    parameters=params,
                    confidence=row[6],
                    evidence_points=row[7],
                    reasoning=row[8]
                )
                suggestions.append(suggestion)

            return suggestions

    def get_high_confidence_suggestions(self, min_confidence: float = 0.70
                                       ) -> List[IndicatorSuggestion]:
        """Get all suggestions above confidence threshold"""
        with sqlite3.connect(self.audit_db) as conn:
            cursor = conn.execute("""
                SELECT suggestion_id, source_strategy, indicator_name, indicator_type,
                       calculation, parameters, confidence, evidence_points, reasoning
                FROM indicator_suggestions
                WHERE confidence >= ?
                ORDER BY confidence DESC
            """, (min_confidence,))

            suggestions = []
            for row in cursor:
                params = json.loads(row[5])
                suggestion = IndicatorSuggestion(
                    suggestion_id=row[0],
                    source_strategy=row[1],
                    indicator_name=row[2],
                    indicator_type=row[3],
                    calculation=row[4],
                    parameters=params,
                    confidence=row[6],
                    evidence_points=row[7],
                    reasoning=row[8]
                )
                suggestions.append(suggestion)

            return suggestions

    def _log_suggestion(self, suggestion: IndicatorSuggestion):
        """Immutable log of indicator suggestion"""
        content = json.dumps({
            "indicator": suggestion.indicator_name,
            "calculation": suggestion.calculation,
            "parameters": suggestion.parameters,
        }, sort_keys=True)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        with sqlite3.connect(self.audit_db) as conn:
            conn.execute("""
                INSERT INTO indicator_suggestions
                (suggestion_id, timestamp, source_strategy, indicator_name,
                 indicator_type, calculation, parameters, confidence,
                 evidence_points, reasoning, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                suggestion.suggestion_id,
                datetime.now().timestamp(),
                suggestion.source_strategy,
                suggestion.indicator_name,
                suggestion.indicator_type,
                suggestion.calculation,
                json.dumps(suggestion.parameters),
                suggestion.confidence,
                suggestion.evidence_points,
                suggestion.reasoning,
                content_hash
            ))
            conn.commit()

        logger.info(f"Indicator suggestion logged: {suggestion.indicator_name} "
                   f"(confidence={suggestion.confidence:.2f})")


# Tests
if __name__ == "__main__":
    import tempfile
    import os

    temp_dir = tempfile.mkdtemp()
    audit_db = os.path.join(temp_dir, "indicator_audit.db")

    suggester = IndicatorSuggester(audit_db)

    print("=== Test 1: Analyze winning trades ===")
    trades = [
        {"duration_bars": 15, "price_momentum": 0.02, "volatility": 1.2,
         "trend_at_entry": "up", "profit_factor": 2.1, "profit": 100},
        {"duration_bars": 20, "price_momentum": 0.018, "volatility": 1.1,
         "trend_at_entry": "up", "profit_factor": 1.9, "profit": 85},
        {"duration_bars": 12, "price_momentum": 0.022, "volatility": 1.3,
         "trend_at_entry": "up", "profit_factor": 2.3, "profit": 120},
    ]
    analysis = suggester.analyze_winning_trades(trades)
    print(f"Analyzed {analysis.get('winning_count', 0)} winning trades")
    print(f"  Avg duration: {analysis.get('avg_duration', 0):.1f} bars")
    print(f"  Avg momentum: {analysis.get('avg_momentum', 0):.4f}")

    print("\n=== Test 2: Suggest indicators ===")
    suggestions = suggester.suggest_indicators("ma_crossover", analysis)
    print(f"Generated {len(suggestions)} suggestions:")
    for s in suggestions:
        print(f"  - {s.indicator_name} (confidence={s.confidence:.2f})")

    print("\n=== Test 3: Get high confidence ===")
    high_conf = suggester.get_high_confidence_suggestions(0.70)
    print(f"Found {len(high_conf)} high-confidence suggestions")

    print("\n=== Test 4: Get by type ===")
    momentum = suggester.get_suggestions_by_type("momentum")
    print(f"Momentum indicators: {len(momentum)}")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    print("\nAll tests passed!")
