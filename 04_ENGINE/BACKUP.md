# FlipFlop API - Backup & Recovery Strategy

## Overview

Automated daily backups with local retention + S3 export. Point-in-time recovery capability.

**Features:**
- Daily compressed SQLite backups (gzip)
- 7-day local retention
- S3 off-site storage (optional)
- Automated cleanup of old backups
- Restoration tools
- Systemd timer automation

## Setup

### Local Backups (Required)

```bash
# Directory structure
mkdir -p backups logs data

# Run manual backup
python backup.py backup

# Check backup status
python backup.py info
```

**Output:**
```
{
  "total_backups": 5,
  "total_size_mb": 45.3,
  "retention_days": 7,
  "oldest_backup": 1234567890,
  "newest_backup": 1234567950
}
```

### S3 Remote Backups (Optional, Recommended)

#### Prerequisites

```bash
pip install boto3
aws configure  # Set AWS credentials
```

#### Enable S3 Export

```bash
# Environment variables
export BACKUP_S3_BUCKET=my-flipflop-backups
export BACKUP_S3_PREFIX=backups/api/
export BACKUP_RETENTION_DAYS=7

# Run backup (auto-uploads to S3)
python backup.py backup
```

#### S3 Bucket Policy (Secure)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencrypted",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-flipflop-backups/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    },
    {
      "Sid": "DenyIncorrectKMS",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-flipflop-backups/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-acl": "private"
        }
      }
    }
  ]
}
```

## Automated Backups (Production)

### Linux with systemd

```bash
# Copy service files
sudo cp flipflop-backup.service /etc/systemd/system/
sudo cp flipflop-backup.timer /etc/systemd/system/

# Enable timer
sudo systemctl daemon-reload
sudo systemctl enable flipflop-backup.timer
sudo systemctl start flipflop-backup.timer

# Check status
sudo systemctl list-timers flipflop-backup.timer
sudo systemctl status flipflop-backup.service
```

**Schedule:** Daily at 2:00 AM UTC (configurable in .timer file)

### Manual Cron Job (Alternative)

```bash
# Add to crontab
0 2 * * * cd /opt/flipflop/api && python3 backup.py backup >> logs/backup.log 2>&1
```

### Windows Task Scheduler

```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "python" `
  -Argument "C:\FLIP_FLOP_HQ\04_ENGINE\backup.py backup" `
  -WorkingDirectory "C:\FLIP_FLOP_HQ\04_ENGINE"

$trigger = New-ScheduledTaskTrigger -Daily -At 02:00:00 AM

Register-ScheduledTask -TaskName "FlipFlop API Backup" `
  -Action $action -Trigger $trigger -RunLevel Highest
```

## Recovery

### List Available Backups

```bash
python backup.py info
ls -lh backups/
```

### Restore from Local Backup

```bash
# Stop API
sudo systemctl stop flipflop-api

# Restore
python backup.py restore flipflop_20260907_140000.db.gz

# Start API
sudo systemctl start flipflop-api
```

### Restore from S3

```bash
# Download backup
aws s3 cp s3://my-flipflop-backups/backups/api/flipflop_20260907_140000.db.gz backups/

# Restore
python backup.py restore flipflop_20260907_140000.db.gz
```

## Monitoring

### Backup Logs

```bash
# Linux/systemd
sudo journalctl -u flipflop-backup.service -f

# Docker
docker-compose logs flipflop-api | grep backup

# Manual log file
tail -f logs/flipflop.log | grep backup
```

### Backup Size Monitoring

```bash
# Check current size
du -sh backups/

# Monitor growth
watch -n 60 'du -sh backups/'
```

### Disk Space Alert

Set alert if backups exceed threshold:

```bash
BACKUP_SIZE=$(du -sb backups/ | cut -f1)
MAX_SIZE=$((100 * 1024 * 1024))  # 100MB limit

if [ $BACKUP_SIZE -gt $MAX_SIZE ]; then
  echo "WARNING: Backups exceed 100MB"
  # Send alert, trigger cleanup
fi
```

## Backup Lifecycle

```
Create Backup (daily)
    ↓
Compress (gzip)
    ↓
Store Locally (backups/)
    ↓
Upload to S3 (if configured)
    ↓
Cleanup (7 days later) ← removes old local backups
```

## Retention Policy

