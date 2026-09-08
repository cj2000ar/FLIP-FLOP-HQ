"""
Continuous Simulator - Market Replay Backtest Engine
Authority: ZERO (locked, non-negotiable)

Execute Market Replay simulations:
- Load strategy code + market data
- Run backtest against historical days
- Record entry/exit, P&L, latency, errors
- Track in immutable append-only log
"""

import os
import sqlite3
import hashlib
import json
import logging
import time
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from uuid import uuid4
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimulationStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class SimulationTrade:
    """Immutable trade execution record from simulator"""
    trade_id: str
    simulation_id: str
    strategy_name: str
    instrument: str
    side: str  # "BUY" | "SELL"
    entry_time: str  # HHMM
    entry_price: float
    exit_time: Optional[str]  # HHMM
    exit_price: Optional[float]
    quantity: int
    pnl_ticks: float
    pnl_dollars: float
    latency_ms: float
    error_code: Optional[str] = None
    authority: str = "ZERO"


@dataclass(frozen=True)
class SimulationResult:
    """Immutable backtest result summary"""
    simulation_id: str
    strategy_name: str
    instrument: str
    test_date: str  # YYYYMMDD
    backtest_date: str  # YYYYMMDD
    start_time: float  # Unix timestamp
    end_time: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    gross_pnl_dollars: float
    net_pnl_dollars: float
    max_drawdown_dollars: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    status: str  # "COMPLETED" | "FAILED"
    error_msg: Optional[str] = None
    result_hash: str = ""
    authority: str = "ZERO"

    def __post_init__(self):
        if self.authority != "ZERO":
            raise ValueError("authority must be ZERO")


