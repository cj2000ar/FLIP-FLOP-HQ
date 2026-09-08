"""
Canary Executor - Guardian Gate 5 (Canary Execution)
Runs small-scale test trades against replay data before full deployment.
Feeds results to Guardian for Gate 5 evaluation.

Authority: ZERO (LOCKED IMMUTABLE)
Date: 2026-09-07
"""

import json
import sqlite3
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from uuid import uuid4
from enum import Enum


class CanaryStatus(str, Enum):
    """Canary execution outcomes"""
    PASS = "PASS"
    HIGH_ERROR_RATE = "HIGH_ERROR_RATE"
    HIGH_LATENCY = "HIGH_LATENCY"
    CANARY_FAILED = "CANARY_FAILED"
    ROLLBACK_TRIGGERED = "ROLLBACK_TRIGGERED"


@dataclass(frozen=True)
class CanaryTrade:
    """Immutable canary test trade"""
    trade_id: str
    strategy_name: str
    instrument: str
    side: str  # BUY or SELL
    quantity: int
    entry_time: str  # ISO format
    exit_time: str
    entry_price: float
    exit_price: float
    pnl_dollars: float
    latency_ms: int  # Execution latency
    success: bool  # Trade executed without error
    error_msg: Optional[str] = None


@dataclass(frozen=True)
class CanaryResult:
    """Immutable canary execution result"""
    canary_id: str
    correlation_id: str
    strategy_name: str
    total_trades: int
    successful_trades: int
    failed_trades: int
    error_rate: float  # 0.0-1.0
    avg_latency_ms: int
    max_latency_ms: int
    pnl_dollars: float
    status: CanaryStatus
    triggered_rollback: bool
    event_time: str
    recorded_at: str


