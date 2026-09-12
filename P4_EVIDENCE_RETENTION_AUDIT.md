# P4 Audit: Evidence Retention Gaps

**Date:** 2026-09-11  
**Status:** Audit Complete  
**Finding:** P3 audit tables append-only but NOT cryptographically sealed or retention-enforced

---

## Current State (P3)

**Audit Tables:**
- `auth_audit_log` (6 fields): event_type, owner_id, device_id, ip_address, status, reason, event_at
- `credential_rotations` (9 fields): rotation_type, old_hash_prefix, new_hash_prefix, rotated_at, rotated_by, reason, device_id, ip_address
- `recovery_codes` (9 fields): code_sequence, generated_at, used_at, used_by_device_id, used_by_ip_address, expires_at
- `auth_sessions` (9 fields): session_token_hash, authenticated_at, expires_at, last_activity_at, ip_address, is_active

**Current Properties:**
- ✓ Append-only (INSERT-only design)
- ✓ Indexed (12 indexes for query performance)
- ✓ Timestamped (event_at, rotated_at, generated_at)
- ✗ No cryptographic sealing
- ✗ No immutability enforcement (DuckDB allows UPDATE/DELETE)
- ✗ No retention policies
- ✗ No evidence batch ledger
- ✗ No integrity verification (hash chain)

---

## P4 Gaps Identified

### 1. Tamper Detection
**Problem:** No way to detect if audit log modified post-insert.  
**Impact:** Compliance failure (GDPR/SOC2 require immutable evidence).

### 2. Retention Policy
**Problem:** No mechanism to enforce record expiry or archival.  
**Impact:** Storage bloat, no legal hold, no GDPR "right to be forgotten".

### 3. Batch Sealing
**Problem:** Evidence not cryptographically linked in sequence.  
**Impact:** No proof of evidence integrity over time.

### 4. Export/Compliance
**Problem:** No compliance report generation.  
**Impact:** Manual audit work, no automated SOC2/GDPR validation.

### 5. Hash Chain
**Problem:** Each batch independent; can't verify sequence integrity.  
**Impact:** No detection of deleted/reordered batches.

---

## P4 Solution Design

**New Tables:**
1. `evidence_ledger` — sealed batch registry (sequence, hash chain, signature)
2. `evidence_archival` — archived batches (compressed, signed)
3. `retention_policies` — configurable expiry rules (per event type)

**New Features:**
1. **Batch Sealing:** SHA256(auth_audit_log entries) → batch_hash
2. **Hash Chain:** batch_hash[N] includes SHA256(batch_hash[N-1])
3. **Immutable Export:** signed compliance reports (GDPR/SOC2)
4. **Retention Enforcement:** scheduled archival + deletion per policy
5. **Integrity Verification:** validate_evidence_chain() verifies hash sequence

**Immutability Model:**
- auth_audit_log: true append-only (no UPDATE/DELETE in code)
- evidence_ledger: sealed (one row per batch, never updated)
- retention_policies: admin-only (rarely modified)

---

## Risk Assessment

**Current Risk:** MEDIUM
- Audit log functionally append-only but not enforced at DB level
- No retention policy = storage/compliance risk
- No hash chain = no proof of integrity

**P4 Mitigates:** Full compliance + tamper detection

---

## Next: Phase B (Migration Design)
- 0003_evidence_retention.sql (3 new tables, 5 indexes)
- Evidence batch framework (sealing + verification)
- Retention scheduler (archival trigger)
