# Guardian Enforcement Phase 2 — Frozen M01 Deliverables Index

**Date:** 2026-09-07  
**Status:** PHASE_2_FROZEN_M01 COMPLETE  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**Implementation Start:** 2026-09-08  

---

## Start Here

**You have 5 frozen documents totaling 114 KB of specifications:**

### 1. GUARDIAN_PHASE2_FROZEN_DELIVERABLES.md (13 KB) ← **START HERE**
**Audience:** Everyone  
**Content:** Overview of all deliverables, what's frozen, onboarding sequence, risks  
**Read Time:** 10 minutes  

---

### 2. GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md (30 KB)
**Audience:** Architects, all stakeholders  
**Content:** Complete specification with entities, relationships, tuples, 8 gates, verdicts, constraints, integration points  
**Read Time:** 30 minutes  
**Key Sections:**
- Authority Invariant (hard-locked)
- 7 Core Entities
- 4 Frozen Tuples
- 8 Gates + Logic
- 8 Fail-Closed Constraints
- Integration Points (HP, NinjaTrader, UI)

---

### 3. GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json (35 KB)
**Audience:** Developers, architects  
**Content:** Machine-readable entity/relationship graph (JSON)  
**Use:** Schema validation, code generation, API spec generation  
**Format:** Structured JSON with:
- Entities (fields, constraints, lifecycle)
- Relationships (cardinality, cascade rules)
- Frozen tuples (field definitions)
- 8 gates (required checks, verdicts, blocking conditions)
- Fail-closed constraints
- Integration points with input/output schemas

---

### 4. GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md (15 KB)
**Audience:** Gate engineers (M03 implementation team)  
**Content:** Per-gate implementation logic, test cases, verdict recording  
**Use:** Copy test cases verbatim, implement gate logic to pass all tests  
**Sections Per Gate:**
- Input schema
- Required checks
- Blocking conditions
- Not-proven conditions
- Verdict truth table
- Test cases (PASS, BLOCKED, NOT_PROVEN examples)

**Quick Reference:** Truth table showing all 8 gates' block/pass/not-proven conditions

---

### 5. GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md (21 KB)
**Audience:** QA, technical reviewers (pre-implementation and M03 exit criteria)  
**Content:** 100+ verification items across:
- Authority invariant lock (7 checks)
- Entity immutability (7 entities)
- Gate logic (6 test cases per gate × 8 gates = 48 tests)
- Fail-closed constraints (5 checks per constraint × 8 = 40 checks)
- Integration points (8–10 checks per system × 3 = 30 checks)
- Sign-off table

**Use:** Check off each item as implementation completes. Sign off when 100% verified.

---

## What Was Frozen (M01 Deliverable)

### Authority Invariant
```
AUTHORITY = ZERO (no escalation ever)
LIVE = OFF (paper-only)
BROKER_ORDERS = NONE (no real orders)
CONTROL_MUTATION = NONE (immutable artifacts)
FAILURE_POLICY = FAIL_CLOSED (stale/missing/contradictory blocks)
```
**Status:** LOCKED. Cannot change. Every implementation must verify.

### 7 Core Entities
1. ReleaseGate — Gate structure + policy reference
2. GateVerdict — Binary outcome (PASS|BLOCKED|NOT_PROVEN), immutable
3. EvidenceRecord — Observations (hashes, canary, policy, health), immutable
4. AuthorityPolicy — Rules for what evidence suffices
5. DecisionCartridge — Snapshot of all 8 gate results, sealed
6. CanaryRun — Controlled test deployment + evidence
7. DeploymentCandidate — Artifact bundle + gate journey

### 4 Frozen Tuples
1. AuthorityTuple (5 fields) — Authority governance
2. StrategyIdentityTuple (5 fields) — Strategy identification
3. GateDecisionTuple (7 fields) — Immutable gate decision record
4. DeploymentCandidateTuple (7 fields) — Deployment bundle

### 8 Sequential Gates
| Gate | Name | Stale Threshold | Pass/Block/Not-Proven Examples |
|------|------|------|------|
| 1 | SCHEMA_AND_IDENTITY | N/A | Valid schema / Duplicate ID / Passport pending |
| 2 | HASH_INTEGRITY | 300s | All hashes match / Hash mismatch / Source unavailable |
| 3 | AUTHORITY_POLICY_COMPLIANCE | 300s | Authority=ZERO / Authority≠ZERO / Policy pending |
| 4 | MACHINE_HEALTH_AND_READINESS | 60s heartbeat | Fleet healthy / Machine error / Heartbeat pending |
| 5 | CANARY_EXECUTION | 300s window | All metrics pass / error_rate>5% / Window incomplete |
| 6 | EVIDENCE_CONSISTENCY | 300s | No contradictions / Hash conflict / Evidence pending |
| 7 | FRESHNESS_AND_STALENESS | 300s hard limit | All fresh / Evidence stale / Evidence not collected |
| 8 | FINAL_ARBITER | 300s | All gates passed / Prior gate blocked / Cartridge incomplete |

