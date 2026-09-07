# NinjaTrader Batch Domain Model — Phase 2 Freeze Complete

**Date:** 2026-09-07  
**Domain Architect:** Frozen Specification  
**Status:** READY FOR IMPLEMENTATION  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**LIVE:** OFF (LOCKED IMMUTABLE)  

---

## Summary

The NinjaTrader Batch domain model is now frozen for Phase 2 implementation. This specification defines an end-of-day batch execution system that integrates Guardian Enforcement verdicts with HP 24/7 Infrastructure durable storage, enabling paper-only analysis and compliance tracking without real order execution.

**Key principle:** Authority=ZERO hard-locked. All data immutable after batch close. Guardian 8-gate verdicts required for batch approval. HP storage required for archive finality.

---

## Deliverables (3 Documents)

### 1. NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json (27 KB)

**Machine-readable entity/relationship graph**

- 7 core entities (BatchRun, DayReport, AlertRecord, ComplianceBundle, TaxDataArchive, ArchiveRecord, BatchVerdict)
- 6 frozen tuples (BatchRunTuple, DayReportTuple, AlertRecordTuple, ComplianceBundleTuple, ArchiveRecordTuple, BatchVerdictTuple)
- Relationships (batch → verdict, batch → report, batch → alerts, batch → compliance, batch → archive)
- 8 constraint gates (CG01-CG08: authority lock, immutability, verdict dependency, etc.)
- Data flow steps (1-8: Guardian verdicts → alert generation → compliance → archive)
- Integration points (Guardian, HP, UI)
- Version control strategy

**Audience:** Developers, architects, database engineers (JSON for programmatic use)

---

### 2. NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md (39 KB)

**Complete technical specification with workflow and constraints**

- Executive Summary (key invariant, Authority=ZERO hard-locked)
- Authority Invariant (non-negotiable fail-closed policy)
- 7 Domain Entities (detailed field descriptions, constraints, lifecycle)
  - BatchRun: end-of-day session container (PENDING → PROCESSING → CLOSED → ARCHIVED)
  - BatchVerdict: final authorization (requires ALL 8 Guardian gates PASS)
  - DayReport: end-of-day summary (trade count, P&L, risk metrics)
  - AlertRecord: trade alerts + anomalies (severity, escalation)
  - ComplianceBundle: tax data + audit trail (certified + locked)
  - TaxDataArchive: regulatory retention lifecycle (7-year minimum)
  - ArchiveRecord: HP durable storage entry (write-once, append-only)
- 6 Frozen Tuples (schemas, examples, immutability constraints)
- Data Flow Diagram (market close → export → alerts → compliance → verdict → archive → closed)
- 8 Constraint Gates (fail-closed enforcement for Authority, immutability, verdict, etc.)
- 3 Integration Points (Guardian verdicts → batch verdict, HP storage → archive, UI dashboard)
- Key Invariants (authority lock, immutability, verdict aggregation logic)
- Archive Retention Lifecycle (ACTIVE → ARCHIVED → PURGED, min 7 years)
- Database Schema Constraints (pseudo-SQL examples)
- Workflow State Transitions (BatchRun, BatchVerdict, ComplianceBundle)
- Phase 2 Timeline (M01-M07, Batch Engine M04: Sep 8-14)
- Onboarding Sequence (for developers, QA, testers)
- Risk Mitigation (R01-R05: Guardian incomplete, unauthorized execution, archive corruption, etc.)
- Version Control (Frozen V1, patch vs. major release strategy)

**Audience:** All stakeholders (technical + business understanding)

---

### 3. NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md (21 KB)

**Executive summary + integration roadmap**

- Overview of 3-document deliverables
- What is frozen (Authority, entities, tuples, gates)
- Batch execution workflow (7-step sequence: creation → processing → verdict → archive → closed → archived)
- 8 Constraint Gates (quick reference table)
- 3 Integration Points (Guardian input/output, HP input/output, UI input/output)
- Key Invariants (authority lock, immutability, verdict logic)
- Batch Lifecycle State Machine (visual)
- Verdict Aggregation Logic (decision table)
- Regulatory Retention Lifecycle (7-year retention, purge enforcement)
- Implementation Lanes (Batch Team M04: Sep 8-14, deliverables, exit criteria, risks)
- Onboarding Sequence (for developers, QA)
- Risk Mitigation Table (R01-R05)
- Version Control strategy
- Sign-off table (roles, responsibilities, TBD owners)

