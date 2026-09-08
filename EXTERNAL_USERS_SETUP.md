# External Users - Read-Only Access Setup

## Architecture

Three-tier access:
1. **Production Server** (24/7, runs scheduler)
2. **Control PC** (admin, monitoring, writes)
3. **External Users** (read-only, view metrics)

## External User Token

```
TIER_EXTERNAL_READ_TOKEN_SECRET
```

**Permissions**: Read-only
- /health
- /metrics
- /vault/items
- /experiments
- /queue
- /arena
- /guardian/wounds
- /guardian/calibration

**Restrictions**: Cannot
- Submit scripts
- Modify parameters
- Write data
- Access admin endpoints

## Setup External User Access

### Step 1: Distribute Token to User

Send via secure channel (encrypted email, password manager):

```
API Token: TIER_EXTERNAL_READ_TOKEN_SECRET
Server: http://<your-server-ip>:8000
Dashboard: http://<your-server-ip>:54923
```

### Step 2: User Configuration

User adds token to their environment:

```bash
# Linux/Mac
export FLIPFLOP_TOKEN="TIER_EXTERNAL_READ_TOKEN_SECRET"

# Windows PowerShell
$env:FLIPFLOP_TOKEN = "TIER_EXTERNAL_READ_TOKEN_SECRET"
```

Or in dashboard header for each request:

```
Authorization: Bearer TIER_EXTERNAL_READ_TOKEN_SECRET
```

### Step 3: User Tests Access

```bash
curl -H "Authorization: Bearer TIER_EXTERNAL_READ_TOKEN_SECRET" \
  http://<server>:8000/health

# Should return:
{
  "status": "healthy",
  "data_age_seconds": 25,
  "authority": "ZERO",
  "live": "OFF"
}
```

## Dashboard URL for External Users

```
http://<your-server-ip>:54923
```

Features available:
- Overview (Guardian seal, P&L, health)
- Trades (execution log, read-only)
- Performance (equity curve, metrics)
- Calendar (monthly heatmap)
- Agents (monitoring status)
- Arena (competitive strategies)

**Not available**:
- Lab (write-protected)
- Script submission
- Parameter editing
- Guardian adjustments

## Network Access

### Local Network
```
http://192.168.1.100:54923
```

### Remote/Cloud

If exposing externally:

```
1. Configure firewall to allow port 54923 (dashboard) and 8000 (API)
2. Optional: Use reverse proxy (nginx) with HTTPS
3. Add IP allowlist in backend_api.py
```

Example IP allowlist:

```python
ALLOWED_IPS = [
    '192.168.1.0/24',    # Local network
    '203.0.113.0',       # External office IP
]

def check_ip_allowed(request):
    ip = request.remote_addr
    for allowed in ALLOWED_IPS:
        if ip in IPNetwork(allowed):
            return True
    return False
```

## Managing Multiple External Users

### User A (Read-Only Investor)
```
Name: investor@company.com
Token: TIER_EXTERNAL_READ_TOKEN_SECRET
Access: Dashboard only (no API direct)
```

### User B (Research Partner)
```
Name: research@partner.com
Token: TIER_EXTERNAL_READ_TOKEN_SECRET
Access: API + Dashboard
```

### User C (Client)
```
Name: client@external.com
Token: TIER_EXTERNAL_READ_TOKEN_SECRET
Access: Dashboard public link
```

## Revoking Access

### Immediate Revocation
1. Change token in backend_api.py:
```python
TIER_TOKENS = {
    'external_read': 'TIER_EXTERNAL_READ_NEW_TOKEN_SECRET',
}
```

2. Restart backend:
```bash
systemctl restart flipflop-scheduler  # Linux
Restart-ScheduledTask -TaskName "FlipFlop-Scheduler"  # Windows
```

3. Notify user of new token or access revoked

### Revoke Specific User
Create multiple token tiers:

```python
TIER_TOKENS = {
    'external_read': 'TIER_EXTERNAL_READ_TOKEN_SECRET',
    'external_user_a': 'TOKEN_FOR_USER_A_SECRET',
    'external_user_b': 'TOKEN_FOR_USER_B_SECRET',
}
```

## Audit Trail

All API calls logged with:
- Timestamp
- Token tier (user level)
- Endpoint accessed
- Response status
- Data age

View audit:

```bash
tail -f /var/log/flipflop/api.log

# Example:
2026-09-08 10:15:30 TIER_EXTERNAL_READ /health 200 data_age=25s
2026-09-08 10:15:35 TIER_EXTERNAL_READ /metrics 200 trades=42
```

## Example: Invite External User

Email template:

```
Subject: FlipFlop HQ Access - Read-Only Dashboard

Hi [User],

You now have access to FlipFlop HQ's autonomous trading research system.

Dashboard: http://flipflop-hq.company.com:54923

You can view:
- Live P&L and trade metrics
- Guardian gate status
- Performance analytics
- Strategy performance comparison

Authority-ZERO enforcement:
- No live trading capability
- No broker access
- Read-only access
- Audit trail preserved

Questions? Contact: admin@company.com

--
FlipFlop HQ
```

## Security Notes

✅ Token sent via secure channel (never email plain text)
✅ HTTPS recommended for external access
✅ IP allowlist optional but recommended
✅ Token rotation every 90 days recommended
✅ Audit all external API access
✅ Authority-ZERO still enforced (no bypass)
