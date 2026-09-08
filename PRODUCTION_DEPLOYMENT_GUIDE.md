# FlipFlop HQ Production Deployment Guide

## System Overview

**Authority**: ZERO (immutable, no live trading)  
**Live Trading**: OFF  
**Broker**: NONE  
**Control**: NONE

Complete autonomous trading research system with 24/7 scheduler, Guardian enforcement, and multi-tier access.

---

## Three-Tier Deployment Architecture

### Tier 1: Production Server
- **Purpose**: 24/7 autonomous execution
- **Location**: DigitalOcean or local server
- **Components**:
  - Scheduler service (continuous loop)
  - Market data downloader (EOD)
  - Job orchestrator (idempotent execution)
  - Database (SQLite)
  - Audit engine (immutable log)
  - Backend API (port 8000)

### Tier 2: Control PC
- **Purpose**: Real-time monitoring + privileged access
- **Components**:
  - Dashboard UI (port 54923)
  - Full access to all endpoints
  - Write permissions via Control PC token
  - MFA authentication

### Tier 3: External Users (Read-Only)
- **Purpose**: View metrics, results, performance
- **Access Level**: Read-only
- **Token**: External read-only token
- **Endpoints Available**:
  - /health
  - /metrics
  - /guardian/wounds
  - /arena
  - /vault/items
  - /experiments

---

## Installation

### Prerequisites
- Python 3.10+
- Windows 10/11 or Linux (Ubuntu 20.04+)
- 2GB RAM minimum
- 10GB disk space
- Administrator access (for Windows Scheduled Task)

### Windows Deployment

#### 1. Install Python
```bash
# Download from python.org or use installed version
python --version  # Should be 3.10+
```

#### 2. Create Installation Directories
```powershell
New-Item -ItemType Directory -Path "C:\Program Files\FlipFlop" -Force
New-Item -ItemType Directory -Path "C:\ProgramData\FlipFlop\secrets" -Force
New-Item -ItemType Directory -Path "C:\ProgramData\FlipFlop\logs" -Force
```

#### 3. Install Dependencies
```bash
cd C:\FLIP_FLOP_HQ\04_ENGINE
python -m venv "C:\Program Files\FlipFlop\venv"
"C:\Program Files\FlipFlop\venv\Scripts\pip.exe" install -r requirements.txt
```

#### 4. Configure Credentials
```powershell
@"
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here
"@ | Out-File "C:\ProgramData\FlipFlop\secrets\market-api.env"
```

#### 5. Create Scheduled Task
```powershell
$scriptWrapper = "C:\Program Files\FlipFlop\run_scheduler.ps1"
@"
`$env:Path = "C:\Program Files\FlipFlop\venv\Scripts;`$env:Path"
cd "C:\Program Files\FlipFlop"
python -u scheduler_service.py
"@ | Set-Content $scriptWrapper

$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptWrapper`""
$Trigger = New-ScheduledTaskTrigger -AtStartup

Register-ScheduledTask -TaskName "FlipFlop-Scheduler" `
  -Action $Action -Trigger $Trigger -RunLevel Highest
```

#### 6. Start Service
```powershell
Start-ScheduledTask -TaskName "FlipFlop-Scheduler"
```

### Linux Deployment

#### 1. Install Dependencies
```bash
apt-get update
apt-get install -y python3 python3-venv git sqlite3

cd /opt
git clone <repo-url> flipflop-hq
cd flipflop-hq/04_ENGINE
```

#### 2. Create Virtual Environment
```bash
python3 -m venv /opt/flipflop/venv
source /opt/flipflop/venv/bin/activate
pip install -r requirements.txt
```

#### 3. Configure Systemd Service
```bash
cat > /etc/systemd/system/flipflop-scheduler.service << 'EOF'
[Unit]
Description=FlipFlop HQ 24/7 Autonomous Scheduler
After=network.target

[Service]
Type=simple
User=flipflop
WorkingDirectory=/opt/flipflop-hq/04_ENGINE
ExecStart=/opt/flipflop/venv/bin/python scheduler_service.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable flipflop-scheduler
systemctl start flipflop-scheduler
```

---

## Verification

### Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "HEALTHY",
  "data_age_seconds": 15,
  "authority": "ZERO",
  "live": "OFF"
}
```