**Audience:** Project managers, technical leads, integration teams

---

## Architecture At a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                    NINJATRADER BATCH                        │
│                    (End-of-Day Workflow)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: Guardian 8-Gate Verdicts (GateDecisionTuple)        │
│         - All 8 gates required for batch approval           │
│         - Any BLOCKED/NOT_PROVEN → batch BLOCKED            │
│                                                             │
│  Process: Batch Lifecycle                                  │
│         1. BatchRun created (PENDING)                       │
│         2. Market close → export (PROCESSING)               │
│         3. Alert generation + compliance checks             │
│         4. Guardian verdict aggregation                     │
│         5. Archive write (if APPROVED)                      │
│         6. Batch close (CLOSED, data immutable)             │
│         7. Archive finalized (ARCHIVED)                     │
│                                                             │
│  Entities:                                                  │
│         - BatchRun (session container)                      │
│         - BatchVerdict (all-or-nothing APPROVED)            │
│         - DayReport (P&L, risk, alerts)                     │
│         - AlertRecord (severity, escalation)                │
│         - ComplianceBundle (tax, receipts, audit trail)     │
│         - TaxDataArchive (7-year retention)                 │
│         - ArchiveRecord (HP durable storage)                │
│                                                             │
│  Authority Invariant: ZERO (hardcoded, no escalation)       │
│  LIVE Status: OFF (paper-only, no real trades)              │
│  Failure Policy: FAIL_CLOSED (all checks must pass)         │
│                                                             │
│  Output: AlertRecordTuple → UI dashboard (read-only)        │
│          DayReportTuple → summary view                      │
│          ArchiveRecordTuple → HP durable storage            │
│          ComplianceBundleTuple → tax filing                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Guardian Enforcement Integration:
  ├─ Input: GateDecisionTuple (8 verdicts)
  ├─ Process: All 8 must PASS for batch APPROVED
  └─ Output: BatchVerdictTuple (aggregated result)

HP 24/7 Infrastructure Integration:
  ├─ Input: MachineRoleTuple (health, heartbeat)
  ├─ Process: Archive write to durable storage
  ├─ Output: ArchiveRecordTuple (storage path + immutable hash)
  └─ Verification: HP receipt required before VERIFIED

UI Control Center Integration:
  ├─ Input: BatchStatusSnapshot
  ├─ Display: Alerts (sorted by severity), Report summary, Guardian gates
  ├─ Authority: ZERO prominently displayed (read-only)
  └─ Constraint: No state changes from UI (immutable batch data)
```

---

## Key Points for Implementation

### 1. Authority Lock (CG01)

**Non-negotiable:** Batch mode must be PAPER/SHADOW/ANALYSIS (never LIVE).
```python
# Hardcoded at batch creation
if batch.mode not in [PAPER, SHADOW, ANALYSIS]:
    raise InvalidBatchMode()
    
# Hardcoded at verdict issuance
if verdict.authority_used != ZERO:
    verdict.batch_status = BLOCKED
```

### 2. Verdict Aggregation (CG03)

**All-or-nothing:** APPROVED only if ALL 8 Guardian gates PASS AND compliance_passed AND tax_verified AND archive_verified.
```python
batch_approved = (
    len(guardian_gate_results) == 8 and
    all(gate.verdict == PASS for gate in guardian_gate_results) and
    compliance_passed and tax_verified and archive_verified
)
```

### 3. Immutability After Close (CG02, CG05, CG06)

**Write-once:** After closed_at is set, no updates allowed. ArchiveRecord INSERT only (no UPDATE/DELETE).
```python
if batch.closed_at is not None:
    if attempt_to_update_batch_data():
        raise ImmutabilityViolation()
```

### 4. Guardian Gate Requirement (CG04)

**Mandatory:** All 8 Guardian gates must complete before batch verdict issuance.
```python
if len(verdict.guardian_gate_results) != 8:
    raise required_verdict_missing()
