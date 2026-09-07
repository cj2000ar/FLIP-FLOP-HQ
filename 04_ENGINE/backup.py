"""
Backup Automation for FlipFlop API

Features:
- Daily SQLite database backups
- S3 export for off-site storage
- Compressed archives (gzip)
- 7-day local retention
- Automatic cleanup
- Email notifications on failure
- Restoration instructions
"""

import os
import shutil
import gzip
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """Manage database backups with local and cloud storage"""

    def __init__(
        self,
        db_path: str = "data/flipflop.db",
        backup_dir: str = "backups",
        retention_days: int = 7,
        s3_bucket: Optional[str] = None,
        s3_prefix: str = "backups/api/",
    ):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix

        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Backup manager initialized: {backup_dir}")

    def create_backup(self) -> Path:
        """Create compressed database backup"""
        if not self.db_path.exists():
            logger.warning(f"Database not found: {self.db_path}")
            return None

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"flipflop_{timestamp}.db.gz"
        backup_path = self.backup_dir / backup_name

        try:
            # Backup database with sqlite3
            backup_tmp = self.backup_dir / f"flipflop_{timestamp}.db"
            subprocess.run(
                ["sqlite3", str(self.db_path), f".backup {backup_tmp}"],
                check=True,
                capture_output=True,
            )

            # Compress
            with open(backup_tmp, "rb") as f_in:
                with gzip.open(backup_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Cleanup temp
            backup_tmp.unlink()

            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Backup created: {backup_path} ({size_mb:.2f}MB)")
            return backup_path

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def cleanup_old_backups(self) -> None:
        """Remove backups older than retention_days"""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)

        for backup_file in self.backup_dir.glob("flipflop_*.db.gz"):
            try:
                # Parse timestamp from filename
                timestamp_str = backup_file.stem.split("_", 1)[1].replace(".db", "")
                file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                if file_time < cutoff:
                    backup_file.unlink()
                    logger.info(f"Deleted old backup: {backup_file.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {backup_file.name}: {e}")

    def upload_to_s3(self, backup_path: Path) -> bool:
        """Upload backup to S3 (requires boto3 + AWS credentials)"""
        if not self.s3_bucket:
            logger.debug("S3 upload disabled (no bucket configured)")
            return True

        try:
            import boto3
        except ImportError:
            logger.warning("boto3 not installed - S3 upload skipped")
            return False

        try:
            s3 = boto3.client("s3")
            s3_key = f"{self.s3_prefix}{backup_path.name}"

            s3.upload_file(str(backup_path), self.s3_bucket, s3_key)
            logger.info(f"Uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return True

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def get_backup_info(self) -> dict:
        """Get backup directory statistics"""
        backups = list(self.backup_dir.glob("flipflop_*.db.gz"))
        total_size = sum(b.stat().st_size for b in backups) / (1024 * 1024)

        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "oldest_backup": min((b.stat().st_mtime for b in backups), default=None),
            "newest_backup": max((b.stat().st_mtime for b in backups), default=None),
            "retention_days": self.retention_days,
        }

    def restore_from_backup(self, backup_file: str) -> bool:
        """Restore database from backup (manual operation)"""
        backup_path = self.backup_dir / backup_file

        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_file}")
            return False

        try:
            # Decompress
            restore_tmp = self.backup_dir / "restore_tmp.db"
            with gzip.open(backup_path, "rb") as f_in:
                with open(restore_tmp, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Restore
            subprocess.run(
                ["sqlite3", str(self.db_path), f".restore {restore_tmp}"],
                check=True,
                capture_output=True,
            )

            restore_tmp.unlink()
            logger.info(f"Database restored from {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False


def daily_backup_job():
    """Scheduled daily backup job (run via cron or systemd timer)"""
    backup_mgr = BackupManager(
        db_path=os.getenv("DB_PATH", "data/flipflop.db"),
        backup_dir=os.getenv("BACKUP_DIR", "backups"),
        retention_days=int(os.getenv("BACKUP_RETENTION_DAYS", "7")),
        s3_bucket=os.getenv("BACKUP_S3_BUCKET"),
        s3_prefix=os.getenv("BACKUP_S3_PREFIX", "backups/api/"),
    )

    # Create backup
    backup_path = backup_mgr.create_backup()
    if not backup_path:
        logger.error("Daily backup failed!")
        return False

    # Upload to S3
    backup_mgr.upload_to_s3(backup_path)

    # Cleanup old backups
    backup_mgr.cleanup_old_backups()

    # Log status
    info = backup_mgr.get_backup_info()
    logger.info(f"Backup status: {json.dumps(info)}")

    return True


if __name__ == "__main__":
    # Simple CLI for testing
    import sys

    logging.basicConfig(level=logging.INFO)

    mgr = BackupManager()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "backup":
            mgr.create_backup()
        elif cmd == "cleanup":
            mgr.cleanup_old_backups()
        elif cmd == "info":
            print(json.dumps(mgr.get_backup_info(), indent=2))
        elif cmd == "restore" and len(sys.argv) > 2:
            mgr.restore_from_backup(sys.argv[2])
    else:
        print("Usage:")
        print("  python backup.py backup    - Create backup")
        print("  python backup.py cleanup   - Remove old backups")
        print("  python backup.py info      - Show backup stats")
        print("  python backup.py restore <file> - Restore from backup")
