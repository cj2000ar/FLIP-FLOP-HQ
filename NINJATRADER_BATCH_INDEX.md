# NinjaTrader Batch Domain Model — Frozen Specification Index

**Phase 2 M01: COMPLETE**  
**Date:** 2026-09-07  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**Status:** READY FOR IMPLEMENTATION (M04: Sep 8-14)  

---

## Deliverables (4 Documents)

### 1. NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json
**Machine-readable entity/relationship graph (27 KB)**

Contains:
- 7 core entities with frozen fields, constraints, relationships
- 6 frozen tuples with immutability constraints
- Entity/relationship definitions (7 relationships defined)
- 8 constraint gates (CG01-CG08: fail-closed enforcement)
- 8-step data flow (market close → archive finalization)
- 3 integration points (Guardian, HP, UI)
- Authority invariant hard-locked (ZERO, LIVE=OFF, no trades)
- Version control and change control strategy

**Purpose:** Machine-readable specification for developers, database engineers
**Use:** Load into system design tools, generate database schemas, validate entity models

---

### 2. NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md
**Complete technical specification (39 KB)**

Contains:
- Executive Summary (key principles, Authority=ZERO)
- Authority Invariant (non-negotiable fail-closed policy)
- 7 Domain Entities (detailed field descriptions, constraints, lifecycle)
  - BatchRun (session container, market open/close, mode immutable)
  - BatchVerdict (final authorization, all-or-nothing APPROVED)
  - DayReport (end-of-day summary, P&L, risk metrics)
  - AlertRecord (trade alerts, severity, escalation)
  - ComplianceBundle (tax data, receipts, audit trail, certification lock)
  - TaxDataArchive (regulatory retention, 7-year minimum)
  - ArchiveRecord (HP durable storage, write-once, immutable hash)
- 6 Frozen Tuples (schemas, examples, constraints)
- Data Flow Diagram (7-step workflow with visual)
- 8 Constraint Gates (fail-closed enforcement table)
- 3 Integration Points (Guardian verdicts, HP durable storage, UI dashboard)
- Key Invariants (authority lock, immutability, verdict aggregation)
- Archive Retention Lifecycle (ACTIVE → ARCHIVED → PURGED)
- Database Schema Constraints (pseudo-SQL for implementation)
- Workflow State Transitions (visual state machines)
- Phase 2 Timeline (M01-M07, Batch M04 Sep 8-14)
- Onboarding Sequence (developers, QA, testers)
- Risk Mitigation (R01-R05)
- Version Control strategy

**Purpose:** Comprehensive technical reference for all stakeholders
**Audience:** Developers, architects, QA, product managers
**Use:** Development guide, testing reference, integration planning

---

### 3. NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md
**Executive summary + integration roadmap (21 KB)**

Contains:
- Overview of 3-document deliverables
- What is frozen (Authority, entities, tuples, gates)
- Batch Execution Workflow (7-step sequence with state transitions)
- 8 Constraint Gates (quick reference table)
- 3 Integration Points (inputs/outputs, constraints, examples)
- Key Invariants (authority lock, immutability, verdict logic)
- Batch Lifecycle State Machine (visual)
- Verdict Aggregation Logic (decision table: APPROVED/BLOCKED/NOT_PROVEN)
- Regulatory Retention Lifecycle (visual)
- Implementation Lanes (Batch Team M04, deliverables, exit criteria, risks)
- Onboarding Sequence (developers, QA)
- Risk Mitigation (R01-R05 table)
- Milestone Summary (M01-M07, critical path)
- Version Control strategy
- Sign-off table (roles, responsibilities)

**Purpose:** Quick-reference guide for project leadership, technical leads
**Audience:** Project managers, technical leads, integration teams
**Use:** Project planning, stakeholder communication, integration coordination

---

### 4. NINJATRADER_BATCH_FROZEN_SUMMARY.md
**Implementation guide + checklist (17 KB)**

Contains:
- Summary of deliverables and scope
- Architecture at a glance (visual overview)
- Key Points for Implementation (5 critical areas with code examples)
- Integration Checklist (Guardian, HP, compliance, immutability)
- File Locations (directory structure)
- Next Steps (M04: Sep 8-14, 5 phases)
- Authority Invariant (non-negotiable, hardcoded)
- Document Status (version, frozen, created date)
- Relationship to Guardian Enforcement
- Relationship to HP 24/7 Infrastructure
- Success Criteria (M04 end: 20+ checkboxes)
- Contact & Escalation (roles, responsibilities)