```

### 5. Archive Retention (CG08)

**Regulatory enforcement:** No purge before retention_until date (minimum 7 years).
```python
if today < retention_until:
    raise retention_not_met()
```

---

## Integration Checklist (Before Implementation)

### Guardian Integration
- [ ] Understand GateDecisionTuple schema (8 tuples, one per gate)
- [ ] Implement verdict aggregation logic (all 8 must PASS for APPROVED)
- [ ] Verify Authority=ZERO propagates from Guardian verdicts
- [ ] Timeout logic: if any gate NOT_PROVEN > 5 min, escalate to BLOCKED
- [ ] Test: all gates PASS → batch APPROVED ✓
- [ ] Test: any gate BLOCKED → batch BLOCKED ✓
- [ ] Test: any gate NOT_PROVEN → batch NOT_PROVEN ✓

### HP Integration
- [ ] Understand DurableReceiptTuple schema (receipt_id, timestamp, confirmation_hash)
- [ ] Implement archive write coordination (storage_path, immutable_hash)
- [ ] Verify HP receipt is received before ArchiveRecord.status = VERIFIED
- [ ] Implement write-once enforcement (no UPDATE/DELETE on ArchiveRecord)
- [ ] Test: archive write successful → HP receipt received ✓
- [ ] Test: archive status updates to VERIFIED ✓
- [ ] Test: attempt to UPDATE/DELETE ArchiveRecord → write_once_violation ✓

### Compliance Bundle
- [ ] Implement tax_summary structure (gains, losses, wash_sales, adjustments, total_taxable_income)
- [ ] Implement receipt_hashes array (SHA256 of all receipts)
- [ ] Implement audit_trail array (append-only log)
- [ ] Implement certification locking (no updates after certified_at)
- [ ] Test: bundle certification marks immutability ✓
- [ ] Test: attempt to update tax_summary after cert → immutability_violation ✓

### Data Immutability
- [ ] Implement closed_at timestamp (marks batch immutability)
- [ ] Implement database trigger: after closed_at, block all updates
- [ ] Test: update batch data after close → immutability_violation ✓
- [ ] Test: update compliance bundle after cert → immutability_violation ✓
- [ ] Test: update/delete archive record → write_once_violation ✓

---

## File Locations (Final)

```
C:\FLIP_FLOP_HQ\
├── NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json          (27 KB)
├── NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md              (39 KB)
├── NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md         (21 KB)
│
├── GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json                    (existing)
├── GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md                       (existing)
├── GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md                   (existing)
├── GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md           (existing)
└── GUARDIAN_PHASE2_FROZEN_DELIVERABLES.md                  (existing)
```

---

## Next Steps (M04: Sep 8-14)

### Batch Engine Team

1. **Review** (Day 1-2)
   - Read NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md (Executive Summary → Authority Invariant)
   - Review JSON model for entity/relationship structure
   - Understand workflow state machine (7 steps)
   - Understand constraint gates (CG01-CG08)

2. **Design** (Day 3-4)
   - Database schema design (validate against pseudo-SQL constraints)
   - API design for batch lifecycle endpoints
   - Guardian integration points (verdict aggregation)
   - HP integration points (archive writes)

3. **Implement** (Day 5-8)
   - Batch lifecycle state machine (PENDING → PROCESSING → CLOSED → ARCHIVED)
   - Guardian verdict aggregation (all 8 gates → batch verdict)
   - Compliance bundle certification (tax data locking)
   - Archive write coordination (HP durable storage)
   - Constraint gate enforcement (CG01-CG08)
   - Alert generation + escalation

4. **Test & Verify** (Day 9-10)
   - Guardian integration (all 8 gates PASS → APPROVED)
   - HP integration (archive write → receipt verification)
   - Authority=ZERO locked throughout
   - Data immutable after batch close
   - All 8 constraint gates enforced
   - Compliance bundle certification immutability
   - Archive write-once enforcement

5. **Sign-Off** (Day 11-14)
   - Code review (frozen invariants vs. implementation)
   - QA sign-off (all tests passed)
   - Technical reviewer sign-off (model adherence)

---

## Authority Invariant — Non-Negotiable

```
BATCH MODE:        PAPER, SHADOW, or ANALYSIS (never LIVE)
AUTHORITY:         ZERO (no escalation ever)
BROKER ORDERS:     NONE (no real order execution)
LIVE TRADING:      OFF (paper-only, analysis only)
FAILURE POLICY:    FAIL_CLOSED (all checks must pass)
```

**Verification at every stage:**
- Batch creation: `if mode != PAPER/SHADOW/ANALYSIS → reject`
- Verdict issuance: `if authority != ZERO → BLOCKED`
- Before archive: `if live_enabled or broker_orders → reject`

**Hardcoded, no conditionals, no fallback paths.**

---

## Document Status

| Document | Version | Status | Created |
|----------|---------|--------|---------|
| NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json | V1 | FROZEN | 2026-09-07 |
| NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md | V1 | FROZEN | 2026-09-07 |
| NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md | V1 | FROZEN | 2026-09-07 |

---

## Relationship to Guardian Enforcement

**Guardian provides:** 8-gate verdicts (GateDecisionTuple)
- Gate 1: Schema and Identity validation
- Gate 2: Hash Integrity check
- Gate 3: Authority Policy Compliance (ZERO hardcoded)
- Gate 4: Machine Health and Readiness
- Gate 5: Canary Execution verification
- Gate 6: Evidence Consistency check
- Gate 7: Freshness and Staleness validation
- Gate 8: Final Arbiter (all gates pass?)

**Batch consumes:** Guardian verdicts → BatchVerdict (all 8 required for APPROVED)

**Batch provides:** Approval/blocking signal (no escalation, fail-closed)

---

## Relationship to HP 24/7 Infrastructure

**HP provides:**
- Machine health reports (heartbeat, clock offset, restart detection)
- Durable storage acceptance (write confirmation)
- Retention support (7-year minimum)

**Batch consumes:** HP health + storage receipt

**Batch provides:**
- ArchiveRecordTuple to HP durable storage (write-once)
- Immutable hash seal (integrity verification)
- Retrieval metadata (format, size, dates)

---

## Success Criteria (M04 End, Sep 14)

- [ ] All 7 entities implemented with frozen fields/constraints
- [ ] All 6 tuples immutable and hashable
- [ ] Batch lifecycle state machine fully functional
- [ ] Guardian verdict aggregation (all 8 gates required)
- [ ] BatchVerdict logic: APPROVED only if ALL conditions met
- [ ] All 8 constraint gates (CG01-CG08) enforced
- [ ] Authority=ZERO hard-locked throughout
- [ ] Compliance bundle certification marks immutability
- [ ] Archive write-once enforcement (no UPDATE/DELETE)
- [ ] HP receipt verification before archive VERIFIED
- [ ] Tax archive retention enforcement (min 7 years, no purge before date)
- [ ] All batch data immutable after closed_at
- [ ] Guardian integration tested (all 8 gates PASS → APPROVED)
- [ ] HP integration tested (archive write → receipt → VERIFIED)
- [ ] UI dashboard displays alerts (read-only), report summary, gates
- [ ] All tests passed (100% of test cases)
- [ ] Code review: frozen invariants verified
- [ ] QA sign-off: all constraint gates verified

---

## Contact & Escalation

**Domain Architect (Specification Owner):**
- All specification questions → refer to frozen documents
- Interpretation clarifications → contact architect
- Authority invariant changes → Owner approval + Architect review (unlikely)

**Batch Team Lead (Implementation Owner):**
- Development questions → Batch team
- Integration issues (Guardian/HP) → coordinate with Guardian/HP teams
- Code review → Technical reviewer + Domain Architect

**Guardian Lead (Integration Partner):**
- GateDecisionTuple schema → Guardian team
- Verdict timing → Guardian team

**HP Lead (Integration Partner):**
- DurableReceiptTuple schema → HP team
- Storage acceptance → HP team
- Retention policies → HP team

---

**NinjaTrader Batch Domain Model: FROZEN AND LOCKED**

**Authority Invariant:** ZERO (immutable)  
**Failure Policy:** FAIL_CLOSED  
**Integration:** Guardian Enforcement (8-gate verdict aggregation)  
**Integration:** HP 24/7 Infrastructure (durable storage + retention)  
**Implementation Start:** 2026-09-08 (M04: Sep 8-14)  

---

**READY FOR IMPLEMENTATION**
