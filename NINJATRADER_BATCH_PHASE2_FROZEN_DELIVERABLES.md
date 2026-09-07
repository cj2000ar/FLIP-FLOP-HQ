# NinjaTrader Batch Phase 2 — Frozen Domain Model Deliverables

**Freeze Date:** 2026-09-07  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**Phase Status:** M01 COMPLETE  
**Implementation Start:** 2026-09-08  

---

## Deliverables Overview

Two comprehensive documents freeze the NinjaTrader Batch domain model for Phase 2 implementation:

1. **NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json** — Structured entity/relationship graph
2. **NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md** — Complete specification with workflow and integrations

---

## File Locations

| File | Location | Purpose | Audience |
|------|----------|---------|----------|
| NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json | `/C/FLIP_FLOP_HQ/` | Canonical entity/relationship graph (machine-readable) | Developers, Architects |
| NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md | `/C/FLIP_FLOP_HQ/` | Complete specification with constraints and examples | All stakeholders |

---

## What Is Frozen (Immutable)

### Authority Invariant (Hard-Locked)

```
AUTHORITY = ZERO (no escalation ever)
LIVE = OFF (paper-only, no real orders)
BROKER_ORDERS = NONE (no broker execution)
CONTROL_MUTATION = NONE (batch data immutable after close)
FAILURE_POLICY = FAIL_CLOSED (stale/missing/contradictory blocks)
```

**Status:** Cannot change. Every implementation must verify this invariant at batch initialization, verdict issuance, and archive finalization.

---

## Seven Core Entities

1. **BatchRun** — End-of-day batch execution session (market close → NinjaTrader export → alerts → summary → archive)
2. **BatchVerdict** — Final authorization verdict (aggregates Guardian 8-gate verdicts + compliance + tax + archive)
3. **DayReport** — End-of-day summary report (trade count, P&L, risk metrics, alert counts)
4. **AlertRecord** — Trade alert or anomaly detection (severity, type, escalation)
5. **ComplianceBundle** — Immutable compliance package (tax summary, receipt hashes, audit trail)
6. **TaxDataArchive** — Write-once tax data archive (regulatory retention lifecycle)
7. **ArchiveRecord** — Immutable archive entry in HP durable storage (read-only retrieval only)

**All entities:**
- Immutable core fields (no update path for content-bearing data)
- Audit-only append semantics (new records, no erasure)
- Hard constraints (database schema + ORM validation)

---

## Six Frozen Tuples

1. **BatchRunTuple** — (batch_id, run_date, market_open_time, market_close_time, mode, correlation_id)
2. **DayReportTuple** — (report_id, batch_id, trade_count, pnl_summary, risk_metrics, alert_count, export_time)
3. **AlertRecordTuple** — (alert_id, batch_id, severity, alert_type, message, timestamp, escalation_flag)
4. **ComplianceBundleTuple** — (bundle_id, batch_id, tax_summary, receipt_hashes, audit_trail, certification_time)
5. **ArchiveRecordTuple** — (archive_record_id, batch_id, storage_path, retention_years, immutable_hash, retrieval_metadata)
6. **BatchVerdictTuple** — (verdict_id, batch_id, guardian_gate_results, compliance_passed, tax_verified, archive_verified, batch_status)

**All tuples:**
- Content immutable (no updates to history)
- Timestamped (event_time, knowledge_time, recorded_at)
- Hashable (evidence_root_hash, policy_root_hash)

---

## Batch Execution Workflow

### End-of-Day Sequence

```
STEP 1: Batch Creation (PENDING)
  - BatchRun created with batch_id, run_date, mode (PAPER/SHADOW/ANALYSIS)
  - correlation_id links to Guardian deployment candidate
  - Authority=ZERO verified at creation

STEP 2: Market Close Triggered (PROCESSING)
  - BatchRun transitions to PROCESSING status
  - NinjaTrader export begins

STEP 3: Data Aggregation
  - DayReport created: trade_count, pnl_summary, risk_metrics
  - AlertRecord array generated: risk limits, compliance flags, anomalies
  - ComplianceBundle created: tax_summary, receipt_hashes, audit_trail

STEP 4: Guardian Verdict Aggregation
  - BatchVerdict receives GateDecisionTuple from all 8 Guardian gates
  - Verdict logic:
    * APPROVED = ALL gates PASS + compliance_passed + tax_verified + archive_verified
    * BLOCKED = ANY gate BLOCKED or verification failed
    * NOT_PROVEN = ANY gate NOT_PROVEN

STEP 5: Archive Write (if APPROVED)
  - ComplianceBundle certified (immutable lock)
  - ArchiveRecord created for HP durable storage
  - storage_path immutable (write-once)
  - immutable_hash seals integrity
  - HP receipt required before verification

STEP 6: Batch Closure (CLOSED)
  - closed_at timestamp set (marks immutability)
  - All batch data now read-only
  - No further mutations allowed

STEP 7: Archive Finalization (ARCHIVED)
  - ArchiveRecord status = VERIFIED (HP receipt confirmed)
  - TaxDataArchive retention lifecycle active
  - Retention period enforced (no purge before retention_until)
```

