# P5 Audit: Migration Ledger Gaps

**Date:** 2026-09-11  
**Status:** Audit Complete  
**Finding:** Current migration tracking insufficient for production idempotency + audit trail

---

## Current State (P3/P4)

**Tracking:**
- `migrations` table (1 row per migration): id, migration_number, name, applied_at, status, checksum
- Status values: APPLIED, ROLLED_BACK
- Checksum: SHA256 of migration SQL file
- Transactions: all-or-nothing (apply/rollback)

**Current Behavior:**
- `apply_migration()`: checks if migration_number exists, skips if found, fails on re-apply
- `rollback_migration()`: updates status to ROLLED_BACK, reverse SQL via _rollback.sql
- `status()`: reports applied, available, pending, latest_applied
- `get_migration_status()`: reads current status from migrations table

**Current Properties:**
- ✓ Transactional (ACID)
- ✓ Checksum verified (SHA256)
- ✓ Sequence tracked (migration_number)
- ✓ Status recorded (APPLIED/ROLLED_BACK)
- ✗ No audit trail (only current state)
- ✗ Not idempotent (skips re-apply)
- ✗ No error tracking (failed attempts lost)
- ✗ No state machine (only 2 states)
- ✗ No concurrency control (no locking)
- ✗ No dependency enforcement
- ✗ No recovery procedures

---

## P5 Gaps Identified

### 1. Audit Trail Missing
**Problem:** Only current status stored. No history of apply/rollback/failed attempts.  
**Impact:** Can't investigate past migration failures, audit trail incomplete.

### 2. Not Idempotent
**Problem:** Re-applying same migration skips silently.  
**Impact:** Can't safely re-run migrations (deployment scripts may retry).

### 3. Error State Lost
**Problem:** Failed migrations not tracked (exception raised, state lost).  
**Impact:** Can't distinguish "never attempted" from "attempted but failed".

### 4. State Machine Incomplete
**Problem:** Only APPLIED/ROLLED_BACK. No PENDING, APPLYING, FAILED, LOCKED states.  
**Impact:** Can't track in-progress migrations or error recovery.

### 5. Concurrency Unsafe
**Problem:** No locking. Multiple processes could apply same migration concurrently.  
**Impact:** Race condition: both try to apply, one succeeds (updates status), other fails.

### 6. Dependency Enforcement Missing
**Problem:** apply_all_pending() doesn't validate sequence.  
**Impact:** Migrations could be applied out of order (schema breaks).

### 7. Recovery Procedures Absent
**Problem:** No way to detect/fix orphaned states (e.g., migration applied but status not recorded).  
**Impact:** Can't recover from partial failures.

---

## P5 Solution Design

**New Tables:**
1. `migration_ledger` — immutable audit trail (all apply/rollback/error attempts)
2. `migration_state` — current atomic state (one row per migration, locked during apply)

**New Features:**
1. **Audit Trail:** every apply/rollback/error logged (ledger_id, migration_number, action, status, reason, timestamp)
2. **Idempotent Apply:** re-apply skips (current state checked), or re-verifies + commits
3. **State Machine:** PENDING → APPLYING → APPLIED (or FAILED/ROLLED_BACK)
4. **Error Recovery:** FAILED state trackable, reason stored, allows retry
5. **Concurrency Lock:** migration_state.locked during apply (exclusive lock)
6. **Dependency Check:** validate migrations applied in sequence (0001 before 0002 before 0003)
7. **Checksum Validation:** verify file checksum matches stored checksum (detect tampering)
8. **Recovery Procedures:** detect orphaned states (applied but not recorded), fix atomically

**State Machine:**
```
PENDING (0001) → APPLYING → APPLIED (checksum stored)
                     ↓
                   FAILED (reason stored, allows retry)
                   
APPLIED → ROLLING_BACK → ROLLED_BACK (marked with rollback_reason)
```

**Idempotent Apply:**
- Check migration_state
- If APPLIED + checksum matches: return success (already applied)
- If APPLIED + checksum differs: fail (file was modified)
- If PENDING or FAILED: attempt apply, record attempt in ledger
- Lock migration during apply (exclusive, released on success/failure)

---

## Risk Assessment

**Current Risk:** MEDIUM
- No audit trail = compliance/investigation gap
- Not idempotent = deployment retry risk
- No error tracking = recovery impossible
- No concurrency control = race condition risk
- No dependency enforcement = schema sequence risk

**P5 Mitigates:** Full audit + idempotent + recoverable

---

## Next: Phase B (Migration Design)
- migration_ledger table (immutable audit trail)
- migration_state table (atomic state with lock)
- State machine enforcement (PENDING → APPLYING → APPLIED)
- Idempotent apply logic + error recovery