**Purpose:** Implementation roadmap and quick-start guide
**Audience:** Batch team leads, developers, QA leads
**Use:** Development sprint planning, testing strategy, sign-off criteria

---

## Document Relationship Map

```
NINJATRADER_BATCH_INDEX.md (this file)
├── NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json
│   └── Reference: 7 entities, 6 tuples, 8 gates, 3 integrations
│       Used by: Database engineers, system architects
│       Purpose: Machine-readable schema
│
├── NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md
│   └── Detailed explanation of: All entities, all tuples, all constraints
│       Includes: Data flow, state machines, lifecycle, invariants
│       Used by: Developers, QA, architects, product managers
│       Purpose: Complete technical reference
│
├── NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md
│   └── Executive summary of: Scope, workflow, integrations, timeline
│       Includes: Constraint gates, verdict logic, risks, milestones
│       Used by: Project managers, technical leads, integration teams
│       Purpose: Quick-reference guide for leadership
│
└── NINJATRADER_BATCH_FROZEN_SUMMARY.md
    └── Implementation guide for: M04 development (Sep 8-14)
        Includes: Architecture overview, integration checklist, success criteria
        Used by: Batch team, developers, QA leads
        Purpose: Development sprint planning and sign-off
```

---

## Key Concepts (Frozen)

### Authority Invariant (Non-Negotiable)

**Hard-locked at design time:**
- `AUTHORITY = ZERO` (no escalation ever)
- `LIVE = OFF` (paper-only, no real orders)
- `BROKER_ORDERS = NONE` (no execution)
- `FAILURE_POLICY = FAIL_CLOSED` (all checks must pass)

**Verified at every stage:**
- Batch creation: mode must be PAPER/SHADOW/ANALYSIS
- Verdict issuance: authority must be ZERO
- Before archive: no real trades executed

---

### Batch Execution Flow (7 Steps)

1. **BatchRun Created (PENDING):** batch_id, run_date, correlation_id
2. **Market Close Triggered (PROCESSING):** NinjaTrader export begins
3. **Data Aggregation:** DayReport + AlertRecord + ComplianceBundle created
4. **Guardian Verdict Aggregation:** All 8 gate verdicts received
5. **Verdict Decision:** APPROVED (all pass) | BLOCKED (any fail) | NOT_PROVEN (waiting)
6. **Archive Write (if APPROVED):** ComplianceBundle certified, ArchiveRecord written to HP
7. **Batch Closure (CLOSED):** closed_at set, all data immutable, archive finalized (ARCHIVED)

---

### Verdict Logic (All-or-Nothing)

```
APPROVED = ALL 8 Guardian gates PASS
           AND compliance_passed = true
           AND tax_verified = true
           AND archive_verified = true

BLOCKED = ANY gate BLOCKED
          OR compliance/tax/archive verification failed

NOT_PROVEN = ANY gate NOT_PROVEN (waiting for evidence)
```

---

### Integration Architecture

```
┌─────────────────────────────────────┐
│  Guardian Enforcement Domain        │
│  (8-gate verdict aggregation)       │
│  Input: GateDecisionTuple (8×)      │
│  Output: BatchVerdictTuple          │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────────┐
        │  NinjaTrader     │
        │  Batch Engine    │
        │  (7 entities)    │
        │  (6 tuples)      │
        │  (8 gates)       │
        └──────┬───────────┘
               │
        ┌──────┴──────────┬──────────────┐
        │                 │              │
        ▼                 ▼              ▼
   ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
   │ UI Dashboard│  │ HP 24/7 Infra│  │ Tax Filing   │
   │ (alerts,    │  │ (durable stor│  │ (compliance  │
   │  report)    │  │  + retention)│  │  data)       │
   └─────────────┘  └──────────────┘  └──────────────┘
```

---

## Implementation Timeline (M04: Sep 8-14)

