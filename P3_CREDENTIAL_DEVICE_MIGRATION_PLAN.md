# P3 — Credential/Device Migration Plan

**Status:** AUDIT PHASE  
**Date:** 2026-09-11  
**Scope:** Device-bound auth + migration 0002 + root recovery + rollback  

---

## Current State (C:\FLIP_FLOP_HQ)

**Auth:** owner_auth.py
- Password + TOTP (MFA) ✓
- Session tokens (8h timeout) ✓
- No device binding ✗
- No credential rotation ✗
- No root recovery procedure ✗
- No migration framework ✗

**Database:** flip_flop.duckdb (single file)
- No schema versioning ✗
- No migration tracking ✗

---

## What P3 Adds

### 1. Device Binding
- Register device fingerprint (OS, hardware ID, browser hash)
- Bind credentials to device
- Require re-auth on new device (challenge + recovery code)
- Multi-device support (primary + 1-2 backup devices)

### 2. Credential Rotation
- Rotate password every 90 days
- Rotate MFA secret every 180 days
- Generate rotation tokens (for secure rotation without re-login)
- Audit trail: who changed what when

### 3. Root Recovery
- Generate recovery codes (10×) at setup
- One-time use per code
- Skip MFA via recovery code + device verification
- Store encrypted backup of MFA secret (HSM/secure storage)

### 4. Migration Framework (0002)
- Schema versioning: `migrations` table tracks applied migrations
- Migration 0001: baseline (existing auth tables)
- Migration 0002: add device binding + recovery + rotation
- Checksums: verify migration integrity
- Rollback: reverses 0002 → 0001 (backward compatible)

### 5. Rollback Safety
- Transaction-based: all-or-nothing
- Checkpoint before 0002 applied
- Rollback procedure: stop app, run `migration_rollback(2)`, restart
- Pre-rollback validation: no active sessions from new features

---

## Deliverables

### Code (new files)
- `04_ENGINE/migrations/migration_framework.py` — run/rollback system
- `04_ENGINE/migrations/0001_baseline.sql` — existing schema
- `04_ENGINE/migrations/0002_device_bound_auth.sql` — new schema (devices, rotation, recovery)
- `04_ENGINE/device_auth.py` — device binding logic
- `04_ENGINE/credential_rotation.py` — rotation job + scheduler hook
- `04_ENGINE/root_recovery.py` — recovery code generation/validation

### Database
- `03_DATABASE/migrations/` directory (new)
- Updated flip_flop.duckdb schema (migration 0002 applied)
- Audit tables: device_registrations, credential_rotations, recovery_codes

### Tests
- `tests/device_auth.test.py` — device binding (10+ tests)
- `tests/credential_rotation.test.py` — rotation flow (8+ tests)
- `tests/root_recovery.test.py` — recovery codes (8+ tests)
- `tests/migrations.test.py` — migration apply/rollback (10+ tests)

### Docs
- `P3_IMPLEMENTATION.md` — detailed flow
- `P3_MIGRATION_GUIDE.md` — rollback procedure
- `RECOVERY_CODES_SETUP.md` — user guide

---

## Phasing

**Phase A (Audit):** [NOW]
- [x] Find current auth code
- [ ] Map current schema (DuckDB tables)
- [ ] Identify where to bind devices
- [ ] Draft schema for 0002

**Phase B (Migration Framework):** [1 day]
- [ ] Create migration runner
- [ ] Write 0001 (baseline)
- [ ] Write 0002 (device binding)

**Phase C (Device Auth):** [2 days]
- [ ] Device fingerprinting
- [ ] Device registration flow
- [ ] New-device challenge

**Phase D (Rotation + Recovery):** [2 days]
- [ ] Rotation job + scheduling
- [ ] Recovery code generation
- [ ] Recovery validation flow

**Phase E (Testing + Rollback):** [1 day]
- [ ] Unit + integration tests
- [ ] Rollback testing
- [ ] Documentation

**Total:** ~6 days

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Old auth stopped mid-rotation | Atomic transactions; all-or-nothing |
| Device fingerprint unstable (IP changes) | Primary device + recovery codes; optional re-bind |
| Recovery codes leaked | Single-use; rate-limit recovery attempts |
| Rollback fails mid-migration | Transaction checkpoint; manual restore from backup |
| Owner locked out | Recovery codes + root recovery procedure |

---

## Decision Points (For CJ)

1. **Device binding scope:** Require for all logins, or optional second factor?
   - Strict (required): Higher security, may lock owner out
   - Optional: Flexible, lower security barrier

2. **Recovery code count:** 10 codes (standard) or more?
   - 10: balanced (90% one won't be needed)
   - 15+: over-conservative

3. **Rotation frequency:** 90d pass, 180d MFA standard?
   - Can adjust based on policy

4. **Rollback procedure:** Automated or manual?
   - Automated: lower risk of human error
   - Manual: more control, requires documentation

---

## Next Step

Audit current DuckDB schema. Draft 0002 changes. Then propose for approval.

*P3 blocks P4 (evidence retention) and P5 (migration ledger) due to schema dependency.*