class CanaryExecutor:
    """Executes canary trades for Gate 5 evaluation"""

    ERROR_RATE_THRESHOLD = 0.05  # 5%
    LATENCY_THRESHOLD_MS = 200  # 200ms
    CANARY_TRADE_SIZE = 5  # Run 5 test trades

    def __init__(self, db_path: str = "databases/canary.db"):
        self.db_path = db_path
        self.authority = "ZERO"
        self.live_enabled = False
        self.broker_orders_allowed = False
        self._init_database()

    def _init_database(self):
        """Initialize canary execution database"""
        import os
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Canary executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canary_executions (
                canary_id TEXT PRIMARY KEY,
                correlation_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                total_trades INTEGER NOT NULL,
                successful_trades INTEGER NOT NULL,
                failed_trades INTEGER NOT NULL,
                error_rate REAL NOT NULL,
                avg_latency_ms INTEGER NOT NULL,
                max_latency_ms INTEGER NOT NULL,
                pnl_dollars REAL NOT NULL,
                status TEXT NOT NULL,
                triggered_rollback BOOLEAN NOT NULL,
                event_time TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_correlation_id
            ON canary_executions(correlation_id)
        """)

        # Canary trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canary_trades (
                trade_id TEXT PRIMARY KEY,
                canary_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                instrument TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                pnl_dollars REAL NOT NULL,
                latency_ms INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_msg TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (canary_id) REFERENCES canary_executions(canary_id)
            )
        """)

        conn.commit()
        conn.close()

    def run_canary(
        self,
        strategy_name: str,
        instrument: str,
        trades_data: List[Dict],
        correlation_id: str
    ) -> Tuple[CanaryStatus, CanaryResult]:
        """
        Execute canary trades from replay data.
        Returns (status, immutable_result).
        """
        canary_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        # Simulate canary trade execution
        canary_trades: List[CanaryTrade] = []
        successful = 0
        failed = 0
        total_latency = 0
        max_latency = 0
        total_pnl = 0.0

        # Run up to CANARY_TRADE_SIZE test trades
        test_trades = trades_data[:self.CANARY_TRADE_SIZE]

        for trade_data in test_trades:
            trade_id = str(uuid4())

            # Simulate execution (in real system, would actually execute)
            latency_ms = trade_data.get("latency_ms", 50)  # Assume 50ms base
            pnl = trade_data.get("pnl_dollars", 0.0)
            success = latency_ms < self.LATENCY_THRESHOLD_MS and pnl > -100  # Rough success metric

            if success:
                successful += 1
                total_pnl += pnl
            else:
                failed += 1

            total_latency += latency_ms
            max_latency = max(max_latency, latency_ms)

            canary_trades.append(CanaryTrade(
                trade_id=trade_id,
                strategy_name=strategy_name,
                instrument=instrument,
                side=trade_data.get("side", "BUY"),
                quantity=trade_data.get("quantity", 1),
                entry_time=trade_data.get("entry_time", now),
                exit_time=trade_data.get("exit_time", now),
                entry_price=trade_data.get("entry_price", 0.0),
                exit_price=trade_data.get("exit_price", 0.0),
                pnl_dollars=pnl,
                latency_ms=latency_ms,
                success=success,
                error_msg=None if success else "Execution latency exceeded threshold"
            ))

        # Calculate metrics
        total_trades = len(canary_trades)
        error_rate = failed / total_trades if total_trades > 0 else 0.0
        avg_latency_ms = int(total_latency / total_trades) if total_trades > 0 else 0

        # Determine status (check latency first, then error rate, then failures)
        status = CanaryStatus.PASS
        rollback_triggered = False

        if avg_latency_ms > self.LATENCY_THRESHOLD_MS:
            status = CanaryStatus.HIGH_LATENCY
            rollback_triggered = True
        elif error_rate > self.ERROR_RATE_THRESHOLD:
            status = CanaryStatus.HIGH_ERROR_RATE
            rollback_triggered = True
        elif failed > 0:
            status = CanaryStatus.CANARY_FAILED
            rollback_triggered = True

        # Create immutable result
        result = CanaryResult(
            canary_id=canary_id,
            correlation_id=correlation_id,
            strategy_name=strategy_name,
            total_trades=total_trades,
            successful_trades=successful,
            failed_trades=failed,
            error_rate=error_rate,
            avg_latency_ms=avg_latency_ms,
            max_latency_ms=max_latency,
            pnl_dollars=total_pnl,
            status=status,
            triggered_rollback=rollback_triggered,
            event_time=now,
            recorded_at=now
        )

        # Log to database
        self._log_canary(result, canary_trades)

        return status, result

    def _log_canary(self, result: CanaryResult, trades: List[CanaryTrade]):
        """Log immutable canary execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        payload = {
            "canary_id": result.canary_id,
            "correlation_id": result.correlation_id,
            "strategy_name": result.strategy_name,
            "total_trades": result.total_trades,
            "successful_trades": result.successful_trades,
            "failed_trades": result.failed_trades,
            "error_rate": result.error_rate,
            "avg_latency_ms": result.avg_latency_ms,
            "max_latency_ms": result.max_latency_ms,
            "pnl_dollars": result.pnl_dollars,
            "status": result.status.value,
            "triggered_rollback": result.triggered_rollback,
        }

        cursor.execute("""
            INSERT INTO canary_executions
            (canary_id, correlation_id, strategy_name, total_trades, successful_trades,
             failed_trades, error_rate, avg_latency_ms, max_latency_ms, pnl_dollars,
             status, triggered_rollback, event_time, recorded_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.canary_id,
            result.correlation_id,
            result.strategy_name,
            result.total_trades,
            result.successful_trades,
            result.failed_trades,
            result.error_rate,
            result.avg_latency_ms,
            result.max_latency_ms,
            result.pnl_dollars,
            result.status.value,
            result.triggered_rollback,
            result.event_time,
            result.recorded_at,
            json.dumps(payload)
        ))

        # Log individual trades
        for trade in trades:
            cursor.execute("""
                INSERT INTO canary_trades
                (trade_id, canary_id, strategy_name, instrument, side, quantity,
                 entry_time, exit_time, entry_price, exit_price, pnl_dollars,
                 latency_ms, success, error_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.trade_id,
                result.canary_id,
                trade.strategy_name,
                trade.instrument,
                trade.side,
                trade.quantity,
                trade.entry_time,
                trade.exit_time,
                trade.entry_price,
                trade.exit_price,
                trade.pnl_dollars,
                trade.latency_ms,
                trade.success,
                trade.error_msg
            ))

        conn.commit()
        conn.close()

    def get_canary_result(self, canary_id: str) -> Optional[Dict]:
        """Retrieve canary execution result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT payload_json FROM canary_executions
            WHERE canary_id = ?
        """, (canary_id,))

        row = cursor.fetchone()
        conn.close()

        return json.loads(row[0]) if row else None

    def get_canary_trades(self, canary_id: str) -> List[Dict]:
        """Retrieve all trades from canary execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT trade_id, strategy_name, instrument, side, quantity,
                   entry_time, exit_time, entry_price, exit_price, pnl_dollars,
                   latency_ms, success, error_msg
            FROM canary_trades
            WHERE canary_id = ?
            ORDER BY entry_time ASC
        """, (canary_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "trade_id": row[0],
                "strategy_name": row[1],
                "instrument": row[2],
                "side": row[3],
                "quantity": row[4],
                "entry_time": row[5],
                "exit_time": row[6],
                "entry_price": row[7],
                "exit_price": row[8],
                "pnl_dollars": row[9],
                "latency_ms": row[10],
                "success": bool(row[11]),
                "error_msg": row[12],
            }
            for row in rows
        ]
