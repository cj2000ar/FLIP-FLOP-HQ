"""
NinjaTrader Bridge - Market Replay Data Ingestion
Authority: ZERO (LOCKED IMMUTABLE)
Live: OFF (Playback/Paper only)
Broker Orders: NONE

Ingest trade events from NinjaTrader Market Replay:
- Entry/exit timestamps
- Fills + slippage
- P&L tracking
- Evidence capture (hashes, passports)
- Guardian integration for approval
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import UUID, uuid4
from pathlib import Path

# ============================================================================
# ENUMS
# ============================================================================

class TradeStatus(str, Enum):
    ENTRY_PENDING = "ENTRY_PENDING"
    FILLED = "FILLED"
    EXIT_PENDING = "EXIT_PENDING"
    CLOSED = "CLOSED"
    STOPPED_OUT = "STOPPED_OUT"
    TARGET_HIT = "TARGET_HIT"

class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class ReplayStatus(str, Enum):
    LOADING = "LOADING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

# ============================================================================
# IMMUTABLE DATA STRUCTURES
# ============================================================================

@dataclass(frozen=True)
class TradeEvent:
    """Immutable trade event from NinjaTrader Market Replay"""
    event_id: UUID
    replay_session_id: UUID
    strategy_name: str
    instrument: str  # NQ, ES, etc
    side: TradeSide
    entry_time: datetime
    entry_price: float
    entry_quantity: int
    stop_price: float
    target_price: float
    exit_time: Optional[datetime]
    exit_price: Optional[float]
    status: TradeStatus
    pnl_ticks: Optional[int]  # Profit/loss in ticks
    pnl_dollars: Optional[float]  # P&L in dollars
    cost_per_side: float  # Execution cost
    slippage_ticks: float  # Actual vs expected entry
    recorded_at: datetime
    observation_hash: str  # SHA256 of entry data
    authority: str = "ZERO"
    broker_orders_allowed: bool = False
    live_enabled: bool = False

    def __post_init__(self):
        """Validate immutable constraints"""
        if self.authority != "ZERO":
            raise ValueError("authority must be ZERO")
        if self.broker_orders_allowed:
            raise ValueError("broker_orders_allowed must be False")
        if self.live_enabled:
            raise ValueError("live_enabled must be False")
        if self.entry_time and self.exit_time:
            if self.entry_time > self.exit_time:
                raise ValueError("entry_time must be <= exit_time")

@dataclass(frozen=True)
class ReplaySession:
    """Immutable Market Replay session configuration"""
    session_id: UUID
    strategy_name: str
    instrument: str
    market_date: str  # YYYYMMDD
    replay_speed: int  # 1=real-time, 2=2x, etc
    start_time: str  # HH:MM ET
    end_time: str  # HH:MM ET
    data_source: str  # "NINJATRADER_PLAYBACK"
    created_at: datetime
    authority: str = "ZERO"
    live_enabled: bool = False

    def __post_init__(self):
        """Validate constraints"""
        if self.authority != "ZERO":
            raise ValueError("authority must be ZERO")
        if self.live_enabled:
            raise ValueError("live_enabled must be False")

@dataclass
class ReplayMetrics:
    """Running metrics for replay session"""
    session_id: UUID
    strategy_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    gross_pnl_ticks: int = 0
    gross_pnl_dollars: float = 0.0
    net_pnl_dollars: float = 0.0
    max_drawdown_dollars: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_pnl_per_trade: float = 0.0
    trades: List[TradeEvent] = field(default_factory=list)

    def add_trade(self, trade: TradeEvent):
        """Add trade and recalculate metrics"""
        self.trades.append(trade)
        self.total_trades += 1

        if trade.pnl_dollars:
            self.gross_pnl_dollars += trade.pnl_dollars
            self.net_pnl_dollars = self.gross_pnl_dollars - (self.total_trades * trade.cost_per_side * 2)

            if trade.pnl_dollars > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1

        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades
            self.avg_pnl_per_trade = self.net_pnl_dollars / self.total_trades

        # Recalculate drawdown
        cumulative = 0
        max_cumulative = 0
        for t in self.trades:
            if t.pnl_dollars:
                cumulative += t.pnl_dollars
                if cumulative < max_cumulative:
                    self.max_drawdown_dollars = min(self.max_drawdown_dollars, max_cumulative - cumulative)
                max_cumulative = max(max_cumulative, cumulative)

# ============================================================================
# NINJATRADER BRIDGE
# ============================================================================

class NinjaTraderBridge:
    """
    Bridge to NinjaTrader Market Replay data.

    Reads trade events from NinjaTrader Playback connection (proven/approved).
    Records immutable evidence for Guardian approval.
    """

    def __init__(self, db_path: str = "ninjatrader.db"):
        self.db_path = db_path
        self.sessions: Dict[UUID, ReplaySession] = {}
        self.metrics: Dict[UUID, ReplayMetrics] = {}
        self.authority = "ZERO"
        self.live_enabled = False
        self.broker_orders_allowed = False
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for replay sessions"""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Replay sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replay_sessions (
                session_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                instrument TEXT NOT NULL,
                market_date TEXT NOT NULL,
                replay_speed INTEGER NOT NULL,
                start_time TEXT,
                end_time TEXT,
                data_source TEXT NOT NULL,
                authority TEXT NOT NULL DEFAULT 'ZERO',
                live_enabled BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'READY'
            )
        """)

        # Trade events table (immutable, append-only)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                instrument TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_quantity INTEGER NOT NULL,
                stop_price REAL NOT NULL,
                target_price REAL NOT NULL,
                exit_time TEXT,
                exit_price REAL,
                status TEXT NOT NULL,
                pnl_ticks INTEGER,
                pnl_dollars REAL,
                cost_per_side REAL NOT NULL,
                slippage_ticks REAL NOT NULL,
                recorded_at TEXT NOT NULL,
                observation_hash TEXT NOT NULL,
                authority TEXT NOT NULL DEFAULT 'ZERO',
                FOREIGN KEY (session_id) REFERENCES replay_sessions(session_id)
            )
        """)

        # Session metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_metrics (
                session_id TEXT PRIMARY KEY,
                strategy_name TEXT NOT NULL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                gross_pnl_ticks INTEGER,
                gross_pnl_dollars REAL,
                net_pnl_dollars REAL,
                max_drawdown_dollars REAL,
                win_rate REAL,
                profit_factor REAL,
                avg_pnl_per_trade REAL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES replay_sessions(session_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_session ON trade_events(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trade_events(instrument)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trade_events(strategy_name)")

        conn.commit()
        conn.close()

    def create_replay_session(
        self,
        strategy_name: str,
        instrument: str,
        market_date: str,
        replay_speed: int = 1,
        start_time: str = "09:30",
        end_time: str = "16:00"
    ) -> ReplaySession:
        """Create new Market Replay session"""
        session = ReplaySession(
            session_id=uuid4(),
            strategy_name=strategy_name,
            instrument=instrument,
            market_date=market_date,
            replay_speed=replay_speed,
            start_time=start_time,
            end_time=end_time,
            data_source="NINJATRADER_PLAYBACK",
            created_at=datetime.utcnow(),
            authority="ZERO",
            live_enabled=False
        )

        self.sessions[session.session_id] = session
        self.metrics[session.session_id] = ReplayMetrics(
            session_id=session.session_id,
            strategy_name=strategy_name
        )

        # Save to DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO replay_sessions
            (session_id, strategy_name, instrument, market_date, replay_speed,
             start_time, end_time, data_source, authority, live_enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(session.session_id), session.strategy_name, session.instrument,
            session.market_date, session.replay_speed, session.start_time,
            session.end_time, session.data_source, session.authority,
            session.live_enabled, session.created_at.isoformat()
        ))
        conn.commit()
        conn.close()

        return session

    def record_trade(
        self,
        session_id: UUID,
        strategy_name: str,
        instrument: str,
        side: TradeSide,
        entry_time: datetime,
        entry_price: float,
        entry_quantity: int,
        stop_price: float,
        target_price: float,
        exit_time: Optional[datetime] = None,
        exit_price: Optional[float] = None,
        status: TradeStatus = TradeStatus.FILLED,
        pnl_ticks: Optional[int] = None,
        pnl_dollars: Optional[float] = None,
        cost_per_side: float = 2.25,
        slippage_ticks: float = 0.0
    ) -> TradeEvent:
        """Record immutable trade event from Market Replay"""

        observation_hash = hashlib.sha256(
            json.dumps({
                "side": side.value,
                "entry_price": entry_price,
                "entry_qty": entry_quantity,
                "stop": stop_price,
                "target": target_price,
                "entry_time": entry_time.isoformat(),
                "strategy": strategy_name,
                "instrument": instrument
            }, sort_keys=True).encode()
        ).hexdigest()

        trade = TradeEvent(
            event_id=uuid4(),
            replay_session_id=session_id,
            strategy_name=strategy_name,
            instrument=instrument,
            side=side,
            entry_time=entry_time,
            entry_price=entry_price,
            entry_quantity=entry_quantity,
            stop_price=stop_price,
            target_price=target_price,
            exit_time=exit_time,
            exit_price=exit_price,
            status=status,
            pnl_ticks=pnl_ticks,
            pnl_dollars=pnl_dollars,
            cost_per_side=cost_per_side,
            slippage_ticks=slippage_ticks,
            recorded_at=datetime.utcnow(),
            observation_hash=observation_hash,
            authority="ZERO",
            broker_orders_allowed=False,
            live_enabled=False
        )

        # Add to metrics
        if session_id in self.metrics:
            self.metrics[session_id].add_trade(trade)

        # Save to DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trade_events
            (event_id, session_id, strategy_name, instrument, side, entry_time, entry_price,
             entry_quantity, stop_price, target_price, exit_time, exit_price, status, pnl_ticks,
             pnl_dollars, cost_per_side, slippage_ticks, recorded_at, observation_hash, authority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(trade.event_id), str(trade.replay_session_id), trade.strategy_name,
            trade.instrument, trade.side.value, trade.entry_time.isoformat(),
            trade.entry_price, trade.entry_quantity, trade.stop_price, trade.target_price,
            trade.exit_time.isoformat() if trade.exit_time else None,
            trade.exit_price, trade.status.value, trade.pnl_ticks,
            trade.pnl_dollars, trade.cost_per_side, trade.slippage_ticks,
            trade.recorded_at.isoformat(), trade.observation_hash, trade.authority
        ))
        conn.commit()
        conn.close()

        return trade

    def get_session_metrics(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        """Get running metrics for replay session"""
        if session_id not in self.metrics:
            return None

        metrics = self.metrics[session_id]
        return {
            "session_id": str(metrics.session_id),
            "strategy_name": metrics.strategy_name,
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "win_rate": round(metrics.win_rate, 4),
            "gross_pnl_dollars": round(metrics.gross_pnl_dollars, 2),
            "net_pnl_dollars": round(metrics.net_pnl_dollars, 2),
            "max_drawdown_dollars": round(metrics.max_drawdown_dollars, 2),
            "avg_pnl_per_trade": round(metrics.avg_pnl_per_trade, 2),
            "profit_factor": metrics.profit_factor,
            "trade_count": len(metrics.trades)
        }

    def get_session_trades(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Get all trades from session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT event_id, strategy_name, instrument, side, entry_time, entry_price,
                   entry_quantity, stop_price, target_price, exit_time, exit_price,
                   status, pnl_ticks, pnl_dollars, cost_per_side, slippage_ticks
            FROM trade_events
            WHERE session_id = ?
            ORDER BY entry_time
        """, (str(session_id),))

        trades = []
        for row in cursor.fetchall():
            trades.append({
                "event_id": row[0],
                "strategy": row[1],
                "instrument": row[2],
                "side": row[3],
                "entry_time": row[4],
                "entry_price": row[5],
                "quantity": row[6],
                "stop": row[7],
                "target": row[8],
                "exit_time": row[9],
                "exit_price": row[10],
                "status": row[11],
                "pnl_ticks": row[12],
                "pnl_dollars": row[13],
                "cost": row[14],
                "slippage": row[15]
            })

        conn.close()
        return trades

    def compare_to_baseline(self, session_id: UUID, baseline_winrate: float = 0.833) -> Dict[str, Any]:
        """Compare session to RR500 baseline (83.3% win rate)"""
        metrics = self.get_session_metrics(session_id)
        if not metrics:
            return {}

        return {
            "session_metrics": metrics,
            "baseline": {
                "win_rate": baseline_winrate,
                "pnl_dollars": 2080,
                "pnl_per_trade": 173.33,
                "trades": 12
            },
            "comparison": {
                "vs_baseline_winrate": round(metrics["win_rate"] - baseline_winrate, 4),
                "vs_baseline_pnl": round(metrics["net_pnl_dollars"] - 2080, 2),
                "performance": "PASS" if metrics["win_rate"] >= baseline_winrate else "NEEDS_WORK"
            }
        }


if __name__ == "__main__":
    # Demo: Create replay session and log trades
    bridge = NinjaTraderBridge("ninjatrader.db")

    session = bridge.create_replay_session(
        strategy_name="RR500",
        instrument="NQ",
        market_date="20260907",
        replay_speed=1
    )

    print(f"Session created: {session.session_id}")

    # Log sample trades
    trade1 = bridge.record_trade(
        session_id=session.session_id,
        strategy_name="RR500",
        instrument="NQ",
        side=TradeSide.BUY,
        entry_time=datetime.utcnow(),
        entry_price=20150.50,
        entry_quantity=1,
        stop_price=20140.00,
        target_price=20180.00,
        exit_time=datetime.utcnow(),
        exit_price=20180.00,
        status=TradeStatus.TARGET_HIT,
        pnl_ticks=30,
        pnl_dollars=150.00
    )

    print(f"\nMetrics:")
    metrics = bridge.get_session_metrics(session.session_id)
    print(json.dumps(metrics, indent=2))

    print(f"\nComparison to baseline:")
    comparison = bridge.compare_to_baseline(session.session_id)
    print(json.dumps(comparison, indent=2))