### 8 Fail-Closed Constraints
- FC01: NO_AUTHORITY_ESCALATION
- FC02: STALE_EVIDENCE_BLOCKS (300s)
- FC03: CONTRADICTED_EVIDENCE_BLOCKS
- FC04: MISSING_REQUIRED_EVIDENCE_BLOCKS
- FC05: CANARY_FAILURE_BLOCKS (error>5%, latency>200ms)
- FC06: HASH_MISMATCH_BLOCKS
- FC07: ALL_GATES_MUST_PASS_FOR_PROMOTION
- FC08: NO_MANUAL_OVERRIDE_OF_GATE_VERDICTS

### 3 Integration Points
- **HP Infrastructure:** Machine health, fencing, heartbeat → Gate 4; promotion → deployment
- **NinjaTrader Batch:** Order intent → evidence; PASS verdict → execution; BLOCKED/NOT_PROVEN → wait/reject
- **UI Dashboard:** Guardian state → display; show Authority=ZERO + truth_age + stale warnings; read-only

---

## How to Use These Documents

### Week 1 (Reading Phase)

**Day 1–2: Architects & Team Leads**
- Read: GUARDIAN_PHASE2_FROZEN_DELIVERABLES.md (10 min)
- Read: GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md (30 min)
- Review: GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json (20 min)
- Discuss: Authority invariant, gate ordering, integration points

**Day 2–3: Gate Engineers (M03 Team)**
- Read: GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md (15 min)
- Copy: Test cases for your assigned gate(s)
- Setup: Development environment, test framework

**Day 3–4: QA / Technical Reviewers**
- Read: GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md (20 min)
- Setup: Test execution plan, verification spreadsheet
- Prepare: Test data, mock services (HP health, canary results, etc.)

### Week 2–3 (M03 Implementation)

**Gate Engineers:**
- Implement Gate logic following guide
- Pass all test cases from Implementation Guide
- Code review + technical reviewer sign-off

**QA:**
- Execute verification checklist as gates complete
- Document pass/fail for each test case
- Sign off on each gate when 100% verified

**UI/Integration Teams:**
- Implement Guardian API endpoints (state snapshot, truth bar, promotion status)
- Integrate with gate verdicts + evidence
- Verify Authority=ZERO displayed on all screens

### Week 4 (M03 Exit & M05 Prep)

**Sign-Off:**
- Architect: Confirms domain model adhered to in code
- Guardian Lead: Confirms 8/8 gates functional
- QA Lead: Confirms 100+ verification items passed
- Technical Reviewer: Signs constraints document

**Handoff to Integration (M05):**
- Move to GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md Integration Points section
- Coordinate with HP Infra, NinjaTrader Batch, UI teams
- Verify end-to-end signal flow (candidate → gates → verdict → action)

---

## File Structure

```
/C/FLIP_FLOP_HQ/
├── 00_README_GUARDIAN_FROZEN_M01.md (this file)
├── GUARDIAN_PHASE2_FROZEN_DELIVERABLES.md (overview)
├── GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md (complete spec)
├── GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json (machine-readable)
├── GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md (implementation)
└── GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md (QA verification)
```

---

## Key Dates

| Milestone | Date | Deliverable | Owner |
|-----------|------|-------------|-------|
| **M01 — Freeze** | 2026-09-07 | Domain model (5 docs) | Domain Architect ✓ |
| M02 — HP Infra | 2026-09-08 to 2026-09-11 | Fencing, health, recovery | HP 24/7 |
| M03 — Guardian | 2026-09-08 to 2026-09-12 | 8-gate engine | Guardian Enforcement |
| M04 — UI | 2026-09-08 to 2026-09-14 | Dashboard, truth bar | UI Design |
| M05 — Integration | 2026-09-15 to 2026-09-16 | Signal flow end-to-end | All lanes |
| M06 — Cert | 2026-09-17 to 2026-09-18 | Authority validation | Architect + Guardian |
| M07 — Owner Review | 2026-09-19 | Final approval | Owner |

**Critical Path:** M01 ✓ → M03 → M05 → M06 → M07

---

## Constraints (Non-Negotiable)

### Authority Lock (Every Implementation)

```python
# Gate 3 + Gate 8 must include:
if candidate.authority != ZERO:
    return BLOCKED, "authority_not_zero"  # No fallback
```

### Stale Evidence (Gate 7)

```
Threshold: 300 seconds (hardcoded)
Evidence > 300s old: BLOCKED
Evidence 300s or newer: PASS (if other checks pass)
```

### All Gates Must Pass (Gate 8 + DecisionCartridge)

