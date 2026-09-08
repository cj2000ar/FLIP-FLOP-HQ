# FlipFlop V2 Deployment Guide

## Overview

FlipFlop V2 introduces Guardian Package Verification for secure staged deployment. The system ensures all artifacts pass verification before launching, with Authority-ZERO constraints and immutable event logging.

**Exit Code 78** = Guardian verification failure (immutable, fail-closed).

## Architecture

### Components

1. **Guardian Package Verifier** (`guardian_package_verifier.py`)
   - SHA256 hash verification of artifacts
   - Immutable event store (SQLite, append-only)
   - Correlation ID tracking for all verification events

2. **Guardian V2 Launcher** (`guardian_v2_launcher.py`)
   - Staged browser launch with verification gates
   - Exit code 78 on Guardian verification failure
   - Integrates with package verifier

3. **Bootstrap Scripts**
   - `bootstrap_v2.ps1` (Windows PowerShell)
   - `bootstrap_v2.sh` (Linux/macOS)
   - Activate venv and invoke launcher

4. **API Endpoints**
   - `POST /v2/launcher/verify` - Verify artifacts
   - `GET /v2/launcher/events/{correlation_id}` - Retrieve events
   - `GET /v2/launcher/health` - Health status

## Deployment Steps

### 1. Prepare Artifact Manifest

Create `manifest.json` with SHA256 hashes of all artifacts:

```json
{
  "strategy_hash": "abc123def456...",
  "engine_hash": "def456ghi789...",
  "ui_hash": "ghi789jkl012...",
  "passport_hash": "jkl012mno345...",
  "created_at": "2026-09-07T00:00:00"
}
```

### 2. Verify Artifacts Locally

```bash
# Windows PowerShell
.\RED_DRAGON\bootstrap_v2.ps1 -ManifestPath ".\manifest.json"

# Linux/macOS
bash ./RED_DRAGON/bootstrap_v2.sh ./manifest.json
```

On verification failure, script exits with code 78.

### 3. Deploy to Production (DigitalOcean 208.68.36.209)

```bash
# SSH into droplet
ssh root@208.68.36.209

# Verify Guardian health
curl http://localhost:8000/v2/launcher/health

# Verify package through API
curl -X POST http://localhost:8000/v2/launcher/verify \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_hash": "abc123...",
    "engine_hash": "def456...",
    "ui_hash": "ghi789...",
    "passport_hash": "jkl012..."
  }'

# Response (on success):
# {
#   "correlation_id": "uuid",
#   "overall_status": "PASS",
#   "exit_code": 0,
#   "event_count": 4,
#   "events": [...]
# }
```

### 4. Monitor Verification Events

```bash
# Retrieve events by correlation ID
curl http://localhost:8000/v2/launcher/events/{correlation_id}
```

## Authority Constraints

Authority-ZERO is immutable and locked:

```python
authority = AuthorityLevel.ZERO
live_enabled = False
broker_orders_allowed = False
control_mutation_allowed = False
```

No trading orders can be executed; system is evidence-scoped only.

## Immutable Event Store

All verification events are immutable (append-only SQLite table):

- No UPDATE, DELETE operations
- Indexed by correlation_id
- Timestamped (event_time, verified_at)
- Contains full hash payload
- Exit code recorded per event

## Testing

Run V2 launcher test suite:

```bash
python -m pytest test_v2_launcher.py -v
```

All 8 tests verify:
- Event store initialization
- Missing artifact detection (exit code 78)
- Immutability enforcement
- Event logging accuracy
- Launcher initialization
- Authority-ZERO enforcement

## Rollback

If verification fails:

1. Check verification events: `GET /v2/launcher/events/{correlation_id}`
2. Identify artifact causing failure
3. Recompute hash and update manifest
4. Re-run bootstrap with updated manifest

Exit code 78 ensures no partial launches occur.

## Deployment Checklist

- [ ] Manifest created with correct SHA256 hashes
- [ ] All artifacts present at expected paths
- [ ] Local verification passes (exit code 0)
- [ ] API endpoints respond to health check
- [ ] Verification events logged to immutable store
- [ ] Production droplet has Guardian service running
- [ ] Monitor /v2/launcher/events for verification history
- [ ] Authority-ZERO verified (live_enabled=False)

## Integration with Existing Systems

V2 Launcher integrates with:

- **HP Infra** - Machine health/readiness via Gate 4
- **Guardian Engine** - 8-gate enforcement pipeline
- **NinjaTrader Bridge** - Replay only (no live orders)
- **Monitoring Stack** - Prometheus + Grafana
- **Private Read API** - Bitemporal access (evidence-scoped)

## Support

- Verification failures: Check exit code 78 + events log
- Hash mismatches: Recompute artifact hash, update manifest
- Authority escalation attempts: Blocked by AuthorityTuple validation

---

**Authority: ZERO | Exit Code: 78 | Date: 2026-09-07**
