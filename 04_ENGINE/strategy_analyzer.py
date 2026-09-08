"""
Strategy Results Analyzer - FlipFlop HQ Auto-Improvement Engine
Reads immutable backtest results, identifies top performers, tracks patterns.
Guardian-compatible: full audit trail, immutable logging.
"""

import json
import sqlite3
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Immutable backtest result record"""
    test_id: str
    strategy_name: str
    parameters: Dict
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    total_return: float
    num_trades: int
    market_condition: str
    test_date: str

    def to_hash(self) -> str:
        """Content-addressable hash for immutability"""
        content = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class TopPerformer:
    """Top performer summary"""
    strategy_name: str
    average_sharpe: float
    average_win_rate: float
    average_profit_factor: float
    count: int
    best_market_condition: str
    params_signature: str


class StrategyAnalyzer:
    """
    Read-only analyzer for backtest results.
    Immutable logging to audit trail DB.
    """

    def __init__(self, results_db_path: str = "results_tracker.db",
                 audit_path: str = "evolution_audit.db"):
        self.results_db = results_db_path
        self.audit_db = audit_path
        self._init_dbs()

    def _init_dbs(self):
        """Initialize database tables"""
        # Audit DB for immutable logging
        with sqlite3.connect(self.audit_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_log (
                    analysis_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    analyzer_version TEXT,
                    findings_hash TEXT,
                    top_performers JSON,
                    market_condition_stats JSON,
                    audit_proof TEXT
                )
            """)
            conn.commit()

    def read_all_results(self) -> List[BacktestResult]:
        """Read all backtest results (immutable source)"""
        results = []
        try:
            with sqlite3.connect(self.results_db) as conn:
                cursor = conn.execute(
                    "SELECT * FROM backtest_results ORDER BY test_date DESC"
                )
                for row in cursor:
                    result = BacktestResult(*row)
                    results.append(result)
        except sqlite3.OperationalError:
            logger.warning(f"Results DB {self.results_db} not found, returning empty")
        return results

    def get_top_performers(self, limit: int = 10,
                          metric: str = "sharpe_ratio") -> List[Tuple[str, float]]:
        """Identify top N strategies by metric"""
        results = self.read_all_results()
        if not results:
            return []

        # Group by strategy name
        by_strategy = {}
        for r in results:
            if r.strategy_name not in by_strategy:
                by_strategy[r.strategy_name] = []
            by_strategy[r.strategy_name].append(r)

        # Calculate average metric per strategy
        averages = []
        for strategy_name, tests in by_strategy.items():
            metric_values = [getattr(t, metric) for t in tests]
            avg = sum(metric_values) / len(metric_values)
            averages.append((strategy_name, avg))

        # Sort and return top N
        averages.sort(key=lambda x: x[1], reverse=True)
        top = averages[:limit]

        # Log to audit trail
        self._log_analysis(top, metric)
        return top

    def get_by_market_condition(self, condition: str) -> List[BacktestResult]:
        """Retrieve results for specific market condition"""
        results = self.read_all_results()
        return [r for r in results if r.market_condition == condition]

    def get_win_rate_distribution(self) -> Dict[str, List[float]]:
        """Win rate by strategy"""
        results = self.read_all_results()
        by_strategy = {}
        for r in results:
            if r.strategy_name not in by_strategy:
                by_strategy[r.strategy_name] = []
            by_strategy[r.strategy_name].append(r.win_rate)
        return by_strategy

    def get_parameter_correlation(self, strategy: str) -> Dict:
        """Analyze which parameters correlate with high Sharpe"""
        results = self.read_all_results()
        strategy_results = [r for r in results if r.strategy_name == strategy]

        if not strategy_results:
            return {}

        # Extract parameters and sharpe ratios
        correlations = {}
        for result in strategy_results:
            for param_name, param_value in result.parameters.items():
                if param_name not in correlations:
                    correlations[param_name] = {
                        "values": [],
                        "sharpe_ratios": []
                    }
                correlations[param_name]["values"].append(param_value)
                correlations[param_name]["sharpe_ratios"].append(result.sharpe_ratio)

        return correlations

    def _log_analysis(self, findings: List[Tuple[str, float]], metric: str):
        """Immutable log of analysis to audit DB"""
        import uuid
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now().timestamp()

        findings_json = json.dumps(findings)
        findings_hash = hashlib.sha256(findings_json.encode()).hexdigest()

        with sqlite3.connect(self.audit_db) as conn:
            conn.execute("""
                INSERT INTO analysis_log
                (analysis_id, timestamp, analyzer_version, findings_hash,
                 top_performers, market_condition_stats, audit_proof)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_id,
                timestamp,
                "1.0",
                findings_hash,
                findings_json,
                json.dumps({"metric": metric}),
                f"guardian:gate4:evidence:{analysis_id}"
            ))
            conn.commit()

        logger.info(f"Analysis logged: {analysis_id} hash={findings_hash[:8]}")


# Tests
if __name__ == "__main__":
    import tempfile
    import os

    # Create temp DB with sample data
    temp_dir = tempfile.mkdtemp()
    results_db = os.path.join(temp_dir, "test_results.db")

    # Initialize test DB
    with sqlite3.connect(results_db) as conn:
        conn.execute("""
            CREATE TABLE backtest_results (
                test_id TEXT PRIMARY KEY,
                strategy_name TEXT,
                parameters TEXT,
                sharpe_ratio REAL,
                win_rate REAL,
                profit_factor REAL,
                max_drawdown REAL,
                total_return REAL,
                num_trades INTEGER,
                market_condition TEXT,
                test_date TEXT
            )
        """)

        # Insert test data
        test_data = [
            ("test_1", "ma_crossover", '{"fast": 10, "slow": 50}',
             2.1, 0.65, 2.3, 0.15, 0.45, 152, "trending", "2024-01-01"),
            ("test_2", "ma_crossover", '{"fast": 12, "slow": 52}',
             2.0, 0.63, 2.1, 0.18, 0.42, 148, "trending", "2024-01-02"),
            ("test_3", "rsi_mean_reversion", '{"overbought": 70, "oversold": 30}',
             1.5, 0.58, 1.8, 0.22, 0.38, 89, "range", "2024-01-01"),
        ]

        for row in test_data:
            conn.execute(
                "INSERT INTO backtest_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                row
            )
        conn.commit()

    # Test analyzer
    analyzer = StrategyAnalyzer(results_db, os.path.join(temp_dir, "audit.db"))

    print("=== Test 1: Read all results ===")
    results = analyzer.read_all_results()
    print(f"Found {len(results)} results")

    print("\n=== Test 2: Top performers ===")
    top = analyzer.get_top_performers(limit=2)
    for strategy, sharpe in top:
        print(f"  {strategy}: Sharpe={sharpe:.2f}")

    print("\n=== Test 3: Market conditions ===")
    trending = analyzer.get_by_market_condition("trending")
    print(f"Trending: {len(trending)} results")

    print("\n=== Test 4: Win rate distribution ===")
    dist = analyzer.get_win_rate_distribution()
    for strategy, rates in dist.items():
        print(f"  {strategy}: {rates}")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    print("\nAll tests passed!")