| Day | Phase | Deliverable | Owner |
|-----|-------|-------------|-------|
| 1-2 | Review | Read specs, understand entity model, constraints | Batch Team |
| 3-4 | Design | DB schema, API design, Guardian integration plan | Batch Team + Architect |
| 5-8 | Implement | Batch lifecycle, verdict aggregation, archive writes | Batch Team |
| 9-10 | Test | Guardian integration, HP integration, constraint gates | Batch Team + QA |
| 11-14 | Verify | Code review, QA sign-off, technical review | All teams |

---

## Success Criteria (End of M04)

### Functional
- [ ] All 7 entities implemented with frozen constraints
- [ ] All 6 tuples immutable and hashable
- [ ] Batch lifecycle state machine (PENDING → PROCESSING → CLOSED → ARCHIVED)
- [ ] Guardian verdict aggregation (all 8 gates required, all-or-nothing APPROVED)
- [ ] Compliance bundle certification locking
- [ ] Archive write-once enforcement (HP durable storage)
- [ ] Tax archive retention enforcement (7-year minimum)
- [ ] All data immutable after closed_at

### Constraint Enforcement
- [ ] CG01: Authority=ZERO hard-locked
- [ ] CG02: Batch data immutable after close
- [ ] CG03: Verdict requires all gates pass
- [ ] CG04: Guardian gates must complete
- [ ] CG05: Compliance bundle immutable after cert
- [ ] CG06: Archive write-once (no UPDATE/DELETE)
- [ ] CG07: HP receipt required before verified
- [ ] CG08: Retention enforcement (no purge before date)

### Integration
- [ ] Guardian integration (8 gates → batch verdict)
- [ ] HP integration (archive write → receipt verification)
- [ ] UI dashboard (alerts + report, read-only)

### Testing
- [ ] 100% of test cases passed
- [ ] Guardian scenario (all 8 PASS → APPROVED) ✓
- [ ] Guardian scenario (any BLOCKED → BLOCKED) ✓
- [ ] Guardian scenario (any NOT_PROVEN → NOT_PROVEN) ✓
- [ ] Immutability scenario (update after close → error) ✓
- [ ] Archive scenario (write-once enforcement) ✓
- [ ] Compliance scenario (certification locking) ✓

### Quality
- [ ] Code review: frozen invariants verified
- [ ] QA sign-off: all constraints verified
- [ ] Technical reviewer sign-off: model adherence confirmed
- [ ] Documentation: API specs, schema, integration guides

---

## Reading Order (Recommended)

### For Developers
1. Start: **NINJATRADER_BATCH_FROZEN_SUMMARY.md** (overview, 17 KB)
2. Then: **NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md** (technical details, 39 KB)
3. Reference: **NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json** (schema, 27 KB)
4. Planning: **NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md** (integration roadmap, 21 KB)

### For QA/Testers
1. Start: **NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md** (workflow, 21 KB)
2. Then: **NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md** (constraints, 39 KB)
3. Reference: **NINJATRADER_BATCH_FROZEN_SUMMARY.md** (integration checklist, 17 KB)

### For Architects/PMs
1. Start: **NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md** (executive summary, 21 KB)
2. Then: **NINJATRADER_BATCH_FROZEN_SUMMARY.md** (integration points, 17 KB)
3. Reference: **NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md** (full details, 39 KB)

### For Database Engineers
1. Start: **NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json** (entity/relationship graph, 27 KB)
2. Then: **NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md** (constraints, pseudo-SQL, 39 KB)
3. Reference: **NINJATRADER_BATCH_FROZEN_SUMMARY.md** (integration points, 17 KB)

---

## Relationship to Guardian Enforcement

**Guardian provides 8-gate verdicts:**
- Gate 1: Schema and Identity (candidate ID valid, schema matches)
- Gate 2: Hash Integrity (artifact hashes verified)
- Gate 3: Authority Policy (authority=ZERO hardcoded)
- Gate 4: Machine Health (heartbeat < 60s, clock < 5s offset, no restart/sleep/jump)
- Gate 5: Canary Execution (error_rate < 5%, latency < 200ms)
- Gate 6: Evidence Consistency (no contradictions, temporal ordering valid)
- Gate 7: Freshness and Staleness (all evidence < 300s old)
- Gate 8: Final Arbiter (all gates passed, no authority escalation)

