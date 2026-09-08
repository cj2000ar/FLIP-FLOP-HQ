"""Deterministic replay with immutable holdout boundaries"""

import numpy as np
import json
import hashlib
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class HoldoutRegistry:
    """Immutable holdout partition registry"""

    def __init__(self, db_dir: str = "databases"):
        self.db_dir = Path(db_dir)
        self.db_path = self.db_dir / "holdouts.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize append-only holdout registry"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holdout_assignments (
                assignment_id INTEGER PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                partition_type TEXT NOT NULL,
                date_range_start TEXT NOT NULL,
                date_range_end TEXT NOT NULL,
                locked_at TEXT NOT NULL,
                correlation_id TEXT UNIQUE NOT NULL,
                locked_by TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_backtest_history (
                backtest_id INTEGER PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                partition_type TEXT NOT NULL,
                backtest_dates TEXT NOT NULL,
                result_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (correlation_id) REFERENCES holdout_assignments(correlation_id)
            )
        """)

        conn.commit()
        conn.close()

    def lock_partition(self, strategy_id: str, partition_type: str,
                       date_range: Tuple[str, str]) -> Dict[str, Any]:
        """Lock partition before execution (immutable)"""
        correlation_id = hashlib.sha256(
            f"{strategy_id}{partition_type}{date_range[0]}{date_range[1]}".encode()
        ).hexdigest()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if already locked
        cursor.execute("""
            SELECT correlation_id FROM holdout_assignments
            WHERE strategy_id = ? AND partition_type = ?
        """, (strategy_id, partition_type))

        existing = cursor.fetchone()
        if existing:
            logger.warning(f"Partition already locked for {strategy_id}")
            conn.close()
            return {
                'status': 'ALREADY_LOCKED',
                'correlation_id': existing[0],
                'locked_at': datetime.utcnow().isoformat()
            }

        # Lock new partition
        cursor.execute("""
            INSERT INTO holdout_assignments
            (strategy_id, partition_type, date_range_start, date_range_end,
             locked_at, correlation_id, locked_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy_id,
            partition_type,
            date_range[0],
            date_range[1],
            datetime.utcnow().isoformat(),
            correlation_id,
            "SCHEDULER"
        ))

        conn.commit()
        conn.close()

        logger.info(f"Locked partition {partition_type} for {strategy_id}")
        return {
            'status': 'LOCKED',
            'correlation_id': correlation_id,
            'locked_at': datetime.utcnow().isoformat()
        }

    def check_holdout_reuse(self, strategy_id: str, test_dates: List[str]) -> bool:
        """Prevent retraining on held-out data"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT backtest_dates FROM strategy_backtest_history
            WHERE strategy_id = ? AND partition_type = 'HOLDOUT'
        """, (strategy_id,))

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            prior_dates = json.loads(row[0])
            overlap = set(test_dates) & set(prior_dates)
            if overlap:
                raise ValueError(
                    f"Holdout reuse detected: {overlap} already used in HOLDOUT partition"
                )

        return True

    def record_backtest(self, strategy_id: str, correlation_id: str,
                       partition_type: str, backtest_dates: List[str],
                       result_hash: str) -> None:
        """Record backtest execution (append-only)"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO strategy_backtest_history
            (strategy_id, correlation_id, partition_type, backtest_dates, result_hash, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            strategy_id,
            correlation_id,
            partition_type,
            json.dumps(backtest_dates),
            result_hash,
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()


class DeterministicReplayEngine:
    """Deterministic backtest with reproducible randomness"""

    def __init__(self, db_dir: str = "databases"):
        self.db_dir = Path(db_dir)
        self.holdouts = HoldoutRegistry(db_dir)

    def run_backtest(self, strategy_func, strategy_id: str, data_partition: Dict[str, Any],
                    partition_type: str = "VALIDATION") -> Dict[str, Any]:
        """Run deterministic backtest"""

        # Verify partition is locked
        if partition_type == "HOLDOUT":
            dates = (
                min(data_partition['dates']),
                max(data_partition['dates'])
            )
            lock = self.holdouts.lock_partition(strategy_id, partition_type, dates)
            correlation_id = lock['correlation_id']
        else:
            correlation_id = hashlib.sha256(
                f"{strategy_id}{partition_type}".encode()
            ).hexdigest()

        # Compute reproducible seed from correlation ID
        seed_value = int(correlation_id[:8], 16) % (2**32)
        np.random.seed(seed_value)

        # Run strategy with locked seed
        trades = []
        rng_log = []

        for bar in data_partition['bars']:
            rng_value = np.random.random()
            rng_log.append(rng_value)

            signal = strategy_func(bar, rng_value)
            if signal:
                trades.append({
                    'timestamp': bar['timestamp'],
                    'rng_value': rng_value,
                    'entry': bar['close'],
                    'stop': bar['close'] - 50,
                    'target': bar['close'] + 100
                })

        # Compute result hash
        result_content = json.dumps({
            'trades': len(trades),
            'correlation_id': correlation_id,
            'seed': seed_value
        }, sort_keys=True)
        result_hash = hashlib.sha256(result_content.encode()).hexdigest()

        # Verify determinism (run twice, compare)
        np.random.seed(seed_value)
        trades_verify = []
        for bar in data_partition['bars']:
            rng_value = np.random.random()
            signal = strategy_func(bar, rng_value)
            if signal:
                trades_verify.append({
                    'timestamp': bar['timestamp'],
                    'rng_value': rng_value
                })

        if len(trades) != len(trades_verify):
            raise RuntimeError(
                f"Non-deterministic execution: {len(trades)} trades first run, "
                f"{len(trades_verify)} second run"
            )

        # Record backtest
        self.holdouts.record_backtest(
            strategy_id, correlation_id, partition_type,
            data_partition['dates'], result_hash
        )

        return {
            'correlation_id': correlation_id,
            'partition_type': partition_type,
            'trades': trades,
            'determinism_verified': True,
            'result_hash': result_hash,
            'seed': seed_value,
            'rng_calls': len(rng_log),
            'timestamp': datetime.utcnow().isoformat()
        }

    def validate_no_holdout_reuse(self, strategy_id: str, test_dates: List[str]) -> None:
        """Prevent holdout data reuse"""
        self.holdouts.check_holdout_reuse(strategy_id, test_dates)
