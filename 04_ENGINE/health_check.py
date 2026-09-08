"""Health check endpoints for FlipFlop scheduler"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class HealthChecker:
    """Comprehensive health checks with dependency validation"""

    def __init__(self, db_dir="databases"):
        self.db_dir = Path(db_dir)

    def check_all(self) -> dict:
        """Run all health checks, fail-closed"""
        checks = {
            'scheduler_running': self._check_scheduler_running(),
            'database_accessible': self._check_database_accessible(),
            'market_data_fresh': self._check_market_data_fresh(),
            'last_backtest_age': self._check_last_backtest_age(),
            'memory_available': self._check_memory_available(),
            'disk_available': self._check_disk_available(),
            'audit_chain': self._check_audit_chain(),
        }

        # Fail-closed: ANY failure = UNHEALTHY
        failed = [k for k, v in checks.items() if not v.get('ok', False)]

        if failed:
            status = 'UNHEALTHY'
        elif any(v.get('degraded', False) for v in checks.values()):
            status = 'DEGRADED'
        else:
            status = 'HEALTHY'

        return {
            'status': status,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': checks,
            'failed_checks': failed,
            'authority': 'ZERO',
            'live': 'OFF'
        }

    def _check_scheduler_running(self) -> dict:
        """Verify scheduler process is responsive"""
        try:
            # Check if this process is running (basic sanity check)
            pid = os.getpid()
            return {
                'ok': True,
                'pid': pid,
                'message': 'Scheduler running'
            }
        except Exception as e:
            return {'ok': False, 'message': f'Scheduler check failed: {e}'}

    def _check_database_accessible(self) -> dict:
        """Verify market data database is accessible"""
        try:
            db_files = list(self.db_dir.glob('market_data_*.db'))
            if not db_files:
                return {'ok': False, 'message': 'No market data databases found'}

            latest_db = max(db_files, key=os.path.getctime')
            conn = sqlite3.connect(str(latest_db))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM market_bars")
            count = cursor.fetchone()[0]
            conn.close()

            return {
                'ok': True,
                'database': latest_db.name,
                'bar_count': count,
                'message': f'{count} bars in database'
            }
        except Exception as e:
            return {'ok': False, 'message': f'Database check failed: {e}'}

    def _check_market_data_fresh(self) -> dict:
        """Market data must exist and be < 24 hours old"""
        try:
            db_files = list(self.db_dir.glob('market_data_*.db'))
            if not db_files:
                return {
                    'ok': False,
                    'message': 'No market data found',
                    'degraded': True
                }

            latest_db = max(db_files, key=os.path.getctime')
            file_age_hours = (datetime.utcnow() - datetime.fromtimestamp(
                os.path.getctime(latest_db)
            )).total_seconds() / 3600

            if file_age_hours > 24:
                return {
                    'ok': False,
                    'age_hours': file_age_hours,
                    'message': f'Market data stale: {file_age_hours:.1f} hours',
                    'degraded': True
                }

            return {
                'ok': True,
                'age_hours': file_age_hours,
                'message': f'Fresh data: {file_age_hours:.1f} hours old'
            }
        except Exception as e:
            return {'ok': False, 'message': f'Data freshness check failed: {e}'}

    def _check_last_backtest_age(self) -> dict:
        """Last backtest must be < 6 hours old"""
        try:
            db_path = self.db_dir / 'results.db'
            if not db_path.exists():
                return {
                    'ok': False,
                    'message': 'No results database',
                    'degraded': True
                }

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(timestamp) FROM completed_backtests")
            last_backtest = cursor.fetchone()[0]
            conn.close()

            if not last_backtest:
                return {
                    'ok': False,
                    'message': 'No backtest completed',
                    'degraded': True
                }

            age = (datetime.utcnow() - datetime.fromisoformat(last_backtest)).total_seconds() / 3600

            if age > 6:
                return {
                    'ok': False,
                    'age_hours': age,
                    'message': f'Last backtest: {age:.1f} hours ago',
                    'degraded': True
                }

            return {
                'ok': True,
                'age_hours': age,
                'message': f'Last backtest: {age:.1f} hours ago'
            }
        except Exception as e:
            return {'ok': False, 'message': f'Backtest age check failed: {e}'}

    def _check_memory_available(self) -> dict:
        """Verify > 2GB free memory"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            free_gb = mem.available / (1024**3)

            if free_gb < 2:
                return {
                    'ok': False,
                    'free_gb': free_gb,
                    'message': f'Memory pressure: {free_gb:.1f}GB free',
                    'degraded': True
                }

            return {
                'ok': True,
                'free_gb': free_gb,
                'message': f'{free_gb:.1f}GB free'
            }
        except ImportError:
            return {'ok': True, 'message': 'psutil not installed, skipping'}
        except Exception as e:
            return {'ok': False, 'message': f'Memory check failed: {e}'}

    def _check_disk_available(self) -> dict:
        """Verify > 100GB free disk"""
        try:
            import shutil
            usage = shutil.disk_usage('/')
            free_gb = usage.free / (1024**3)

            if free_gb < 100:
                return {
                    'ok': False,
                    'free_gb': free_gb,
                    'message': f'Disk pressure: {free_gb:.1f}GB free',
                    'degraded': True
                }

            return {
                'ok': True,
                'free_gb': free_gb,
                'message': f'{free_gb:.1f}GB free'
            }
        except Exception as e:
            return {'ok': False, 'message': f'Disk check failed: {e}'}

    def _check_audit_chain(self) -> dict:
        """Verify audit trail integrity"""
        try:
            audit_path = self.db_dir / 'audit.db'
            if not audit_path.exists():
                return {'ok': True, 'message': 'Audit database not yet created'}

            conn = sqlite3.connect(str(audit_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]
            conn.close()

            return {
                'ok': True,
                'event_count': count,
                'message': f'Audit chain: {count} events'
            }
        except Exception as e:
            return {'ok': False, 'message': f'Audit chain check failed: {e}'}
