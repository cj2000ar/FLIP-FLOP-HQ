# FlipFlop HQ Private Read API - Deployment Guide

## Overview

Process Manager setup for production-ready API deployment with auto-restart, health checks, and monitoring.

## Options

### Option 1: Docker (Recommended for Production)

Uses Docker container with automatic health checks and restart policy.

**Requirements:** Docker & docker-compose installed

**Setup:**
```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f private-read-api

# Stop
docker-compose down
```

**Features:**
- Auto-restart on crash (`restart: unless-stopped`)
- Health check every 30s (GET /health)
- JSON logging with rotation (100MB max, 3 files)
- Isolated network
- Resource monitoring

### Option 2: Windows PowerShell (Development)

Uses PowerShell script with background job monitoring and health checks.

**Setup:**
```powershell
# Run with defaults (port 8000)
powershell -ExecutionPolicy Bypass -File start_api.ps1

# Or with custom port
powershell -ExecutionPolicy Bypass -File start_api.ps1 -Port 9000
```

**Features:**
- Auto-restart on process crash (5s delay)
- HTTP health check every 30s (GET /health)
- Logs to `api.log`
- Graceful shutdown on Ctrl+C

**Parameters:**
- `-Port`: API port (default: 8000)
- `-Host`: Bind host (default: 127.0.0.1)
- `-LogFile`: Log file path (default: api.log)
- `-RestartDelaySeconds`: Delay before restart (default: 5)
- `-HealthCheckIntervalSeconds`: Health check interval (default: 30)

### Option 3: Linux systemd (Production)

Uses systemd service with auto-restart and journal logging.

**Setup:**
```bash
# Copy service file
sudo cp flipflop-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Start service
sudo systemctl start flipflop-api

# Enable auto-start on boot
sudo systemctl enable flipflop-api

# Check status
sudo systemctl status flipflop-api

# View logs
sudo journalctl -u flipflop-api -f
```

**Features:**
- Auto-restart on crash (5s delay)
- Journal logging (structured, queryable)
- Security: isolated filesystem, read-only root, no new privileges
- Resource limits: 65536 file descriptors, 512 processes
- Automatic startup on boot

**User Setup:**
```bash
# Create flipflop user (if not exists)
sudo useradd -m -s /bin/bash -d /home/flipflop flipflop

# Create API directory
sudo mkdir -p /opt/flipflop/api/logs
sudo chown -R flipflop:flipflop /opt/flipflop/api
```

## Health Check

All options include automatic health checks via GET /health:

```bash
curl http://localhost:8000/health
# Returns: {"status":"healthy","service":"Private Read API",...}
```

## Token Management

### Issue Test Token (Dev/Test)

```bash
curl -X POST "http://localhost:8000/dev/issue-token?machine_id=test-machine"
# Returns: {"token":"...", "expires_in_seconds":86400, ...}
```

### Use Token

```bash
curl -H "Machine-ID: test-machine" \
     -H "Fencing-Token: <token>" \
     http://localhost:8000/vault/families
```

## Monitoring

### Docker
```bash
# Real-time stats
docker stats flipflop-api

# Logs
docker logs -f flipflop-api
```

### PowerShell
Check `api.log` file for activity and errors.

### systemd
```bash
# Real-time logs
journalctl -u flipflop-api -f

# Last 50 lines
journalctl -u flipflop-api -n 50
```

## Production Checklist

- [ ] Secrets: Use HP /validate_fencing_token (remove /dev/issue-token endpoint)
- [ ] HTTPS: Deploy behind nginx reverse proxy with TLS
- [ ] Logging: Centralize logs to file-based system or cloud
- [ ] Backups: Schedule SQLite backups (if data persistence added)
- [ ] Monitoring: Set up alerts on health check failures
- [ ] Load Testing: Verify performance under expected traffic

## Troubleshooting

### API won't start
- Check port 8000 is available: `netstat -ano | findstr :8000`
- Check Python/uvicorn installed: `pip list | grep uvicorn`
- Review logs for startup errors

### Health check failing
- Verify API is responding: `curl http://localhost:8000/health`
- Check network connectivity if remote
- Review API logs for exceptions

### Token validation issues
- Ensure Machine-ID and Fencing-Token headers present
- Check token hasn't expired (24h TTL)
- Verify machine_id matches token's machine_id
- Use /dev/issue-token to generate new test token

## Next Steps

1. **HTTPS/TLS**: Deploy behind nginx for reverse proxy + SSL termination
2. **Centralized Logging**: Export logs to file system or cloud service
3. **Backups**: Implement automated backup strategy
4. **HP Integration**: Replace /dev/issue-token with HP /validate_fencing_token
5. **Monitoring**: Set up Prometheus/Grafana or CloudWatch