---

## Eight Constraint Gates (Fail-Closed)

| ID | Constraint | Enforcement | Consequence |
|----|------------|-------------|-------------|
| **CG01** | NO_AUTHORITY_ESCALATION | Authority must be ZERO throughout | BLOCKED if authority≠ZERO detected |
| **CG02** | BATCH_DATA_IMMUTABLE_AFTER_CLOSE | No updates after closed_at | immutability_violation error |
| **CG03** | VERDICT_REQUIRES_ALL_GATES_PASS | APPROVED only if ALL conditions met | BLOCKED if ANY gate BLOCKED/NOT_PROVEN |
| **CG04** | GUARDIAN_GATES_MUST_COMPLETE | All 8 gates required before close | required_verdict_missing error |
| **CG05** | COMPLIANCE_LOCK | No updates after certification | immutability_violation error |
| **CG06** | ARCHIVE_WRITE_ONCE | ArchiveRecord INSERT only | write_once_violation error |
| **CG07** | HP_DURABLE_RECEIPT | Receipt required before VERIFIED | missing_receipt error |
| **CG08** | RETENTION_ENFORCED | No purge before retention_until | retention_not_met error |

---

## Three Integration Points

### Integration 1: Guardian Enforcement Domain

**Input to Batch:**
- `GateDecisionTuple` (8 verdicts from Guardian gates 1-8)
  - Each tuple: gate_id, verdict (PASS|BLOCKED|NOT_PROVEN), evidence_id, event_time, knowledge_time
  - All 8 must be received before batch verdict issuance
  - Any gate BLOCKED/NOT_PROVEN blocks batch approval

**Output from Batch:**
- `BatchVerdictTuple` (final verdict for batch execution)
  - Aggregates all 8 guardian_gate_results
  - Includes compliance_passed, tax_verified, archive_verified
  - Status: APPROVED|BLOCKED|NOT_PROVEN

**Constraints:**
- Batch cannot execute without APPROVED verdict
- Authority=ZERO must be verified across all gate results
- No conditional escalation paths
- Stale/missing/contradictory evidence in any gate → BLOCKED

**Example Integration:**
```
Guardian Gate 1 → PASS (schema + identity valid)
Guardian Gate 2 → PASS (hash integrity verified)
Guardian Gate 3 → PASS (authority = ZERO confirmed)
Guardian Gate 4 → PASS (machine health + heartbeat fresh)
Guardian Gate 5 → PASS (canary execution successful)
Guardian Gate 6 → PASS (evidence consistent, no contradictions)
Guardian Gate 7 → PASS (all evidence fresh, < 300s old)
Guardian Gate 8 → PASS (final arbiter: all gates pass, authority ZERO)

Result:
BatchVerdict.batch_status = APPROVED
Batch proceeds to archive write
```

---

### Integration 2: HP 24/7 Infrastructure Domain

**Input to Batch:**
- `MachineRoleTuple` (health, heartbeat, truth_age from HP machines)
  - Used by Guardian Gate 4 (Machine Health and Readiness)
  - Heartbeat < 60 seconds (fresh)
  - Clock skew < 5 seconds
  - Fencing token not expired
  - Restart/sleep/clock-jump detection
- `DurableReceiptTuple` (storage confirmation from HP durable storage)
  - Confirms ArchiveRecord write completed
  - HP receipt: receipt_id, timestamp, confirmation_hash

**Output from Batch:**
- `ArchiveRecordTuple` (immutable storage record)
  - storage_path: `/durable/{run_date}/batch-{batch_id}.tar.gz`
  - immutable_hash: SHA256 of archived data
  - retrieval_metadata: format, size_bytes, created_date, archived_date
  - hp_receipt: confirmation from HP durable storage

**Constraints:**
- Archive must be accepted by HP durable storage before batch closes
- Write-once to HP: no modifications/deletions allowed
- HP receipt required before ArchiveRecord.archive_status = VERIFIED
- Storage path immutable (cannot be updated)
- No manual override of archive verification

