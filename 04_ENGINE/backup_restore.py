"""Backup and restore system with integrity verification"""

import shutil
import sqlite3
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class BackupManager:
    """Daily backups with integrity checking"""

    def __init__(self, db_dir: str = "databases", backup_dir: str = "backups"):
        self.db_dir = Path(db_dir)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = 30

    def backup_all(self) -> Dict[str, Any]:
        """Backup all databases with checksums"""
        backup_date = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / backup_date
        backup_path.mkdir(parents=True, exist_ok=True)

        manifest = {
            'backup_date': backup_date,
            'timestamp': datetime.utcnow().isoformat(),
            'databases': {}
        }

        # Backup each database
        for db_file in self.db_dir.glob("*.db"):
            try:
                backup_file = backup_path / db_file.name
                shutil.copy2(str(db_file), str(backup_file))

                # Compute checksum
                with open(backup_file, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()

                manifest['databases'][db_file.name] = {
                    'size_bytes': backup_file.stat().st_size,
                    'sha256': file_hash,
                    'backed_up_at': datetime.utcnow().isoformat()
                }

                logger.info(f"Backed up: {db_file.name} ({backup_file.stat().st_size} bytes)")

            except Exception as e:
                logger.error(f"Backup failed for {db_file.name}: {str(e)}")
                manifest['databases'][db_file.name] = {
                    'status': 'FAILED',
                    'error': str(e)
                }

        # Save manifest
        manifest_file = backup_path / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Cleanup old backups
        self._cleanup_old_backups()

        logger.info(f"Backup completed: {backup_path}")
        return {
            'status': 'OK',
            'backup_path': str(backup_path),
            'manifest': manifest
        }

    def verify_backup(self, backup_date: str) -> Dict[str, Any]:
        """Verify backup integrity"""
        backup_path = self.backup_dir / backup_date
        manifest_file = backup_path / "manifest.json"

        if not manifest_file.exists():
            return {'status': 'FAILED', 'error': 'Manifest not found'}

        with open(manifest_file) as f:
            manifest = json.load(f)

        errors = []

        for db_name, db_info in manifest['databases'].items():
            if db_info.get('status') == 'FAILED':
                errors.append(f"{db_name}: backup failed")
                continue

            backup_file = backup_path / db_name

            if not backup_file.exists():
                errors.append(f"{db_name}: file not found")
                continue

            # Verify checksum
            with open(backup_file, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            if file_hash != db_info.get('sha256'):
                errors.append(
                    f"{db_name}: checksum mismatch "
                    f"(expected {db_info['sha256'][:8]}..., got {file_hash[:8]}...)"
                )

        if errors:
            return {
                'status': 'CORRUPTED',
                'errors': errors
            }

        return {
            'status': 'VERIFIED',
            'database_count': len(manifest['databases']),
            'backup_date': manifest['backup_date'],
            'timestamp': manifest['timestamp']
        }

    def restore_from_backup(self, backup_date: str) -> Dict[str, Any]:
        """Restore all databases from backup"""
        backup_path = self.backup_dir / backup_date

        if not backup_path.exists():
            return {'status': 'FAILED', 'error': f'Backup not found: {backup_date}'}

        # Verify backup first
        verification = self.verify_backup(backup_date)
        if verification['status'] != 'VERIFIED':
            return {
                'status': 'FAILED',
                'error': f'Backup verification failed: {verification}'
            }

        # Restore each file
        restored = []
        errors = []

        for backup_file in backup_path.glob("*.db"):
            try:
                target_file = self.db_dir / backup_file.name
                shutil.copy2(str(backup_file), str(target_file))
                restored.append(backup_file.name)
                logger.info(f"Restored: {backup_file.name}")
            except Exception as e:
                errors.append(f"{backup_file.name}: {str(e)}")
                logger.error(f"Restore failed for {backup_file.name}: {str(e)}")

        if errors:
            return {
                'status': 'PARTIAL',
                'restored': restored,
                'errors': errors
            }

        return {
            'status': 'OK',
            'restored_count': len(restored),
            'restored_files': restored,
            'restore_time': datetime.utcnow().isoformat()
        }

    def _cleanup_old_backups(self) -> None:
        """Remove backups older than retention period"""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)

        for backup_path in self.backup_dir.iterdir():
            if not backup_path.is_dir():
                continue

            try:
                # Parse date from directory name (YYYYMMDD_HHMMSS)
                date_str = backup_path.name.split('_')[0]
                backup_time = datetime.strptime(date_str, "%Y%m%d")

                if backup_time < cutoff:
                    shutil.rmtree(backup_path)
                    logger.info(f"Cleaned up old backup: {backup_path.name}")
            except Exception as e:
                logger.warning(f"Cleanup error for {backup_path.name}: {str(e)}")

    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []

        for backup_path in sorted(self.backup_dir.iterdir(), reverse=True):
            if not backup_path.is_dir():
                continue

            manifest_file = backup_path / "manifest.json"
            if not manifest_file.exists():
                continue

            with open(manifest_file) as f:
                manifest = json.load(f)

            backups.append({
                'backup_date': backup_path.name,
                'timestamp': manifest['timestamp'],
                'database_count': len(manifest['databases'])
            })

        return backups