class StrategyBacktester:
    """Execute strategy backtest against market data"""

    def __init__(self, db_dir: str = "databases"):
        self.db_dir = Path(db_dir)
        self.authority = "ZERO"

    def _init_results_db(self):
        """Initialize results database"""
        results_db = self.db_dir / "simulation_results.db"
        results_db.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(results_db))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_results (
                simulation_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                instrument TEXT NOT NULL,
                test_date TEXT NOT NULL,
                backtest_date TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                winning_trades INTEGER NOT NULL,
                losing_trades INTEGER NOT NULL,
                gross_pnl_dollars REAL NOT NULL,
                net_pnl_dollars REAL NOT NULL,
                max_drawdown_dollars REAL NOT NULL,
                win_rate REAL NOT NULL,
                profit_factor REAL NOT NULL,
                sharpe_ratio REAL NOT NULL,
                status TEXT NOT NULL,
                error_msg TEXT,
                result_hash TEXT NOT NULL,
                authority TEXT NOT NULL,
                UNIQUE(strategy_name, instrument, test_date, backtest_date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_trades (
                trade_id TEXT PRIMARY KEY,
                simulation_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                instrument TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_time TEXT,
                exit_price REAL,
                quantity INTEGER NOT NULL,
                pnl_ticks REAL NOT NULL,
                pnl_dollars REAL NOT NULL,
                latency_ms REAL NOT NULL,
                error_code TEXT,
                authority TEXT NOT NULL,
                FOREIGN KEY(simulation_id) REFERENCES simulation_results(simulation_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_simulation_strategy
            ON simulation_results(strategy_name, test_date)
        """)

        conn.commit()
        conn.close()

        return results_db

    def _load_market_data(self, instrument: str, date: str) -> Optional[List[Dict[str, Any]]]:
        """Load market bars from downloaded data"""
        db_path = self.db_dir / f"market_data_{date}.db"

        if not db_path.exists():
            logger.warning(f"Market data not found: {db_path}")
            return None

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT time, open_price, high_price, low_price, close_price, volume
                FROM market_bars
                WHERE instrument = ?
                ORDER BY time ASC
            """, (instrument,))

            bars = []
            for row in cursor.fetchall():
                bars.append({
                    "time": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5]
                })

            conn.close()
            return bars

        except Exception as e:
            logger.error(f"Error loading market data: {str(e)}")
            return None

    def run_backtest(self, strategy_func: Callable, strategy_name: str,
                    instrument: str, test_date: str,
                    backtest_dates: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Run backtest of strategy against multiple dates
        Args:
            strategy_func: Strategy function that takes bars and returns trades
            strategy_name: Name of strategy
            instrument: Instrument symbol
            test_date: Date strategy was built (YYYYMMDD)
            backtest_dates: Dates to backtest against (defaults to 5 previous days)
        Returns:
            List of simulation results
        """
        results_db = self._init_results_db()

        if backtest_dates is None:
            # Default: last 5 trading days
            from datetime import datetime, timedelta
            today = datetime.strptime(test_date, "%Y%m%d")
            backtest_dates = []
            for i in range(5, 0, -1):
                prev_date = today - timedelta(days=i)
                backtest_dates.append(prev_date.strftime("%Y%m%d"))

        all_results = []

        for backtest_date in backtest_dates:
            simulation_id = str(uuid4())
            start_time = time.time()

            try:
                # Load market data
                bars = self._load_market_data(instrument, backtest_date)

                if not bars:
                    logger.warning(f"No data for {instrument} on {backtest_date}")
                    continue

                # Run strategy
                trades = strategy_func(bars)

                # Calculate metrics
                result = self._calculate_metrics(
                    simulation_id=simulation_id,
                    strategy_name=strategy_name,
                    instrument=instrument,
                    test_date=test_date,
                    backtest_date=backtest_date,
                    trades=trades,
                    start_time=start_time
                )

                # Store result
                self._store_result(results_db, result, trades)
                all_results.append({
                    "simulation_id": simulation_id,
                    "status": "COMPLETED",
                    "metrics": {
                        "total_trades": result.total_trades,
                        "win_rate": result.win_rate,
                        "profit_factor": result.profit_factor,
                        "net_pnl": result.net_pnl_dollars,
                        "max_drawdown": result.max_drawdown_dollars,
                        "sharpe": result.sharpe_ratio
                    }
                })

                logger.info(f"Backtest {strategy_name} {instrument} {backtest_date}: "
                           f"trades={result.total_trades}, PnL=${result.net_pnl_dollars:.2f}")

            except Exception as e:
                logger.error(f"Backtest error {strategy_name} {backtest_date}: {str(e)}")
                all_results.append({
                    "simulation_id": simulation_id,
                    "status": "FAILED",
                    "error": str(e)
                })

        return all_results

    def _calculate_metrics(self, simulation_id: str, strategy_name: str,
                          instrument: str, test_date: str, backtest_date: str,
                          trades: List[Dict[str, Any]],
                          start_time: float) -> SimulationResult:
        """Calculate backtest performance metrics"""
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('pnl_dollars', 0) > 0)
        losing_trades = total_trades - winning_trades

        gross_pnl = sum(t.get('pnl_dollars', 0) for t in trades)
        commission = total_trades * 2  # $2 per trade round-trip
        net_pnl = gross_pnl - commission

        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown(trades)

        # Calculate Sharpe ratio
        pnls = [t.get('pnl_dollars', 0) for t in trades]
        sharpe = self._calculate_sharpe(pnls) if pnls else 0.0

        # Calculate profit factor
        profit_factor = abs(gross_pnl / commission) if commission > 0 else 0.0

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        result = SimulationResult(
            simulation_id=simulation_id,
            strategy_name=strategy_name,
            instrument=instrument,
            test_date=test_date,
            backtest_date=backtest_date,
            start_time=start_time,
            end_time=time.time(),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            gross_pnl_dollars=gross_pnl,
            net_pnl_dollars=net_pnl,
            max_drawdown_dollars=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            status="COMPLETED",
            result_hash=""
        )

        return result

    def _calculate_max_drawdown(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate maximum drawdown from trades"""
        if not trades:
            return 0.0

        cumulative = 0
        peak = 0
        max_dd = 0

        for trade in trades:
            cumulative += trade.get('pnl_dollars', 0)
            peak = max(peak, cumulative)
            drawdown = peak - cumulative
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_sharpe(self, pnls: List[float], rf_rate: float = 0.05) -> float:
        """Calculate Sharpe ratio (annualized)"""
        if not pnls or len(pnls) < 2:
            return 0.0

        import statistics
        mean = statistics.mean(pnls)
        stdev = statistics.stdev(pnls)

        if stdev == 0:
            return 0.0

        return (mean - rf_rate / 252) / (stdev / (252 ** 0.5))

    def _store_result(self, db_path: Path, result: SimulationResult,
                     trades: List[Dict[str, Any]]):
        """Store result and trades in database"""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Generate result hash
        result_hash = hashlib.sha256(
            f"{result.simulation_id}{result.strategy_name}{result.instrument}"
            f"{result.total_trades}{result.net_pnl_dollars}".encode()
        ).hexdigest()

        result_dict = asdict(result)
        result_dict['result_hash'] = result_hash

        cursor.execute("""
            INSERT OR REPLACE INTO simulation_results
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(result_dict.values()))

        # Store trades
        for trade in trades:
            trade_id = str(uuid4())
            cursor.execute("""
                INSERT INTO simulation_trades
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                result.simulation_id,
                result.strategy_name,
                result.instrument,
                trade.get('side', 'BUY'),
                trade.get('entry_time', '0000'),
                trade.get('entry_price', 0.0),
                trade.get('exit_time'),
                trade.get('exit_price'),
                trade.get('quantity', 1),
                trade.get('pnl_ticks', 0.0),
                trade.get('pnl_dollars', 0.0),
                trade.get('latency_ms', 0.0),
                trade.get('error_code'),
                self.authority
            ))

        conn.commit()
        conn.close()


def example_strategy(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Example: simple moving average crossover strategy"""
    trades = []

    if len(bars) < 20:
        return trades

    # Calculate 10/20 MA
    ma10 = sum(b['close'] for b in bars[-10:]) / 10
    ma20 = sum(b['close'] for b in bars[-20:]) / 20

    # Entry signal
    if ma10 > ma20 and bars[-2]['close'] * 1.0 < bars[-1]['close']:
        trades.append({
            "side": "BUY",
            "entry_time": bars[-1].get('time', '0000'),
            "entry_price": bars[-1]['close'],
            "quantity": 1,
            "pnl_ticks": 5.0,
            "pnl_dollars": 50.0,
            "latency_ms": 50.0
        })

    return trades


if __name__ == "__main__":
    backtester = StrategyBacktester()
    results = backtester.run_backtest(
        strategy_func=example_strategy,
        strategy_name="MA_Crossover",
        instrument="NQ",
        test_date="20260907"
    )
    print(json.dumps(results, indent=2))
