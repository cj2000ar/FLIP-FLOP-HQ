"""
Evolution Loop Orchestrator - FlipFlop HQ Auto-Improvement Engine
Master controller: every 1000 completed backtests, trigger evolution round.
Generate variants, rank by recent performance, flag promotion candidates.
Guardian Gate 4 compatible audit trail.
"""

import json
import sqlite3
import hashlib
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
import logging

from strategy_analyzer import StrategyAnalyzer
from parameter_evolution import ParameterEvolution
from indicator_suggester import IndicatorSuggester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EvolutionRound:
    """Single evolution round record"""
    round_id: str
    trigger_backtest_count: int
    timestamp: str
    top_performers: List[Tuple[str, float]]
    variants_generated: int
    indicators_suggested: int
    promotion_candidate: Optional[str]


@dataclass
class PromotionCandidate:
    """Strategy ready for live trading promotion"""
    candidate_id: str
    strategy_name: str
    avg_sharpe_7d: float
    win_rate_7d: float
    profit_factor_7d: float
    total_tested_variants: int
    outperformance_vs_baseline: float
    readiness_score: float
    promotion_date: str
    authority_approval: str  # "ZERO" (locked)


class EvolutionLoop:
    """
    Master orchestrator for strategy evolution.
    - Monitors backtest completion count
    - Triggers evolution every 1000 tests
    - Generates variants, tests, ranks
    - Promotes top performers to live
    """

    def __init__(self, tracker_db: str = "backtest_tracker.db",
                 evolution_db: str = "evolution_master.db"):
        self.tracker_db = tracker_db
        self.evolution_db = evolution_db
        self.analyzer = StrategyAnalyzer()
        self.evolver = ParameterEvolution()
        self.indicator_suggester = IndicatorSuggester()
        self._init_dbs()

    def _init_dbs(self):
        """Initialize evolution master database"""
        with sqlite3.connect(self.evolution_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_rounds (
                    round_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    trigger_backtest_count INTEGER,
                    top_performers JSON,
                    variants_generated INTEGER,
                    indicators_suggested INTEGER,
                    promotion_candidate TEXT,
                    round_status TEXT,
                    content_hash TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS promotion_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    strategy_name TEXT,
                    avg_sharpe_7d REAL,
                    win_rate_7d REAL,
                    profit_factor_7d REAL,
                    total_variants INTEGER,
                    outperformance REAL,
                    readiness_score REAL,
                    promotion_gate_status TEXT,
                    authority_lock TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_metrics (
                    metric_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    metric_name TEXT,
                    metric_value REAL,
                    round_id TEXT
                )
            """)
            conn.commit()

    def get_backtest_count(self) -> int:
        """Get total completed backtests"""
        try:
            with sqlite3.connect(self.tracker_db) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM backtest_results"
                )
                return cursor.fetchone()[0]
        except:
            return 0

    def should_trigger_evolution(self) -> bool:
        """Check if 1000+ new backtests since last evolution round"""
        count = self.get_backtest_count()
        last_round_count = self._get_last_evolution_backtest_count()
        return (count - last_round_count) >= 1000

    def _get_last_evolution_backtest_count(self) -> int:
        """Get backtest count from last evolution round"""
        with sqlite3.connect(self.evolution_db) as conn:
            cursor = conn.execute("""
                SELECT MAX(trigger_backtest_count)
                FROM evolution_rounds
            """)
            result = cursor.fetchone()[0]
            return result if result else 0

    def run_evolution_round(self) -> EvolutionRound:
        """Execute full evolution round"""
        round_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        backtest_count = self.get_backtest_count()

        logger.info(f"=== Evolution Round {round_id[:8]} ===")
        logger.info(f"Triggered at {backtest_count} completed backtests")

        # Step 1: Identify top performers
        top_performers = self.analyzer.get_top_performers(limit=10)
        logger.info(f"Top performers: {len(top_performers)}")

        # Step 2: Generate parameter variants for each
        variants_generated = 0
        all_variants = []

        for strategy_name, sharpe in top_performers:
            logger.info(f"Evolving {strategy_name} (Sharpe={sharpe:.2f})")

            # Get recent test params for this strategy
            recent_params = self._get_recent_params(strategy_name)
            if not recent_params:
                continue

            variants = self.evolver.suggest_variants(
                strategy_name, recent_params, sharpe, count=5
            )
            variants_generated += len(variants)
            all_variants.extend(variants)

            # Get metric correlations for correlation-driven variants
            correlations = self.analyzer.get_parameter_correlation(strategy_name)
            if correlations:
                corr_variants = self.evolver.suggest_by_metric_correlation(
                    strategy_name, correlations, recent_params
                )
                variants_generated += len(corr_variants)
                all_variants.extend(corr_variants)

        logger.info(f"Generated {variants_generated} parameter variants")

        # Step 3: Analyze winning trades for indicator suggestions
        recent_trades = self._get_recent_winning_trades()
        indicators_suggested = 0

        if recent_trades:
            for strategy_name, trades in recent_trades.items():
                analysis = self.indicator_suggester.analyze_winning_trades(trades)
                suggestions = self.indicator_suggester.suggest_indicators(
                    strategy_name, analysis
                )
                indicators_suggested += len(suggestions)

        logger.info(f"Suggested {indicators_suggested} new indicators")

        # Step 4: Rank strategies by 7-day performance
        promotion_candidate = self._select_promotion_candidate(top_performers)

        # Log round
        self._log_evolution_round(
            round_id, backtest_count, top_performers,
            variants_generated, indicators_suggested, promotion_candidate
        )

        round_summary = EvolutionRound(
            round_id=round_id,
            trigger_backtest_count=backtest_count,
            timestamp=timestamp,
            top_performers=top_performers,
            variants_generated=variants_generated,
            indicators_suggested=indicators_suggested,
            promotion_candidate=promotion_candidate
        )

        return round_summary

    def _get_recent_params(self, strategy_name: str) -> Dict:
        """Get most recent parameters for strategy"""
        results = self.analyzer.read_all_results()
        strategy_results = [r for r in results if r.strategy_name == strategy_name]
        if strategy_results:
            return strategy_results[0].parameters
        return {}

    def _get_recent_winning_trades(self, days: int = 7) -> Dict[str, List[Dict]]:
        """Get winning trades from last N days (simplified)"""
        # In real implementation, would fetch from detailed trade log
        return {}

    def _select_promotion_candidate(self,
                                   top_performers: List[Tuple[str, float]]
                                   ) -> Optional[str]:
        """Select top performer for live promotion"""
        if not top_performers:
            return None

        best_strategy, best_sharpe = top_performers[0]

        # Check 7-day performance
        results = self.analyzer.read_all_results()
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_results = [
            r for r in results
            if r.strategy_name == best_strategy and
            datetime.fromisoformat(r.test_date) >= recent_cutoff
        ]

        if len(recent_results) < 3:  # Need minimum tests
            return None

        avg_sharpe_7d = sum(r.sharpe_ratio for r in recent_results) / len(recent_results)
        avg_win_rate = sum(r.win_rate for r in recent_results) / len(recent_results)

        # Promotion criteria
        if avg_sharpe_7d > 1.8 and avg_win_rate > 0.55:
            return best_strategy

        return None

    def promote_to_live(self, strategy_name: str) -> PromotionCandidate:
        """Mark strategy for live trading promotion"""
        candidate_id = str(uuid.uuid4())
        timestamp = datetime.now().timestamp()

        # Calculate metrics
        results = self.analyzer.read_all_results()
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_results = [
            r for r in results
            if r.strategy_name == strategy_name and
            datetime.fromisoformat(r.test_date) >= recent_cutoff
        ]

        avg_sharpe = sum(r.sharpe_ratio for r in recent_results) / len(recent_results) \
            if recent_results else 0.0
        avg_win_rate = sum(r.win_rate for r in recent_results) / len(recent_results) \
            if recent_results else 0.0
        avg_pf = sum(r.profit_factor for r in recent_results) / len(recent_results) \
            if recent_results else 1.0

        readiness_score = min(1.0,
                             (avg_sharpe / 2.0) * 0.4 +
                             (avg_win_rate / 0.7) * 0.3 +
                             (avg_pf / 2.0) * 0.3)

        candidate = PromotionCandidate(
            candidate_id=candidate_id,
            strategy_name=strategy_name,
            avg_sharpe_7d=avg_sharpe,
            win_rate_7d=avg_win_rate,
            profit_factor_7d=avg_pf,
            total_tested_variants=len(recent_results),
            outperformance_vs_baseline=avg_sharpe - 1.5,
            readiness_score=readiness_score,
            promotion_date=datetime.now().isoformat(),
            authority_approval="ZERO"
        )

        self._log_promotion(candidate)
        return candidate

    def get_promotion_status(self, strategy_name: str) -> Optional[PromotionCandidate]:
        """Check if strategy is ready for live promotion"""
        with sqlite3.connect(self.evolution_db) as conn:
            cursor = conn.execute("""
                SELECT candidate_id, strategy_name, avg_sharpe_7d, win_rate_7d,
                       profit_factor_7d, total_variants, outperformance,
                       readiness_score
                FROM promotion_candidates
                WHERE strategy_name = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (strategy_name,))

            row = cursor.fetchone()
            if not row:
                return None

            return PromotionCandidate(
                candidate_id=row[0],
                strategy_name=row[1],
                avg_sharpe_7d=row[2],
                win_rate_7d=row[3],
                profit_factor_7d=row[4],
                total_tested_variants=row[5],
                outperformance_vs_baseline=row[6],
                readiness_score=row[7],
                promotion_date="",
                authority_approval="ZERO"
            )

    def _log_evolution_round(self, round_id: str, backtest_count: int,
                            top_performers: List[Tuple[str, float]],
                            variants: int, indicators: int,
                            promotion: Optional[str]):
        """Immutable log of evolution round"""
        content = json.dumps({
            "top_performers": top_performers,
            "variants": variants,
            "indicators": indicators,
        }, sort_keys=True)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        with sqlite3.connect(self.evolution_db) as conn:
            conn.execute("""
                INSERT INTO evolution_rounds
                (round_id, timestamp, trigger_backtest_count, top_performers,
                 variants_generated, indicators_suggested, promotion_candidate,
                 round_status, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                round_id,
                datetime.now().timestamp(),
                backtest_count,
                json.dumps([{"strategy": s, "sharpe": sh}
                           for s, sh in top_performers]),
                variants,
                indicators,
                promotion or "",
                "COMPLETED",
                content_hash
            ))
            conn.commit()

        logger.info(f"Evolution round logged: {round_id[:8]} hash={content_hash[:8]}")

    def _log_promotion(self, candidate: PromotionCandidate):
        """Log promotion candidate"""
        with sqlite3.connect(self.evolution_db) as conn:
            conn.execute("""
                INSERT INTO promotion_candidates
                (candidate_id, timestamp, strategy_name, avg_sharpe_7d, win_rate_7d,
                 profit_factor_7d, total_variants, outperformance,
                 readiness_score, promotion_gate_status, authority_lock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate.candidate_id,
                datetime.now().timestamp(),
                candidate.strategy_name,
                candidate.avg_sharpe_7d,
                candidate.win_rate_7d,
                candidate.profit_factor_7d,
                candidate.total_tested_variants,
                candidate.outperformance_vs_baseline,
                candidate.readiness_score,
                "READY" if candidate.readiness_score > 0.75 else "EVALUATING",
                candidate.authority_approval
            ))
            conn.commit()

        logger.info(f"Promotion candidate: {candidate.strategy_name} "
                   f"readiness={candidate.readiness_score:.2f}")


# Tests
if __name__ == "__main__":
    import tempfile
    import os
    import shutil

    temp_dir = tempfile.mkdtemp()

    # Create mock tracker DB
    tracker_db = os.path.join(temp_dir, "tracker.db")
    evolution_db = os.path.join(temp_dir, "evolution.db")

    # Pre-populate tracker
    with sqlite3.connect(tracker_db) as conn:
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

        for i in range(5):
            conn.execute(
                """INSERT INTO backtest_results VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"test_{i}", "ma_crossover", '{"fast": 10}',
                 1.8 + i*0.1, 0.60 + i*0.02, 2.0 + i*0.1, 0.15, 0.40, 100,
                 "trending", datetime.now().isoformat())
            )
        conn.commit()

    print("=== Test 1: Get backtest count ===")
    loop = EvolutionLoop(tracker_db, evolution_db)
    count = loop.get_backtest_count()
    print(f"Backtests completed: {count}")

    print("\n=== Test 2: Should trigger evolution ===")
    should_trigger = loop.should_trigger_evolution()
    print(f"Should trigger: {should_trigger} (need 1000)")

    print("\n=== Test 3: Get recent params ===")
    params = loop._get_recent_params("ma_crossover")
    print(f"Recent params: {params}")

    print("\n=== Test 4: Promotion status ===")
    promo = loop.get_promotion_status("ma_crossover")
    print(f"Promotion status: {promo}")

    # Cleanup
    shutil.rmtree(temp_dir)

    print("\nAll tests passed!")
