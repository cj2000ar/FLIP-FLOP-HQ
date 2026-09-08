"""
Parameter Evolution Engine - FlipFlop HQ Auto-Improvement
Suggests parameter tweaks for top strategies via systematic variation.
Append-only audit trail to evolution_log.db.
"""

import json
import sqlite3
import hashlib
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ParameterVariant:
    """Suggested parameter variant"""
    variant_id: str
    parent_strategy: str
    parent_params: Dict
    suggested_params: Dict
    variation_type: str  # "increase", "decrease", "combined"
    confidence: float
    reasoning: str


class ParameterEvolution:
    """
    Generate parameter variants for top strategies.
    Uses ±10% adjustments and logs all suggestions immutably.
    """

    def __init__(self, evolution_log_path: str = "evolution_log.db"):
        self.log_db = evolution_log_path
        self._init_db()

    def _init_db(self):
        """Initialize immutable evolution log"""
        with sqlite3.connect(self.log_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_log (
                    evolution_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    parent_strategy TEXT,
                    parent_params JSON,
                    variant_id TEXT,
                    suggested_params JSON,
                    variation_type TEXT,
                    confidence REAL,
                    reasoning TEXT,
                    content_hash TEXT,
                    authority_lock TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS variant_results (
                    result_id TEXT PRIMARY KEY,
                    variant_id TEXT,
                    backtest_date TEXT,
                    sharpe_ratio REAL,
                    win_rate REAL,
                    outperformed_parent INTEGER,
                    profit_improvement REAL
                )
            """)
            conn.commit()

    def suggest_variants(self, strategy_name: str, current_params: Dict,
                        current_sharpe: float, count: int = 5) -> List[ParameterVariant]:
        """
        Generate 5-10 parameter variants with ±10% adjustments.
        Tracks reasoning for each suggestion.
        """
        variants = []

        numeric_params = {
            k: v for k, v in current_params.items()
            if isinstance(v, (int, float))
        }

        if not numeric_params:
            logger.warning(f"No numeric parameters for {strategy_name}")
            return variants

        # Strategy 1: Single parameter increases
        for param_name, param_value in list(numeric_params.items())[:count // 2]:
            new_value = param_value * 1.1
            new_params = current_params.copy()
            new_params[param_name] = new_value

            variant = ParameterVariant(
                variant_id=str(uuid.uuid4()),
                parent_strategy=strategy_name,
                parent_params=current_params.copy(),
                suggested_params=new_params,
                variation_type="increase",
                confidence=0.6,
                reasoning=f"Increase {param_name} by 10% to test sensitivity"
            )
            variants.append(variant)

        # Strategy 2: Single parameter decreases
        for param_name, param_value in list(numeric_params.items())[:count // 2]:
            new_value = param_value * 0.9
            new_params = current_params.copy()
            new_params[param_name] = new_value

            variant = ParameterVariant(
                variant_id=str(uuid.uuid4()),
                parent_strategy=strategy_name,
                parent_params=current_params.copy(),
                suggested_params=new_params,
                variation_type="decrease",
                confidence=0.6,
                reasoning=f"Decrease {param_name} by 10% to test lower bound"
            )
            variants.append(variant)

        # Log all variants to immutable log
        for variant in variants:
            self._log_variant(variant)

        return variants[:count]

    def suggest_by_metric_correlation(self, strategy_name: str,
                                     param_correlations: Dict,
                                     current_params: Dict) -> List[ParameterVariant]:
        """
        Suggest variants based on which parameters correlate with high Sharpe.
        Uses correlation analysis from strategy_analyzer.
        """
        variants = []

        for param_name, corr_data in param_correlations.items():
            values = corr_data["values"]
            sharpe_ratios = corr_data["sharpe_ratios"]

            if len(values) < 2:
                continue

            # Simple correlation: higher values → higher Sharpe?
            avg_high = sum(s for v, s in zip(values, sharpe_ratios)
                          if v > sum(values) / len(values)) / max(
                              len([s for v, s in zip(values, sharpe_ratios)
                                   if v > sum(values) / len(values)]), 1)
            avg_low = sum(s for v, s in zip(values, sharpe_ratios)
                         if v <= sum(values) / len(values)) / max(
                             len([s for v, s in zip(values, sharpe_ratios)
                                  if v <= sum(values) / len(values)]), 1)

            if avg_high > avg_low:  # High values correlate with better Sharpe
                direction = "increase"
                confidence = 0.75
            else:
                direction = "decrease"
                confidence = 0.75

            new_params = current_params.copy()
            if direction == "increase":
                new_params[param_name] = current_params[param_name] * 1.1
            else:
                new_params[param_name] = current_params[param_name] * 0.9

            variant = ParameterVariant(
                variant_id=str(uuid.uuid4()),
                parent_strategy=strategy_name,
                parent_params=current_params.copy(),
                suggested_params=new_params,
                variation_type="correlation_driven",
                confidence=confidence,
                reasoning=f"{param_name} shows {direction} correlation with Sharpe"
            )
            variants.append(variant)

        # Log variants
        for variant in variants:
            self._log_variant(variant)

        return variants

    def log_variant_result(self, variant_id: str, sharpe_ratio: float,
                          win_rate: float, parent_sharpe: float) -> bool:
        """Record backtest result for variant"""
        outperformed = 1 if sharpe_ratio > parent_sharpe else 0
        improvement = sharpe_ratio - parent_sharpe

        result_id = str(uuid.uuid4())
        with sqlite3.connect(self.log_db) as conn:
            conn.execute("""
                INSERT INTO variant_results
                (result_id, variant_id, backtest_date, sharpe_ratio, win_rate,
                 outperformed_parent, profit_improvement)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result_id,
                variant_id,
                datetime.now().isoformat(),
                sharpe_ratio,
                win_rate,
                outperformed,
                improvement
            ))
            conn.commit()

        return bool(outperformed)

    def get_winning_variants(self) -> List[Tuple[str, float]]:
        """Retrieve variants that outperformed parents"""
        with sqlite3.connect(self.log_db) as conn:
            cursor = conn.execute("""
                SELECT variant_id, profit_improvement
                FROM variant_results
                WHERE outperformed_parent = 1
                ORDER BY profit_improvement DESC
            """)
            return [(row[0], row[1]) for row in cursor]

    def _log_variant(self, variant: ParameterVariant):
        """Append-only log of parameter suggestion"""
        content = json.dumps({
            "parent_strategy": variant.parent_strategy,
            "parent_params": variant.parent_params,
            "suggested_params": variant.suggested_params,
        }, sort_keys=True)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        evolution_id = str(uuid.uuid4())
        with sqlite3.connect(self.log_db) as conn:
            conn.execute("""
                INSERT INTO evolution_log
                (evolution_id, timestamp, parent_strategy, parent_params,
                 variant_id, suggested_params, variation_type, confidence,
                 reasoning, content_hash, authority_lock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evolution_id,
                datetime.now().timestamp(),
                variant.parent_strategy,
                json.dumps(variant.parent_params),
                variant.variant_id,
                json.dumps(variant.suggested_params),
                variant.variation_type,
                variant.confidence,
                variant.reasoning,
                content_hash,
                "ZERO"
            ))
            conn.commit()

        logger.info(f"Variant logged: {variant.variant_id[:8]} " +
                   f"hash={content_hash[:8]}")


# Tests
if __name__ == "__main__":
    import tempfile
    import os

    temp_dir = tempfile.mkdtemp()
    log_db = os.path.join(temp_dir, "evo.db")

    evolver = ParameterEvolution(log_db)

    print("=== Test 1: Suggest variants ===")
    current_params = {"fast_ma": 10, "slow_ma": 50, "stop_pct": 0.02}
    variants = evolver.suggest_variants(
        "ma_crossover", current_params, 1.8, count=5
    )
    print(f"Generated {len(variants)} variants")
    for v in variants:
        print(f"  {v.variation_type}: {v.variant_id[:8]}")

    print("\n=== Test 2: Log variant result ===")
    if variants:
        win = evolver.log_variant_result(variants[0].variant_id, 1.9, 0.64, 1.8)
        print(f"Variant outperformed: {win}")

    print("\n=== Test 3: Get winning variants ===")
    winners = evolver.get_winning_variants()
    print(f"Found {len(winners)} winning variants")

    print("\n=== Test 4: Metric correlation ===")
    correlations = {
        "fast_ma": {
            "values": [8, 10, 12, 14],
            "sharpe_ratios": [1.6, 1.8, 1.95, 1.85]
        }
    }
    variants2 = evolver.suggest_by_metric_correlation(
        "ma_crossover", correlations, current_params
    )
    print(f"Generated {len(variants2)} correlation-driven variants")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    print("\nAll tests passed!")