```
final_verdict = PASS  IFF  all 8 gates = PASS
final_verdict = BLOCKED  IF  any gate = BLOCKED
final_verdict = NOT_PROVEN  IF  any gate = NOT_PROVEN AND none = BLOCKED
```

### Verdict Immutability (Database)

```
GateVerdict table: INSERT only
No UPDATE path on verdict field
Immutable record = audit trail
```

---

## Quick Links (Sections in Documents)

### GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md

- [Authority Invariant](#authority-invariant-hard-locked) — Must verify in code
- [7 Core Entities](#domain-entities-7-core) — Immutability rules
- [8 Gates](#eight-gates--verdicts) — Logic for each gate
- [Verdict Types](#verdict-types) — PASS vs BLOCKED vs NOT_PROVEN
- [Fail-Closed Constraints](#fail-closed-constraints-8-hard-rules) — 8 non-negotiables
- [Integration Points](#integration-points) — HP, NinjaTrader, UI

### GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md

- [Gate 1: SCHEMA_AND_IDENTITY](#gate-1-schema_and_identity) — Test cases + logic
- [Gate 2: HASH_INTEGRITY](#gate-2-hash_integrity) — Hash matching
- [Gate 3: AUTHORITY_POLICY_COMPLIANCE](#gate-3-authority_policy_compliance) — Authority lock
- [Gate 4: MACHINE_HEALTH_AND_READINESS](#gate-4-machine_health_and_readiness) — Health checks
- [Gate 5: CANARY_EXECUTION](#gate-5-canary_execution) — Canary results
- [Gate 6: EVIDENCE_CONSISTENCY](#gate-6-evidence_consistency) — Contradiction detection
- [Gate 7: FRESHNESS_AND_STALENESS](#gate-7-freshness_and_staleness) — Freshness checks
- [Gate 8: FINAL_ARBITER](#gate-8-final_arbiter) — Final verdict
- [Summary: 8-Gate Truth Table](#summary-8-gate-truth-table) — One-page reference

### GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md

- [Authority Invariant Lock](#authority-invariant-lock) — 7 checks
- [Entity Immutability Guarantees](#entity-immutability-guarantees) — Per-entity constraints
- [Gate Logic Verification (M03 Start Checklist)](#gate-logic-verification-m03-start-checklist) — 6 tests per gate
- [Fail-Closed Constraint Verification](#fail-closed-constraint-verification) — 8 constraints × 5 checks each
- [Integration Points Verification](#integration-points-verification) — HP, NT, UI checks
- [Pre-Deployment Sign-Off](#pre-deployment-sign-off) — 100+ items

---

## FAQ

**Q: Can we change the 300-second stale threshold?**  
A: No. It's frozen and hardcoded in Gate 7. If you need a different threshold, that's a Phase 3 requirement, not Phase 2.

**Q: Can we skip a gate or reorder them?**  
A: No. All 8 gates must execute sequentially. Reordering is a Phase 3 decision, not Phase 2.

**Q: What if authority needs to be SCALED or escalated?**  
A: That's a Phase 3 or later requirement. Phase 2 is Authority=ZERO only. Gate 3 rejects any authority ≠ ZERO.

**Q: Can we allow live orders?**  
A: No. live_enabled=false is frozen. Phase 2 is paper-only. Real orders come in Phase 3 (if approved by Owner).

**Q: What if a gate produces a different verdict than expected?**  
A: Document as a bug. Create an issue with specifics (gate #, test case, expected vs actual). Domain Architect reviews for patch vs Phase 3 requirement.

**Q: Who approves code changes to Guardian?**  
A: Domain Architect (for bug fixes / frozen model adherence) + Guardian Lead (for implementation details).

---

## Support

**For questions about this domain model:**
- Frozen spec issues → Domain Architect
- Implementation questions → Guardian Lead
- Gate-specific bugs → Gate Engineer + Technical Reviewer
- Integration issues → Integration Lead (M05)

---

## Document Index

| Document | Size | Version | Frozen |
|----------|------|---------|--------|
| 00_README_GUARDIAN_FROZEN_M01.md | 10K | 1.0 | Yes |
| GUARDIAN_PHASE2_FROZEN_DELIVERABLES.md | 13K | 1.0 | Yes |
| GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md | 30K | 1.0 | Yes |
| GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json | 35K | 1.0 | Yes |
| GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md | 15K | 1.0 | Yes |
| GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md | 21K | 1.0 | Yes |

**Total:** 124 KB of frozen specifications

**Authority:** Domain Architect  
**Status:** LOCKED (M01 COMPLETE)  
**Next Phase:** M03 Implementation starts 2026-09-08  

---

**Guardian Phase 2 Domain Model: FROZEN AND READY FOR IMPLEMENTATION**

Proceed to M03. Authority=ZERO is locked. All gates defined. Begin Gate 1–8 implementation.