**Batch consumes:** GateDecisionTuple array (8 verdicts)

**Batch aggregates:** BatchVerdictTuple (all 8 must PASS for APPROVED)

**Batch enforces:** Authority=ZERO propagates through verdicts

---

## Relationship to HP 24/7 Infrastructure

**HP provides:**
- Machine health reports (MachineRoleTuple: heartbeat, clock offset, restart detection)
- Durable storage service (write acceptance, receipt confirmation)
- Retention support (7+ years minimum)

**Batch consumes:** 
- MachineRoleTuple (used by Guardian Gate 4)
- DurableReceiptTuple (archive write confirmation)

**Batch provides:**
- ArchiveRecordTuple to HP durable storage
- Immutable hash seal (SHA256)
- Retrieval metadata (format, size, dates)

**Batch enforces:**
- Write-once to HP (no modifications after write)
- HP receipt required before VERIFIED
- Retention enforcement (no purge before date)

---

## Authority Lock Verification Checklist

Use this checklist at implementation completion:

### Hardcoded Checks
- [ ] Batch.mode must be PAPER/SHADOW/ANALYSIS (never LIVE)
- [ ] Batch.authority must be ZERO (no escalation)
- [ ] BatchVerdict.authority_used must be ZERO
- [ ] No conditional escalation paths (no "if admin, then enable")
- [ ] No fallback to LIVE if Guardian delays

### Guardian Integration
- [ ] All 8 gates required (no skipping gates)
- [ ] Any gate BLOCKED → batch BLOCKED
- [ ] Any gate NOT_PROVEN → batch NOT_PROVEN
- [ ] All 8 gates PASS AND compliance AND tax AND archive → APPROVED only

### Compliance Enforcement
- [ ] Compliance checks mandatory (not optional)
- [ ] Tax verification mandatory
- [ ] Archive verification mandatory
- [ ] No "disable compliance for speed" mode

### HP Integration
- [ ] Archive writes to HP durable storage only
- [ ] HP receipt required (not optional)
- [ ] Write-once enforcement (no overwrites)
- [ ] No fallback to local storage if HP unavailable

### Audit Trail
- [ ] All verdicts immutable (no UPDATE, audit-only append)
- [ ] All batch data immutable after closed_at
- [ ] All compliance data immutable after certified_at
- [ ] All archive records immutable (write-once)

---

## Version and Change Control

**Current Versions:**
- NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json ← V1 (FROZEN)
- NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md ← V1 (FROZEN)
- NINJATRADER_BATCH_PHASE2_FROZEN_DELIVERABLES.md ← V1 (FROZEN)
- NINJATRADER_BATCH_FROZEN_SUMMARY.md ← V1 (FROZEN)

**Change Control:**
- **Bugs discovered:** File issue, patch in V1.1 (no specification change)
- **Clarifications:** Add appendix to frozen document, don't modify sections
- **New requirements:** Wait for Phase 3 planning, new major version (V2)
- **Authority changes:** Owner approval + Domain Architect review (unlikely/never)

**Immutable Aspects (never change):**
- Authority invariant (ZERO locked)
- Entity structure (7 entities, 6 tuples)
- Constraint gates (CG01-CG08)
- Integration points (Guardian, HP, UI)
- Failure policy (FAIL_CLOSED)

---

## Questions? Contact

**Specification Owner (Domain Architect):**
- Authority invariant questions
- Frozen model interpretation
- Phase 2 architecture decisions

**Batch Team Lead:**
- Implementation questions
- Development timeline
- Integration issues

**Guardian Integration Lead:**
- GateDecisionTuple schema
- Verdict timing and format
- Gate completeness requirements

**HP Integration Lead:**
- DurableReceiptTuple schema
- Archive storage constraints
- Retention policies

---

**NinjaTrader Batch Domain Model: FROZEN**

**Phase 2 M01: COMPLETE**  
**Implementation: M04 (Sep 8-14)**  
**Authority:** ZERO (hard-locked, immutable)  
**Failure Policy:** FAIL_CLOSED (all checks must pass)  

**Status: READY FOR IMPLEMENTATION**

---

**Document Index Created:** 2026-09-07  
**Index Version:** V1 (FROZEN)