**Example Integration:**
```
ComplianceBundle certified (tax_summary + receipt_hashes locked)
↓
ArchiveRecord created (storage_path immutable)
↓
HP Durable Storage receives write request
↓
HP confirms: DurableReceiptTuple received
  {receipt_id: uuid, timestamp: 2026-09-07T20:45:00Z, confirmation_hash: sha256...}
↓
ArchiveRecord.archive_status = VERIFIED
↓
BatchRun.closed_at set (batch now immutable)
```

---

### Integration 3: UI Control Center Domain

**Input to Batch:**
- UI reads BatchStatusSnapshot
  - Batch ID, verdict status (APPROVED|BLOCKED|NOT_PROVEN)
  - Alert array with severity breakdown
  - Report summary: trade count, P&L, risk metrics
  - Guardian gate results (all 8 + final verdict)
  - Authority=ZERO lock status

**Output from Batch:**
- `AlertRecordTuple` → dashboard display (read-only)
  - Alerts sorted by severity (CRITICAL → HIGH → MEDIUM → LOW)
  - Escalation flags visible
  - Resolution status tracked
- `DayReportTuple` → summary view (read-only)
  - Trade count, gross P&L, net P&L
  - Risk metrics: max_drawdown, VaR_95, Sharpe ratio, win_rate
  - Export timestamp and finalization status
- Guardian verdict display (read-only)
  - All 8 gates + results (PASS|BLOCKED|NOT_PROVEN)
  - Final batch verdict
  - Authority=ZERO prominently displayed
  - Truth bar: age in seconds, stale warning if > 300s

**Constraints:**
- UI display read-only (no state changes allowed from UI)
- No authority grants (Authority=ZERO hardcoded)
- No verdict overrides (batch verdict immutable)
- Alerts are escalation-only (state set by batch, not UI)
- Truth bar shows staleness (> 300s = red warning)

---

## Key Invariants (Must Be Verified in Code)

### Authority Lock (Non-Negotiable)

```python
# Hardcoded check at batch creation
if batch.mode not in [PAPER, SHADOW, ANALYSIS]:
    raise InvalidBatchMode("mode must be PAPER, SHADOW, or ANALYSIS")
    
# Hardcoded check at verdict issuance
if verdict.authority_used != ZERO:
    verdict.batch_status = BLOCKED
    raise AuthorityEscalationDetected("authority must be ZERO")
    
# Hardcoded check before executing trades (never allowed)
if batch.live_enabled or batch.broker_orders_allowed:
    raise LiveExecutionBlocked("batch cannot execute real trades")
```

**No conditionals. No fallback. No escalation path.**

### Immutability Enforcement

```python
# Batch data immutable after close
if batch.closed_at is not None:
    if attempt_to_update_batch_data():
        raise ImmutabilityViolation("batch data locked after close")
        
# Compliance bundle immutable after certification
if compliance_bundle.certified_at is not None:
    if attempt_to_update_bundle_fields():
        raise ImmutabilityViolation("bundle locked after certification")
        
# Archive write-once enforcement
if archive_record_exists(archive_record_id):
    if attempt_to_update_or_delete_archive():
        raise WriteOnceViolation("archive records cannot be modified/deleted")
```

### Verdict Aggregation Logic

```python
# All 8 gates must PASS for batch APPROVED
batch_approved = (
    len(verdict.guardian_gate_results) == 8 and
    all(gate.verdict == PASS for gate in verdict.guardian_gate_results) and
    verdict.compliance_passed and
    verdict.tax_verified and
    verdict.archive_verified
)

if batch_approved:
    verdict.batch_status = APPROVED
elif any(gate.verdict == BLOCKED for gate in verdict.guardian_gate_results):
    verdict.batch_status = BLOCKED
else:  # Any gate NOT_PROVEN
    verdict.batch_status = NOT_PROVEN
```

---

## Batch Lifecycle State Machine