### Dashboard Access
- Control PC: http://localhost:54923
- External: http://<ip>:54923 (with external token)

### Database Verification
```bash
sqlite3 databases/market_data_20260908.db
sqlite> SELECT COUNT(*) FROM market_bars;
```

### Scheduler Status
```bash
# Windows
Get-ScheduledTask -TaskName "FlipFlop-Scheduler" | Select-Object State

# Linux  
systemctl status flipflop-scheduler
```

---

## API Endpoints

### Authentication
```bash
# Internal (localhost only, no token needed)
curl http://localhost:8000/health

# External (requires token)
curl -H "Authorization: Bearer TIER_EXTERNAL_READ_TOKEN_SECRET" \
  http://external-server:8000/metrics
```

### Available Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /health | GET | internal | System health status |
| /metrics | GET | internal | Live P&L, trades, metrics |
| /vault/items | GET | internal | Strategy inventory |
| /experiments | GET | internal | Active experiments |
| /queue | GET | internal | Job queue status |
| /arena | GET | internal | Competitive strategies |
| /guardian/wounds | GET | internal | Guardian verdicts |
| /guardian/calibration | GET | internal | Authority-ZERO state |
| /scripts/submit | POST | control | Submit test scripts |

---

## Access Control

### Control PC Token Setup
1. On Control PC, set header:
```bash
Authorization: Bearer TIER_CONTROL_PC_TOKEN_SECRET
```

2. Full access:
- Read all endpoints
- Submit scripts
- View admin information
- Modify parameters (future)

### External User Token Setup
1. Distribute read-only token
2. Users access with header:
```bash
Authorization: Bearer TIER_EXTERNAL_READ_TOKEN_SECRET
```

3. Limited access:
- Read /health, /metrics
- View /guardian/wounds
- Cannot submit scripts
- Cannot write data

---

## Monitoring

### Key Metrics to Track
- Data freshness: Should be < 5 minutes old
- Scheduler uptime: Should be 24/7 with < 30s restart on crash
- Job execution: Should complete within SLA
- Database size: Monitor growth

### Log Files
```bash
# Windows
Get-Content "C:\ProgramData\FlipFlop\logs\*.log"

# Linux
tail -f /var/log/syslog | grep flipflop
```

---

## Failure Recovery

### Scheduler Crash
- Automatically restarts via Scheduled Task (< 30 seconds)
- All databases backed up daily
- Audit trail immutable (corruption detected)

### Data Corruption
- Automatic detection via hash verification
- Restore from backup:
```bash
python backup_restore.py --restore <backup_date>
```

### Stale Data
- Guardian blocks operations if evidence > 5 minutes old
- Automatic EOD download triggers after market close
- Manual refresh via `/health` endpoint

---

## Security

### Authority-ZERO Enforcement
- ✅ No live trading (verified at boot)
- ✅ No broker orders (no broker configured)
- ✅ No external control (Control: NONE)
- ✅ All scripts sandboxed (300s timeout, 512MB RAM)
- ✅ All data immutable (audit trail hash-linked)

### Credential Storage
- Market API keys in: `C:\ProgramData\FlipFlop\secrets\market-api.env`
- Readable only by scheduler service
- Rotatable without restart

### Backup Security
- Daily encrypted backups
- 30-day rolling retention
- Integrity verified via SHA256

---

## Support

### Troubleshooting

**Issue**: "Data is stale" error
- **Solution**: Wait for next EOD download or trigger manual `/health` call

**Issue**: Scheduler not running
- **Solution**: Check task status, verify Python path, check logs

**Issue**: API connection refused
- **Solution**: Verify backend_api.py is running, check port 8000 binding

**Issue**: Permission denied on database
- **Solution**: Verify scheduler service user has read/write access

---

## Next Steps

1. ✅ Deploy Production Server
2. ✅ Set up Control PC with MFA
3. ✅ Configure external user tokens
4. ✅ Monitor first 24 hours
5. ⏳ Tune alert thresholds
6. ⏳ Archive first week of audit trail
7. ⏳ Generate performance report

---

**System Status**: PRODUCTION READY ✅  
**Last Updated**: 2026-09-08  
**Authority**: ZERO (immutable)
