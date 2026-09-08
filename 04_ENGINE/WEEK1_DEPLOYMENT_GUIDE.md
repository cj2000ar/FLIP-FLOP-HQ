# Week 1 Deployment Guide

**Goal:** Real market provider + Durable scheduler + Health checks + EOD download test

**Status:** All code ready for production

---

## Prerequisites

- Ubuntu 22.04 LTS server OR Windows Server 2022
- Python 3.9+
- Alpaca Markets API account (free tier OK)
- 64GB RAM recommended
- UPS (power resilience)

---

## Step 1: Get Alpaca Credentials

1. Sign up: https://alpaca.markets
2. Get API keys from dashboard
3. Copy to secure location

**Keys needed:**
- `ALPACA_API_KEY`
- `ALPACA_API_SECRET`

---

## Step 2: Deploy on Linux

### 2.1 Clone and prepare

```bash
sudo mkdir -p /opt/flipflop
sudo chown $USER /opt/flipflop
cd /opt/flipflop

# Copy code
git clone <repo> .
cd 04_ENGINE
```

### 2.2 Run bootstrap

```bash
sudo bash bootstrap_production.sh
```

Bootstrap does:
1. Create `flipflop` user (unprivileged)
2. Create directories (data, databases, logs)
3. Install Python dependencies
4. Setup credentials file
5. Install systemd service
6. Enable auto-start
7. Start scheduler

### 2.3 Add credentials

```bash
sudo nano /etc/flipflop/secrets/market-api.env
```

Add:
```
ALPACA_API_KEY=YOUR_KEY_HERE
ALPACA_API_SECRET=YOUR_SECRET_HERE
```

Save and verify permissions:
```bash
sudo chmod 600 /etc/flipflop/secrets/market-api.env
sudo systemctl restart flipflop-scheduler.service
```

---

## Step 3: Deploy on Windows

### 3.1 Prepare

Open PowerShell as Administrator:
```powershell
cd C:\path\to\04_ENGINE
```

### 3.2 Run bootstrap

```powershell
powershell -ExecutionPolicy Bypass -File bootstrap_production.ps1
```

Bootstrap does:
1. Create directories
2. Create Python venv
3. Install dependencies
4. Setup credentials
5. Create scheduled task
6. Start scheduler

### 3.3 Add credentials

Edit: `C:\ProgramData\FlipFlop\secrets\market-api.env`

Add:
```
ALPACA_API_KEY=YOUR_KEY_HERE
ALPACA_API_SECRET=YOUR_SECRET_HERE
```

Restart task:
```powershell
Stop-ScheduledTask -TaskName "FlipFlop-Scheduler"
Start-ScheduledTask -TaskName "FlipFlop-Scheduler"
```

---

## Step 4: Test EOD Download

### 4.1 Set credentials (if not already set)

**Linux:**
```bash
export ALPACA_API_KEY="your_key"
export ALPACA_API_SECRET="your_secret"
```

**Windows (PowerShell):**
```powershell
$env:ALPACA_API_KEY = "your_key"
$env:ALPACA_API_SECRET = "your_secret"
```

### 4.2 Run test

```bash
python3 test_eod_download.py
```

Expected output:
```
============================================================
FlipFlop HQ - EOD Download Test
============================================================
✓ Alpaca credentials found

[1/5] Initializing downloader...
✓ Database directory: databases

[2/5] Downloading EOD data for 20260907...
  NQ: COMPLETE
    - Bars: 391
    - Quality: 0.95
  ES: COMPLETE
    - Bars: 388
    - Quality: 0.94

[3/5] Verifying database...
✓ Database exists: databases/market_data_20260907.db

[4/5] Running health checks...
Overall Status: HEALTHY
  ✓ scheduler_running: Scheduler running
  ✓ database_accessible: 779 bars in database
  ✓ market_data_fresh: Fresh data: 0.1 hours old
  ✓ last_backtest_age: No results database
  ✓ memory_available: 32.4GB free
  ✓ disk_available: 1200.5GB free
  ✓ audit_chain: Audit database not yet created

Authority: ZERO
Live: OFF

✅ EOD Download Test PASSED
============================================================
```

