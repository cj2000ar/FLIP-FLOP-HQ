# P6 Audit: Schema Versioning + Migrations-As-Code

**Date:** 2026-09-11  
**Status:** Audit Starting  
**Scope:** Enhance migration system with schema tracking and automated diffing

---

## Current State (P3/P4/P5)

**Migration System:**
- migration_framework.py: apply/rollback/status CLI
- Migrations numbered (0001, 0002, 0003, 0004)
- SQL files in 04_ENGINE/migrations/
- migration_ledger.py: audit trail, idempotent apply, state machine (P5)

**Tracking:**
- migrations table: tracks applied migrations (number, name, status, checksum)
- migration_ledger: audit trail of all attempts
- migration_state: current state machine

**Limitations:**
- No schema snapshots (can't compare current vs expected)
- No automated schema diffing
- No schema validation (tables/indexes/constraints)
- No rollback simulation (can't preview rollback impact)
- No dependency graph visualization
- No schema change documentation generation

---

## P6 Gaps Identified

### 1. No Schema Snapshots
**Problem:** Can't verify database schema matches migration expectations  
**Impact:** Silent schema drift (manual changes, corrupt state)

### 2. No Schema Diffing
**Problem:** Can't automatically detect schema divergence  
**Impact:** Can't catch when prod schema != expected

### 3. No Migration Reversibility Preview
**Problem:** Can't know what rollback will do before executing  
**Impact:** Risky rollbacks (data loss, downtime)

### 4. No Schema Documentation
**Problem:** No automatically generated schema docs  
**Impact:** Manual doc maintenance, outdated specs

### 5. No Constraint Tracking
**Problem:** Primary keys, foreign keys, unique constraints not tracked in migration ledger  
**Impact:** Can't audit constraint changes

---

## P6 Solution Design

**New Components:**
1. `schema_snapshot.py` — capture current schema (tables, columns, indexes, constraints)
2. `schema_validator.py` — verify actual vs expected schema
3. `schema_differ.py` — generate human-readable diffs
4. `schema_0001.py` through `schema_0004.py` — schema-as-code (ORM-style definitions)
5. `migration_reversal_simulator.py` — preview rollback impact

**New Features:**
1. **Schema snapshots:** JSON snapshots of schema after each migration
2. **Schema validation:** verify DB matches expected (pre/post-migration)
3. **Schema diffs:** readable diffs between versions
4. **Migration reversibility:** simulate rollback, show data impact
5. **Constraint tracking:** all constraints in ledger
6. **Auto-docs:** generate schema markdown from migrations

---

## Risk Assessment

**Current Risk:** MEDIUM
- Schema drift undetected (manual changes slip in)
- Rollback impact unknown (risky blind reversals)
- Schema validation manual (error-prone)

**P6 Mitigates:** Auto-detection + validation + preview

---

## Next: Phase B (Schema-As-Code Framework)

- Define schema capture format (JSON schema spec)
- Implement schema_snapshot.py (introspect DB)
- Implement schema_validator.py (verify actual vs expected)
- Build schema 0001-0004 (as-code definitions)
