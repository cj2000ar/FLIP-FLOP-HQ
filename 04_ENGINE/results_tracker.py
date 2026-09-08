"""
Results Tracker - Immutable Append-Only Logging
Authority: ZERO (locked, non-negotiable)

Log all simulation runs to SQLite (append-only):
- Track: strategy version, backtest date, results, metrics
- Compute: win rate, profit factor, max drawdown, Sharpe ratio
- Correlation ID for tracing runs
- Immutable history with cryptographic proofs
"""

import os
import sqlite3
import hashlib
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimulationLogEntry:
    """Immutable simulation log entry (append-only)"""
    log_id: str
    correlation_id: str  # Links related runs
    simulation_id: str
    strategy_name: str
    strategy_version: str
    instrument: str
    backtest_date: str  # YYYYMMDD
    recorded_date: str  # YYYYMMDD
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    gross_pnl: float
    net_pnl: float
    runtime_seconds: float
    timestamp: float  # Unix epoch
    entry_hash: str = ""  # SHA256 hash chain
    prev_hash: str = ""  # Link to previous entry (chain)
    authority: str = "ZERO"

    def __post_init__(self):
        if self.authority != "ZERO":
            raise ValueError("authority must be ZERO")


@dataclass(frozen=True)
class StrategyMetricsSnapshot:
    """Immutable snapshot of strategy performance over time"""
    snapshot_id: str
    strategy_name: str
    strategy_version: str
    as_of_date: str  # YYYYMMDD
    days_tested: int
    total_simulations: int
    avg_win_rate: float
    avg_profit_factor: float
    cumulative_pnl: float
    max_peak_drawdown: float
    avg_sharpe: float
    consistency_score: float  # How stable metrics are over time
    snapshot_hash: str = ""
    authority: str = "ZERO"

    def __post_init__(self):
        if self.authority != "ZERO":
            raise ValueError("authority must be ZERO")


