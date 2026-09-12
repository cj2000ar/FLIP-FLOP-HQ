"""
Market Data Downloader - EOD Auto-Download
Authority: ZERO (locked, non-negotiable)

Fetch market data daily at 5 PM ET:
- OHLCV bars from multiple instruments
- Data quality validation
- Store in SQLite with immutable hashing
- Track download timestamps and quality metrics
"""

import os
import sqlite3
import hashlib
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4
import time

try:
    import alpaca_trade_api as tradeapi
except ImportError:
    tradeapi = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketBar:
    """Immutable OHLCV bar record"""
    bar_id: str
    instrument: str
    date: str  # YYYYMMDD
    time: str  # HHMM
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    recorded_at: float  # Unix timestamp
    data_source: str = "MARKET_DOWNLOADER"
    authority: str = "ZERO"
    integrity_hash: str = ""  # SHA256

    def __post_init__(self):
        if self.authority != "ZERO":
            raise ValueError("authority must be ZERO")
        if not (self.close_price >= self.low_price and
                self.close_price <= self.high_price):
            raise ValueError("close price must be within H/L range")


@dataclass(frozen=True)
class DownloadSession:
    """Immutable download session record"""
    session_id: str
    instrument: str
    download_date: str  # YYYYMMDD
    start_timestamp: float
    end_timestamp: float
    bars_count: int
    quality_score: float  # 0.0-1.0
    status: str  # "COMPLETE" | "PARTIAL" | "FAILED"
    error_msg: Optional[str] = None
    session_hash: str = ""
    authority: str = "ZERO"

    def __post_init__(self):
        if self.authority != "ZERO":
            raise ValueError("authority must be ZERO")
        if not (0.0 <= self.quality_score <= 1.0):
            raise ValueError("quality_score must be 0.0-1.0")