```
                    ┌──────────────────────────────────┐
                    │ BatchRun State Transitions        │
                    └──────────────────────────────────┘
                            │
                            ▼
                      ┌──────────────┐
                      │   PENDING    │
                      │  (batch_id,  │
                      │   run_date)  │
                      └──────┬───────┘
                             │
                    (market_close_time reached)
                             │
                             ▼
                      ┌──────────────┐
                      │  PROCESSING  │
                      │ (export +    │
                      │  summary)    │
                      └──────┬───────┘
                             │
    (verdict issued)   (compliance     (archive
     + gates pass)       verified)      written)
             │               │              │
             │       ┌───────┴──────┐      │
             │       ▼              │      │
             │   ┌──────────┐       │      │
             │   │ BLOCKED  │       │      │
             │   │ (halt)   │       │      │
             │   └──────────┘       │      │
             │                      │      │
             ▼                      ▼      ▼
         ┌────────────────────────────────┐
         │ CLOSED                         │
         │ (closed_at set, data immutable)│
         └────────────┬───────────────────┘
                      │
         (archive write verified,
          hp_receipt received)
                      │
                      ▼
         ┌────────────────────────────┐
         │ ARCHIVED                   │
         │ (ArchiveRecord.status=VER) │
         │ (read-only, retention=7yr) │
         └────────────────────────────┘
```

---

## Verdict Aggregation Logic

### Input: Guardian 8-Gate Verdicts

```
Gate 1: SCHEMA_AND_IDENTITY
Gate 2: HASH_INTEGRITY
Gate 3: AUTHORITY_POLICY_COMPLIANCE
Gate 4: MACHINE_HEALTH_AND_READINESS
Gate 5: CANARY_EXECUTION
Gate 6: EVIDENCE_CONSISTENCY
Gate 7: FRESHNESS_AND_STALENESS
Gate 8: FINAL_ARBITER
```

### Batch Verdict Decision Table

| Condition | Batch Status | Action |
|-----------|---|---|
| ALL 8 gates = PASS AND compliance_passed AND tax_verified AND archive_verified | **APPROVED** | Proceed to archive write |
| ANY gate = BLOCKED OR compliance failed OR tax failed OR archive failed | **BLOCKED** | Halt batch, no archive write, alert escalation |
| ANY gate = NOT_PROVEN (waiting for evidence) | **NOT_PROVEN** | Wait for resolution (5-min timeout → BLOCKED) |

---

## Regulatory Retention Lifecycle

### TaxDataArchive Retention

```
Archive Created (ACTIVE, archive_date)
  ↓
Retention Period Active
  (retention_years = 7, minimum per IRS/regulatory requirements)
  ↓
Retention Until Date Reached (retention_until = archive_date + 7 years)
  ↓
Available for Purge (archive_status = ACTIVE → PURGED)
  ↓
Archive Purged (data destroyed, compliance met)
```

**Key Rules:**
- Minimum 7-year retention (regulatory requirement)
- No purge before `retention_until` date (enforced by constraint gate CG08)
- Archive status immutable until PURGED
- After PURGED, record archived but data gone (no recovery)

---

## Implementation Lanes (Parallel Ready)

### Batch Engine Team (M04: Sep 8–14)

**Deliverables:**
- Batch lifecycle management (PENDING → PROCESSING → CLOSED → ARCHIVED)
- Guardian verdict aggregation (8-gate input → batch verdict)
- Compliance bundle certification (tax data locking)
- Archive write coordination (HP durable storage)
- Alert generation and escalation
- Report finalization

**Exit criteria:**
- All constraint gates (CG01-CG08) enforced
- Guardian integration tested (all 8 gates PASS → APPROVED)
- HP integration tested (archive write + receipt verification)
- Authority=ZERO locked throughout
- Data immutable after batch close

**Risks:**
- R01: Guardian verdict incomplete → timeout to BLOCKED
- R02: Batch executes without APPROVED → hardcode authority check
- R03: Archive data corrupted → immutable hash verification
- R04: Batch data mutable after close → database trigger enforcement
- R05: Compliance data loss → HP durable storage + receipt

---

## Version Control

**Frozen Documents:**
- NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json ← V1 (immutable)
- NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md ← V1 (immutable)

**Change Control:**
- Bugs discovered: file issue, patch in PATCH release (V1.1)
- Clarifications: add appendix, don't modify frozen sections
- New requirements: wait for Phase 3, new major version (V2)
- Authority invariant changes: Owner approval + Domain Architect review (unlikely)

---

## Onboarding Sequence (M04 Start)

**For Batch Engine Developers:**

1. Read: NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md (Executive Summary → Authority Invariant)
2. Review: NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json (entities, tuples, relationships)
3. Study: Workflow state machine, constraint gates, integrations
4. Understand: Guardian verdict aggregation (all 8 gates required)
5. Understand: HP archive integration (durable storage + receipt)
6. Implement: Batch lifecycle state machine
7. Implement: Verdict aggregation logic (all-or-nothing APPROVED)
8. Implement: Constraint gate enforcement (CG01-CG08)
9. Test: Guardian integration (gate verdicts → batch verdict)
10. Test: HP integration (archive write → hp_receipt → VERIFIED)
11. Verify: Authority=ZERO locked, data immutable after close
12. Code review: Frozen invariants vs. implementation