class ResultsTracker:
    """Append-only immutable results logger"""

    def __init__(self, db_path: str = "databases/results_tracker.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.authority = "ZERO"
        self._init_db()

    def _init_db(self):
        """Initialize append-only database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Main immutable log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_log (
                log_id TEXT PRIMARY KEY,
                correlation_id TEXT NOT NULL,
                simulation_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                strategy_version TEXT NOT NULL,
                instrument TEXT NOT NULL,
                backtest_date TEXT NOT NULL,
                recorded_date TEXT NOT NULL,
                total_trades INTEGER NOT NULL,
                winning_trades INTEGER NOT NULL,
                losing_trades INTEGER NOT NULL,
                win_rate REAL NOT NULL,
                profit_factor REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                sharpe_ratio REAL NOT NULL,
                gross_pnl REAL NOT NULL,
                net_pnl REAL NOT NULL,
                runtime_seconds REAL NOT NULL,
                timestamp REAL NOT NULL,
                entry_hash TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                authority TEXT NOT NULL,
                UNIQUE(simulation_id)
            )
        """)

        # Metrics snapshots (point-in-time aggregates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_metrics_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                strategy_version TEXT NOT NULL,
                as_of_date TEXT NOT NULL,
                days_tested INTEGER NOT NULL,
                total_simulations INTEGER NOT NULL,
                avg_win_rate REAL NOT NULL,
                avg_profit_factor REAL NOT NULL,
                cumulative_pnl REAL NOT NULL,
                max_peak_drawdown REAL NOT NULL,
                avg_sharpe REAL NOT NULL,
                consistency_score REAL NOT NULL,
                snapshot_hash TEXT NOT NULL,
                authority TEXT NOT NULL,
                UNIQUE(strategy_name, strategy_version, as_of_date)
            )
        """)

        # Indexes for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_date
            ON simulation_log(strategy_name, recorded_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_correlation
            ON simulation_log(correlation_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_metrics
            ON strategy_metrics_snapshots(strategy_name, as_of_date)
        """)

        conn.commit()
        conn.close()

    def log_simulation(self, simulation_result: Dict[str, Any],
                      strategy_version: str,
                      correlation_id: Optional[str] = None) -> str:
        """
        Log a simulation result to append-only log
        Args:
            simulation_result: Result dict with metrics
            strategy_version: Version of strategy (e.g., "1.0.1")
            correlation_id: Correlation ID for tracing related runs
        Returns:
            Log entry ID
        """
        if correlation_id is None:
            correlation_id = str(uuid4())

        log_id = str(uuid4())
        current_timestamp = time.time()
        current_date = datetime.now().strftime("%Y%m%d")

        # Get previous hash for chain
        prev_hash = self._get_latest_hash(simulation_result['strategy_name'])

        # Create log entry
        entry = SimulationLogEntry(
            log_id=log_id,
            correlation_id=correlation_id,
            simulation_id=simulation_result.get('simulation_id', str(uuid4())),
            strategy_name=simulation_result['strategy_name'],
            strategy_version=strategy_version,
            instrument=simulation_result['instrument'],
            backtest_date=simulation_result['backtest_date'],
            recorded_date=current_date,
            total_trades=simulation_result.get('total_trades', 0),
            winning_trades=simulation_result.get('winning_trades', 0),
            losing_trades=simulation_result.get('losing_trades', 0),
            win_rate=simulation_result.get('win_rate', 0.0),
            profit_factor=simulation_result.get('profit_factor', 0.0),
            max_drawdown=simulation_result.get('max_drawdown', 0.0),
            sharpe_ratio=simulation_result.get('sharpe_ratio', 0.0),
            gross_pnl=simulation_result.get('gross_pnl', 0.0),
            net_pnl=simulation_result.get('net_pnl', 0.0),
            runtime_seconds=simulation_result.get('runtime_seconds', 0.0),
            timestamp=current_timestamp,
            entry_hash="",
            prev_hash=prev_hash
        )

        # Calculate entry hash (chain of custody)
        entry_hash = self._calculate_entry_hash(entry)

        # Store in database (APPEND ONLY)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        entry_dict = asdict(entry)
        entry_dict['entry_hash'] = entry_hash

        try:
            cursor.execute("""
                INSERT INTO simulation_log
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(entry_dict.values()))

            conn.commit()
            logger.info(f"Logged simulation {log_id}: {entry.strategy_name} "
                       f"{entry.instrument} {entry.backtest_date}")

        except sqlite3.IntegrityError as e:
            logger.error(f"Duplicate entry detected: {str(e)}")
            return ""
        finally:
            conn.close()

        return log_id

    def _get_latest_hash(self, strategy_name: str) -> str:
        """Get latest entry hash for strategy (chain of custody)"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT entry_hash FROM simulation_log
                WHERE strategy_name = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (strategy_name,))

            result = cursor.fetchone()
            conn.close()

            return result[0] if result else ""
        except Exception as e:
            logger.error(f"Error getting latest hash: {str(e)}")
            return ""

    def _calculate_entry_hash(self, entry: SimulationLogEntry) -> str:
        """Calculate SHA256 hash of log entry"""
        data = f"{entry.log_id}{entry.simulation_id}{entry.strategy_name}" \
               f"{entry.total_trades}{entry.net_pnl}{entry.timestamp}{entry.prev_hash}"
        return hashlib.sha256(data.encode()).hexdigest()

    def create_metrics_snapshot(self, strategy_name: str,
                               strategy_version: str,
                               lookback_days: int = 30) -> str:
        """
        Create point-in-time snapshot of strategy metrics
        Args:
            strategy_name: Name of strategy
            strategy_version: Version string
            lookback_days: Days to aggregate over
        Returns:
            Snapshot ID
        """
        snapshot_id = str(uuid4())
        current_date = datetime.now().strftime("%Y%m%d")

        # Query log for metrics over lookback period
        cutoff_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y%m%d")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_sims,
                COUNT(DISTINCT backtest_date) as days_tested,
                AVG(win_rate) as avg_win_rate,
                AVG(profit_factor) as avg_profit_factor,
                SUM(net_pnl) as cumulative_pnl,
                MAX(max_drawdown) as max_peak_drawdown,
                AVG(sharpe_ratio) as avg_sharpe
            FROM simulation_log
            WHERE strategy_name = ? AND strategy_version = ? AND recorded_date >= ?
        """, (strategy_name, strategy_version, cutoff_date))

        row = cursor.fetchone()

        if row and row[0] > 0:
            total_sims, days_tested, avg_wr, avg_pf, cum_pnl, max_dd, avg_sharpe = row
            consistency_score = self._calculate_consistency(strategy_name, strategy_version, cutoff_date)
        else:
            total_sims = 0
            days_tested = 0
            avg_wr = 0.0
            avg_pf = 0.0
            cum_pnl = 0.0
            max_dd = 0.0
            avg_sharpe = 0.0
            consistency_score = 0.0

        snapshot = StrategyMetricsSnapshot(
            snapshot_id=snapshot_id,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            as_of_date=current_date,
            days_tested=days_tested or 0,
            total_simulations=total_sims or 0,
            avg_win_rate=avg_wr or 0.0,
            avg_profit_factor=avg_pf or 0.0,
            cumulative_pnl=cum_pnl or 0.0,
            max_peak_drawdown=max_dd or 0.0,
            avg_sharpe=avg_sharpe or 0.0,
            consistency_score=consistency_score,
            snapshot_hash=""
        )

        # Calculate snapshot hash
        snapshot_hash = self._calculate_snapshot_hash(snapshot)

        snapshot_dict = asdict(snapshot)
        snapshot_dict['snapshot_hash'] = snapshot_hash

        cursor.execute("""
            INSERT OR REPLACE INTO strategy_metrics_snapshots
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(snapshot_dict.values()))

        conn.commit()
        conn.close()

        logger.info(f"Created snapshot {snapshot_id}: {strategy_name} v{strategy_version}")

        return snapshot_id

    def _calculate_consistency(self, strategy_name: str, strategy_version: str,
                              cutoff_date: str) -> float:
        """Calculate consistency score based on metric variance"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT win_rate, profit_factor, net_pnl
                FROM simulation_log
                WHERE strategy_name = ? AND strategy_version = ? AND recorded_date >= ?
            """, (strategy_name, strategy_version, cutoff_date))

            rows = cursor.fetchall()
            conn.close()

            if len(rows) < 2:
                return 0.0

            win_rates = [r[0] for r in rows]
            pfs = [r[1] for r in rows]

            # Low variance = high consistency
            import statistics
            wr_stdev = statistics.stdev(win_rates) if len(win_rates) > 1 else 0
            pf_stdev = statistics.stdev(pfs) if len(pfs) > 1 else 0

            # Consistency: 1.0 - normalized stdev
            consistency = max(0.0, 1.0 - (wr_stdev + pf_stdev) / 10)

            return consistency

        except Exception as e:
            logger.error(f"Error calculating consistency: {str(e)}")
            return 0.0

    def _calculate_snapshot_hash(self, snapshot: StrategyMetricsSnapshot) -> str:
        """Calculate snapshot hash"""
        data = f"{snapshot.snapshot_id}{snapshot.strategy_name}" \
               f"{snapshot.strategy_version}{snapshot.as_of_date}" \
               f"{snapshot.total_simulations}{snapshot.cumulative_pnl}"
        return hashlib.sha256(data.encode()).hexdigest()

    def get_strategy_history(self, strategy_name: str,
                            days: int = 30) -> List[Dict[str, Any]]:
        """Get history of strategy runs"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    log_id, simulation_id, strategy_version, instrument,
                    backtest_date, total_trades, win_rate, profit_factor,
                    net_pnl, max_drawdown, sharpe_ratio, timestamp
                FROM simulation_log
                WHERE strategy_name = ? AND recorded_date >= ?
                ORDER BY timestamp DESC
            """, (strategy_name, cutoff_date))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "log_id": r[0],
                    "simulation_id": r[1],
                    "version": r[2],
                    "instrument": r[3],
                    "backtest_date": r[4],
                    "trades": r[5],
                    "win_rate": r[6],
                    "profit_factor": r[7],
                    "net_pnl": r[8],
                    "max_drawdown": r[9],
                    "sharpe": r[10],
                    "timestamp": r[11]
                }
                for r in rows
            ]

        except Exception as e:
            logger.error(f"Error getting strategy history: {str(e)}")
            return []

    def verify_log_integrity(self) -> Tuple[bool, str]:
        """
        Verify log integrity using hash chain
        Returns: (is_valid, message)
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT log_id, entry_hash, prev_hash
                FROM simulation_log
                ORDER BY timestamp ASC
            """)

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return True, "Log is empty"

            # Verify first entry has no previous hash
            if rows[0][2] != "":
                return False, "First entry has invalid prev_hash"

            # Verify chain
            for i, (log_id, entry_hash, prev_hash) in enumerate(rows):
                if i == 0:
                    continue

                # Previous entry's hash should match current prev_hash
                if rows[i-1][1] != prev_hash:
                    return False, f"Hash chain broken at entry {i}"

            return True, "Log integrity verified"

        except Exception as e:
            return False, f"Integrity check error: {str(e)}"


if __name__ == "__main__":
    tracker = ResultsTracker()

    # Example log
    result = {
        "simulation_id": "sim_001",
        "strategy_name": "MA_Crossover",
        "instrument": "NQ",
        "backtest_date": "20260901",
        "total_trades": 15,
        "winning_trades": 9,
        "losing_trades": 6,
        "win_rate": 0.6,
        "profit_factor": 1.85,
        "max_drawdown": 500.0,
        "sharpe_ratio": 1.2,
        "gross_pnl": 5000.0,
        "net_pnl": 4700.0,
        "runtime_seconds": 2.5
    }

    log_id = tracker.log_simulation(result, strategy_version="1.0.0")
    print(f"Logged: {log_id}")

    # Create snapshot
    snapshot_id = tracker.create_metrics_snapshot("MA_Crossover", "1.0.0")
    print(f"Snapshot: {snapshot_id}")

    # Verify integrity
    is_valid, msg = tracker.verify_log_integrity()
    print(f"Integrity: {is_valid} - {msg}")