class MarketDownloader:
    """EOD market data downloader with validation"""

    def __init__(self, db_dir: str = "databases"):
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.authority = "ZERO"

    def get_db_path(self, date: str) -> Path:
        """Get database path for date (YYYYMMDD)"""
        return self.db_dir / f"market_data_{date}.db"

    def _init_db(self, db_path: Path):
        """Initialize database with immutable schema"""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_bars (
                bar_id TEXT PRIMARY KEY,
                instrument TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume INTEGER NOT NULL,
                recorded_at REAL NOT NULL,
                data_source TEXT NOT NULL,
                authority TEXT NOT NULL,
                integrity_hash TEXT NOT NULL,
                UNIQUE(instrument, date, time)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_sessions (
                session_id TEXT PRIMARY KEY,
                instrument TEXT NOT NULL,
                download_date TEXT NOT NULL,
                start_timestamp REAL NOT NULL,
                end_timestamp REAL NOT NULL,
                bars_count INTEGER NOT NULL,
                quality_score REAL NOT NULL,
                status TEXT NOT NULL,
                error_msg TEXT,
                session_hash TEXT NOT NULL,
                authority TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_instrument_date
            ON market_bars(instrument, date)
        """)

        conn.commit()
        conn.close()

    def _generate_bar_hash(self, bar: MarketBar) -> str:
        """Generate SHA256 hash of bar data"""
        data = f"{bar.instrument}{bar.date}{bar.time}{bar.open_price}" \
               f"{bar.high_price}{bar.low_price}{bar.close_price}{bar.volume}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _validate_bar_quality(self, bars: List[Dict[str, Any]]) -> float:
        """Validate data quality: gaps, outliers, volume"""
        if not bars:
            return 0.0

        quality_score = 1.0

        # Check for gaps
        gaps = 0
        for i in range(1, len(bars)):
            prev_time = int(bars[i-1]['time'])
            curr_time = int(bars[i]['time'])
            if curr_time - prev_time > 5:  # Allow 5 min gaps
                gaps += 1

        gap_penalty = min(len(bars) * 0.1, gaps * 0.05)
        quality_score -= gap_penalty

        # Check for zero volume
        zero_volume_count = sum(1 for b in bars if b['volume'] == 0)
        quality_score -= zero_volume_count * 0.02

        # Check for price anomalies
        for bar in bars:
            if bar['high'] < bar['low']:
                quality_score -= 0.1
            if bar['close'] > bar['high'] or bar['close'] < bar['low']:
                quality_score -= 0.05

        return max(0.0, quality_score)

    def download_daily_data(self, instruments: List[str], date: str) -> Dict[str, Any]:
        """
        Download EOD data for given date
        Args:
            instruments: List of instrument symbols (e.g., ["NQ", "ES"])
            date: Date in YYYYMMDD format
        Returns:
            Dict with download results per instrument
        """
        results = {}
        db_path = self.get_db_path(date)
        self._init_db(db_path)

        for instrument in instruments:
            session_id = str(uuid4())
            start_time = time.time()

            try:
                # Simulate data fetch (replace with actual broker API)
                bars_data = self._fetch_bars(instrument, date)

                if not bars_data:
                    session = DownloadSession(
                        session_id=session_id,
                        instrument=instrument,
                        download_date=date,
                        start_timestamp=start_time,
                        end_timestamp=time.time(),
                        bars_count=0,
                        quality_score=0.0,
                        status="FAILED",
                        error_msg="No data returned"
                    )
                    results[instrument] = {"status": "FAILED", "session_id": session_id}
                    continue

                # Validate quality
                quality_score = self._validate_bar_quality(bars_data)

                # Store bars
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                for bar_data in bars_data:
                    bar = MarketBar(
                        bar_id=str(uuid4()),
                        instrument=instrument,
                        date=date,
                        time=bar_data['time'],
                        open_price=bar_data['open'],
                        high_price=bar_data['high'],
                        low_price=bar_data['low'],
                        close_price=bar_data['close'],
                        volume=bar_data['volume'],
                        recorded_at=time.time(),
                        data_source="SYNTHETIC" if bar_data.get("synthetic") else "MARKET_DOWNLOADER",
                        integrity_hash=""
                    )

                    # Generate hash
                    integrity_hash = self._generate_bar_hash(bar)
                    bar_dict = asdict(bar)
                    bar_dict['integrity_hash'] = integrity_hash

                    cursor.execute("""
                        INSERT OR REPLACE INTO market_bars
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(bar_dict.values()))

                # Store session
                session_hash = hashlib.sha256(
                    f"{session_id}{instrument}{date}{len(bars_data)}{quality_score}".encode()
                ).hexdigest()

                cursor.execute("""
                    INSERT INTO download_sessions
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, instrument, date, start_time, time.time(),
                    len(bars_data), quality_score, "COMPLETE", None,
                    session_hash, self.authority
                ))

                conn.commit()
                conn.close()

                results[instrument] = {
                    "status": "COMPLETE",
                    "session_id": session_id,
                    "bars_count": len(bars_data),
                    "quality_score": quality_score,
                    "db_path": str(db_path)
                }

                logger.info(f"Downloaded {instrument} for {date}: "
                           f"{len(bars_data)} bars, quality={quality_score:.2f}")

            except Exception as e:
                logger.error(f"Error downloading {instrument}: {str(e)}")
                results[instrument] = {
                    "status": "FAILED",
                    "session_id": session_id,
                    "error": str(e)
                }

        return results

    def _fetch_bars(self, instrument: str, date: str) -> List[Dict[str, Any]]:
        """Fetch real bars from Alpaca SIP feed"""
        api_key = os.environ.get("ALPACA_API_KEY")
        api_secret = os.environ.get("ALPACA_API_SECRET")

        if not api_key or not api_secret or not tradeapi:
            logger.warning(f"Alpaca credentials missing or library not installed, using synthetic")
            return self._fetch_bars_synthetic(instrument, date)

        try:
            rest_api = tradeapi.REST(
                api_key, api_secret,
                base_url="https://api.alpaca.markets",
                api_version="v2"
            )

            # Verify date is past trading hours (after 4 PM ET / 8 PM UTC)
            now = datetime.utcnow()
            date_dt = datetime.strptime(date, "%Y%m%d")
            market_close = date_dt.replace(hour=20, minute=0, tzinfo=None)  # 4 PM ET = 8 PM UTC

            if now < market_close:
                logger.warning(f"Data for {date} not yet available (before market close)")
                return []

            # Fetch bars
            bars = rest_api.get_bars(
                instrument,
                "1Min",
                start=date_dt.strftime("%Y-%m-%d"),
                end=date_dt.strftime("%Y-%m-%d"),
                feed="sip"
            )

            result = []
            for bar in bars:
                result.append({
                    "time": bar.t.strftime("%H%M"),
                    "open": float(bar.o),
                    "high": float(bar.h),
                    "low": float(bar.l),
                    "close": float(bar.c),
                    "volume": int(bar.v)
                })

            logger.info(f"Alpaca SIP fetch {instrument}/{date}: {len(result)} bars")
            return result

        except Exception as e:
            logger.error(f"Alpaca fetch failed: {str(e)}")
            return []

    def _fetch_bars_synthetic(self, instrument: str, date: str) -> List[Dict[str, Any]]:
        """Synthetic fallback for testing only"""
        bars = []
        times = ["0930", "1000", "1030", "1100", "1130", "1200",
                "1230", "1300", "1330", "1400", "1430", "1500", "1530", "1600"]
        base_price = 5000.0
        for i, time_str in enumerate(times):
            bars.append({
                "time": time_str,
                "open": base_price + i,
                "high": base_price + i + 2,
                "low": base_price + i - 1,
                "close": base_price + i + 1,
                "volume": 1000000 + i * 50000,
                "synthetic": True,  # test fallback; must never be read as market evidence
            })
        return bars


def download_eod_job(instruments: List[str] = None):
    """Scheduled job for EOD download"""
    if instruments is None:
        instruments = ["NQ", "ES", "MNQ", "MES"]

    downloader = MarketDownloader()
    today = datetime.now().strftime("%Y%m%d")

    logger.info(f"Starting EOD download for {today}")
    results = downloader.download_daily_data(instruments, today)

    return results


if __name__ == "__main__":
    results = download_eod_job()
    print(json.dumps(results, indent=2))
