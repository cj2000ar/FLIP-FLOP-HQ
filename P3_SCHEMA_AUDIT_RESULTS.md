# P3 Schema Audit — Results & Findings

**Date:** 2026-09-11  
**DB:** flip_flop.duckdb (13 MB, DuckDB v64)  
**Auth Code:** 04_ENGINE/owner_auth.py  

---

## Current Auth Structure

**In-Memory Sessions Only**
- owner_auth.py stores sessions in `self.sessions` dict
- No persistent credential storage (TODOs at lines 171, 176)
- MFA secret / password loaded from "secure config" (not implemented)
- Audit log goes to logger, not database

**Password Hashing**
- PBKDF2(SHA256, salt, 100000 iterations)
- Salt stored alongside hash

**MFA**
- TOTP (RFC 6238, pyotp library)
- 30-second time window, ±1 drift allowed
- No backup secret stored

**Sessions**
- Random urlsafe tokens (32 bytes)
- 8-hour timeout
- No device binding
- IP address tracked but only logged (not enforced)

---

## Missing for P3

| Feature | Current | Needed |
|---|---|---|
| Device binding | ✗ | device_registrations table + fingerprint logic |
| Device list | ✗ | UI to show registered devices |
| New device challenge | ✗ | Require recovery code or MFA for new device |
| Credential rotation | ✗ | credential_rotations table + scheduler hook |
| Recovery codes | ✗ | recovery_codes table + 1-time use logic |
| Persistent sessions | ✗ | auth_sessions table + audit trail |
| Audit log (DB) | ✗ | auth_audit_log table |
| MFA secret backup | ✗ | mfa_secret_backup_encrypted column |

---

## Migration 0002 Schema (Created)

**New Tables (8 total):**
1. `migrations` — track applied migrations (checksum-verified)
2. `owner_credentials` — persistent owner creds (password + MFA secret)
3. `device_registrations` — device fingerprints, 1 primary per owner
4. `credential_rotations` — audit trail of all rotations
5. `recovery_codes` — 10 one-time codes per owner
6. `auth_sessions` — persistent session records
7. `auth_audit_log` — immutable audit trail
8. Indexes (7×) for performance

**Key Design Decisions:**
- Credentials stored with expiration (password 90d, MFA 180d)
- Device fingerprint = hash(OS + HW ID + browser)
- Recovery codes: single-use, indexed by owner
- Sessions: device-bound, auto-expire at 8h
- Audit: immutable, every event logged

---

## Compatibility & Risk

**Backward Compatible:** ✓
- No existing tables modified
- New tables are additions only
- Existing owner_auth.py code still works with in-memory sessions
- 0002 can be applied without downtime

**Risk Level:** LOW
- Transaction-based apply
- Rollback restores by dropping 0002 tables only
- No data loss on rollback

---

## Next Steps

1. **Migration Framework** — runner to apply/rollback migrations
2. **Device Binding Logic** — fingerprinting + challenge flow
3. **Rotation Job** — scheduled task to rotate expiring creds
4. **Recovery Flow** — use recovery code to unlock account
5. **Tests** — apply 0002, verify structure, rollback verify

---

## Questions for CJ (P3 decisions)

1. **Device fingerprint scope:** What level of detail (OS only, or full browser+HW combo)?
2. **Primary device enforcement:** Require re-setup of primary if lost?
3. **Rotation scheduler:** Run at fixed time (2 AM?) or per-user scheduled?
4. **Recovery code scope:** Global (any device) or device-specific?

---

*Migration 0002 schema SQL ready in `P3_MIGRATION_0002_SCHEMA.sql`*