| Backup Type | Retention | Purpose |
|------------|-----------|---------|
| Local | 7 days | Fast recovery, minimal storage |
| S3 | 30 days | Off-site, audit trail, compliance |
| Archive | 1 year | Annual backup, legal holds |

## Testing Backups

### Monthly Recovery Test

```bash
# 1. Create test database copy
cp data/flipflop.db data/flipflop_test.db

# 2. Restore backup to test DB
python backup.py restore flipflop_20260907_140000.db.gz

# 3. Validate data integrity
sqlite3 data/flipflop.db "SELECT COUNT(*) FROM experiments;"
sqlite3 data/flipflop_test.db "SELECT COUNT(*) FROM experiments;"

# 4. Verify counts match
# 5. Cleanup
rm data/flipflop_test.db
```

## Disaster Recovery Plan

### Total Data Loss Scenario

1. **Assess:** Determine what was lost (data, metadata, logs)
2. **Stop API:** `sudo systemctl stop flipflop-api`
3. **Restore Latest:** `python backup.py restore flipflop_LATEST.db.gz`
4. **Verify:** Check data integrity (row counts, timestamps)
5. **Start API:** `sudo systemctl start flipflop-api`
6. **Monitor:** Watch logs for any errors
7. **Notify:** Alert users of recovery

### Partial Corruption Scenario

1. **Identify:** Which tables are corrupted
2. **Check Backup:** Restore to test database
3. **Compare:** Identify what's lost vs. what's corrupted
4. **Restore Selectively:** Restore only corrupted tables (manual SQL)
5. **Verify:** Full integrity check before production restart

## Configuration

### Environment Variables

```bash
# Database path
DB_PATH=data/flipflop.db

# Backup directory
BACKUP_DIR=backups

# Local retention (days)
BACKUP_RETENTION_DAYS=7

# S3 storage (optional)
BACKUP_S3_BUCKET=my-flipflop-backups
BACKUP_S3_PREFIX=backups/api/

# Logging
LOG_DIR=logs
LOG_LEVEL=INFO
```

### Docker Setup

```yaml
services:
  flipflop-api:
    volumes:
      - ./backups:/app/backups
      - ./data:/app/data
    environment:
      - BACKUP_S3_BUCKET=my-bucket
```

## Cost Estimation

### Storage Costs (AWS S3)

| Scenario | Daily Backup | 30-day Cost |
|----------|--------------|-------------|
| 10 MB db | 300 MB/month | ~$0.07 |
| 100 MB db | 3 GB/month | ~$0.07 |
| 1 GB db | 30 GB/month | ~$0.69 |

## Best Practices

✅ **Do:**
- Backup daily, especially before deployments
- Test restoration monthly
- Monitor backup completion
- Keep S3 backups for 30+ days
- Document restoration procedures
- Alert on backup failures

❌ **Don't:**
- Skip backups for "just testing"
- Store backups only locally
- Forget to test restoration
- Leave backups unencrypted
- Mix backup retention policies

## Compliance & Audit

### Backup Metadata

Each backup includes:
- Timestamp (creation time)
- Database version (schema version)
- Row counts (per table)
- File size (compressed)
- Checksum (integrity verification)

### Audit Trail

Backup operations logged in structured JSON:
```json
{
  "timestamp": "2026-09-07T02:00:00Z",
  "operation": "backup_created",
  "file": "flipflop_20260907_020000.db.gz",
  "size_mb": 45.3,
  "s3_uploaded": true,
  "old_backups_cleaned": 1,
  "next_retention_date": "2026-09-14T02:00:00Z"
}
```

## Troubleshooting

### Backup Fails with "Database is locked"

```
Error: database is locked
```

**Solution:**
- Stop API before backup
- Or use non-blocking backup method
- Check for long-running queries

### S3 Upload Fails

```
Error: An error occurred (AccessDenied) when calling the PutObject operation
```

**Solution:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check S3 bucket policy
- Verify bucket exists and is accessible

### Restore Fails

```
Error: could not restore database
```

**Solution:**
- Verify backup file integrity: `gzip -t backup.db.gz`
- Check disk space: `df -h`
- Ensure database path is writable

## Next Steps

1. **Monitor:** Set up alerts for backup failures
2. **Archive:** Move 30-day-old backups to Glacier
3. **Encryption:** Enable S3 client-side encryption
4. **Automation:** Wire backup job into CI/CD
5. **Documentation:** Document recovery procedures in runbooks