---

## Step 5: Verify Scheduler Running

### Linux

```bash
# Check service status
sudo systemctl status flipflop-scheduler.service

# Follow logs
sudo journalctl -u flipflop-scheduler -f

# Check PID
ps aux | grep scheduler_service.py
```

Expected:
```
● flipflop-scheduler.service - FlipFlop HQ Autonomous Scheduler
     Loaded: loaded (/etc/systemd/system/flipflop-scheduler.service)
     Active: active (running) since Mon 2026-09-08 12:00:00 UTC
```

### Windows

```powershell
# Check task status
Get-ScheduledTask -TaskName "FlipFlop-Scheduler"

# View task info
Get-ScheduledTask -TaskName "FlipFlop-Scheduler" | Get-ScheduledTaskInfo
```

Expected:
```
TaskName                                 State
--------                                 -----
FlipFlop-Scheduler                       Running
```

---

## Step 6: Health Check Endpoints

Start health server:
```bash
python3 health_server.py
```

Test endpoints:

**Simple health:**
```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "HEALTHY",
  "timestamp": "2026-09-08T12:34:56.789012",
  "authority": "ZERO",
  "live": "OFF"
}
```

**Detailed health:**
```bash
curl http://localhost:8080/health/detail
```

**Prometheus metrics:**
```bash
curl http://localhost:8080/metrics
```

---

## Verification Checklist

- [ ] Bootstrap completed without errors
- [ ] Scheduler running (systemd/Task Scheduler)
- [ ] Credentials file configured
- [ ] EOD download test PASSED
- [ ] Market data downloaded (>300 bars)
- [ ] Database file created
- [ ] Health check returns HEALTHY
- [ ] Logs show no errors
- [ ] Memory usage < 4GB
- [ ] Disk usage stable
- [ ] Authority: ZERO confirmed
- [ ] Live: OFF confirmed

---

## Monitoring

**Daily checks:**
```bash
# Health status
curl http://localhost:8080/health

# Last download age
stat /opt/flipflop/databases/market_data_*.db

# Scheduler uptime
sudo systemctl status flipflop-scheduler.service

# Error logs
sudo journalctl -u flipflop-scheduler -p err
```

**Weekly:**
- Verify backup exists
- Check disk usage growth
- Audit trail integrity

---

## Troubleshooting

**Scheduler not starting:**
```bash
# Check logs
sudo journalctl -u flipflop-scheduler -n 50

# Restart
sudo systemctl restart flipflop-scheduler.service
```

**Alpaca connection fails:**
- Verify API keys in `/etc/flipflop/secrets/market-api.env`
- Check network connectivity
- Verify market is open (data only available after 4 PM ET)

**Disk space low:**
- Check: `df -h`
- Delete old databases: `rm /opt/flipflop/databases/market_data_*.db` (keeps only latest)

**Memory pressure:**
- Check: `free -h`
- Restart scheduler if > 8GB used

---

## Week 1 Acceptance Criteria

| Criterion | Status | Test |
|-----------|--------|------|
| Real provider connected | ⏳ | Run test_eod_download.py |
| Durable scheduler | ⏳ | systemctl status shows active |
| Auto-restart working | ⏳ | Kill PID, verify restart < 30s |
| Health check passing | ⏳ | curl /health returns HEALTHY |
| Real EOD downloaded | ⏳ | Database has 300+ bars |
| Freshness verified | ⏳ | Data within 5 min of 4 PM ET |
| No errors in logs | ⏳ | journalctl shows clean startup |
| Authority: ZERO locked | ✅ | Immutable in code |
| Live: OFF locked | ✅ | No broker API configured |

---

## Next: Week 2-4

After verifying Week 1:
1. Idempotent jobs + resumability
2. Deterministic replay + holdout
3. Audit trail (append-only)
4. Dashboard freshness labels
5. Backup + restore
6. Monitoring + alerts
7. Chaos tests

See: `FLIPFLOP_PRODUCTION_SETUP_COMPLETE.md`