**For QA/Testers:**

1. Read: NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md (Verdict Types + Constraints)
2. Implement: Test cases for all 8 constraint gates (CG01-CG08)
3. Implement: Guardian integration tests
   - All 8 gates PASS → batch APPROVED
   - Any gate BLOCKED → batch BLOCKED
   - Any gate NOT_PROVEN → batch NOT_PROVEN
4. Implement: Compliance bundle tests
   - Certification locks data (immutable)
   - Receipt hashes populated
   - Audit trail append-only
5. Implement: Archive write-once tests
   - HP durable storage accepts write
   - HP receipt received and verified
   - No updates/deletes allowed after write
6. Implement: Immutability tests
   - After closed_at, no batch data updates
   - After certified_at, no compliance data updates
   - After archive write, no archive updates
7. Test: Authority=ZERO hardcoded
   - Batch mode must be PAPER/SHADOW/ANALYSIS (not LIVE)
   - Verdict authority must be ZERO
   - No real trades executed
8. Document: Pass/fail for each test case
9. Sign-Off: QA lead confirms all tests passed

---

## Risk Mitigation

### Critical Risks (Phase 2)

| Risk | Mitigation | Owner |
|------|-----------|-------|
| R01: Guardian verdict incomplete | Batch verdict requires all 8 gates. Timeout to BLOCKED if missing gates. | Batch Team |
| R02: Batch executes without APPROVED | Authority=ZERO hardcoded. APPROVED requires ALL conditions. No bypass paths. | Batch Team + Guardian |
| R03: Archive data corrupted | Write-once to HP durable storage. Immutable hash seals integrity. HP receipt confirms. | Batch Team + HP |
| R04: Batch data mutable after close | closed_at timestamp marks immutability. UPDATE triggers database violation. | Batch Team |
| R05: Compliance data loss | ComplianceBundle certified + locked. Archived to HP with receipt. Retention enforced. | Batch Team + HP |

---

## Milestone Summary

| Milestone | Status | Date | Owner |
|-----------|--------|------|-------|
| **M01 — Freeze** | COMPLETE | 2026-09-07 | Domain Architect |
| **M02 — HP Infra** | STARTING | 2026-09-08 | HP 24/7 Team |
| **M03 — Guardian** | STARTING | 2026-09-08 | Guardian Enforcement |
| **M04 — Batch Engine** | STARTING | 2026-09-08 | Batch Team |
| **M05 — Integration** | WAITING | 2026-09-15 | All lanes |
| **M06 — Cert** | WAITING | 2026-09-17 | Architect + Guardian |
| **M07 — Owner Review** | WAITING | 2026-09-19 | Owner |

**Critical Path:** M01 ✓ → M03 + M04 → M05 → M06 → M07

---

## Sign-Off

| Role | Responsibility | Status |
|------|---|---|
| **Domain Architect** | Froze batch domain model, verified Authority invariant | ✓ COMPLETE |
| **Guardian Lead** | Integration review (GateDecisionTuple → BatchVerdictTuple) | TBD (M04 start) |
| **HP Lead** | Integration review (ArchiveRecord + durable storage + receipt) | TBD (M04 start) |
| **Batch Team Lead** | Implementation plan + development start | TBD (M04 start) |
| **Technical Reviewer** | Code adherence to frozen model | TBD (M04 end) |
| **QA Lead** | Test plan + constraint gate verification | TBD (M04 end) |

---

## Document Control

**Classification:** Technical Specification (Frozen)  
**Audience:** Batch Engine Team, Guardian Integration, HP Integration, QA, Architects  
**Distribution:** Internal (FlipFlop HQ project directory)  
**Change Authority:** Domain Architect (for corrections), Owner (for major changes)  
**Retention:** Permanent (audit trail)  

---

**NinjaTrader Batch Phase 2 Domain Model: FROZEN AND LOCKED**

Authority Invariant: ZERO (immutable)  
Failure Policy: FAIL_CLOSED  
Guardian Integration: 8-gate verdict aggregation (all-or-nothing APPROVED)  
HP Integration: Durable storage archive + receipt verification  
Implementation Start: 2026-09-08  

**Status: READY FOR IMPLEMENTATION**
