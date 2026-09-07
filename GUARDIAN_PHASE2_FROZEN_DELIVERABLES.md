# Guardian Phase 2 — Frozen Domain Model Deliverables

**Freeze Date:** 2026-09-07  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**Phase Status:** M01 COMPLETE  
**Implementation Start:** 2026-09-08  

---

## Deliverables Overview

Four comprehensive documents freeze the Guardian enforcement domain model for Phase 2 implementation:

1. **GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json** — Structured entity/relationship graph
2. **GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md** — Complete specification with examples
3. **GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md** — Developer quick-reference for 8-gate logic
4. **GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md** — 100+ verification items for QA

---

## File Locations

### Primary Frozen Documents

| File | Location | Purpose | Audience |
|------|----------|---------|----------|
| GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json | `/C/FLIP_FLOP_HQ/` | Canonical entity/relationship graph (machine-readable) | Developers, Architects |
| GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md | `/C/FLIP_FLOP_HQ/` | Complete specification with constraints and examples | All stakeholders |
| GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md | `/C/FLIP_FLOP_HQ/` | Per-gate implementation logic, test cases, verdicts | Gate engineers |
| GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md | `/C/FLIP_FLOP_HQ/` | Pre-implementation verification (100+ checks) | QA, Technical Reviewers |

---

## What Is Frozen (Immutable)

### Authority Invariant (Hard-Locked)

```
AUTHORITY = ZERO (no escalation ever)
LIVE = OFF (paper-only, no real orders)
BROKER_ORDERS = NONE (no broker execution)
CONTROL_MUTATION = NONE (artifacts immutable)
FAILURE_POLICY = FAIL_CLOSED (stale/missing/contradictory blocks)
```

**Status:** Cannot change. Every implementation must verify this invariant.

---

### Seven Core Entities

1. **ReleaseGate** — Permitting checkpoint (1 of 8)
2. **GateVerdict** — Outcome of gate evaluation (PASS|BLOCKED|NOT_PROVEN)
3. **EvidenceRecord** — Factual observation (hashes, canary results, policy, health)
4. **AuthorityPolicy** — Rules governing gate verdict thresholds
5. **DecisionCartridge** — Immutable snapshot of all 8 gate results + final verdict
6. **CanaryRun** — Controlled test deployment + evidence generation
7. **DeploymentCandidate** — Artifact bundle awaiting gate evaluations

**All entities:**
- Immutable core fields (no update path for content-bearing data)
- Audit-only append semantics (new records, no erasure)
- Hard constraints (database schema + ORM validation)

---

### Four Frozen Tuples

1. **AuthorityTuple** — (authority=ZERO, live=false, broker=false, mutation=false, approval_id)
2. **StrategyIdentityTuple** — (side, sha256, passport_id, gate_version, verification_state)
3. **GateDecisionTuple** — (gate_id, correlation_id, input_hashes, evidence_id, verdict, event_time, knowledge_time)
4. **DeploymentCandidateTuple** — (candidate_id, artifact_hashes, passport_hash, gate_results, canary_evidence_id, authority, approval_id)

**All tuples:**
- Content immutable (no updates to history)
- Timestamped (event_time, knowledge_time, recorded_at)
- Hashable (evidence_root_hash, policy_root_hash)

---

### Eight Sequential Gates

| Gate | Name | Blocks On | Produces Verdict |
|------|------|-----------|------------------|
| 1 | SCHEMA_AND_IDENTITY | Bad schema, duplicate ID, missing hash | PASS \| BLOCKED \| NOT_PROVEN |
| 2 | HASH_INTEGRITY | Hash mismatch, contradiction | PASS \| BLOCKED \| NOT_PROVEN |
| 3 | AUTHORITY_POLICY_COMPLIANCE | authority≠ZERO, live=true, mutation=true | PASS \| BLOCKED \| NOT_PROVEN |
| 4 | MACHINE_HEALTH_AND_READINESS | Machine error, heartbeat stale, clock drift, restart | PASS \| BLOCKED \| NOT_PROVEN |
| 5 | CANARY_EXECUTION | error_rate>5%, latency>200ms, rollback | PASS \| BLOCKED \| NOT_PROVEN |
| 6 | EVIDENCE_CONSISTENCY | Contradiction, temporal ordering violation | PASS \| BLOCKED \| NOT_PROVEN |
| 7 | FRESHNESS_AND_STALENESS | Evidence >300s old, missing evidence | PASS \| BLOCKED \| NOT_PROVEN |
| 8 | FINAL_ARBITER | Prior gate blocked/not_proven, authority escalation | PASS \| BLOCKED \| NOT_PROVEN |

**Decision Logic:**
- **PASS:** Evidence requirements met. Candidate may proceed.
- **BLOCKED:** Blocking condition detected (mismatch, violation, failure, contradiction, stale/missing). Candidate held.
- **NOT_PROVEN:** Evidence unavailable or incomplete. Candidate waits (5-minute timeout escalates to BLOCKED).

---

### Eight Fail-Closed Constraints

| ID | Constraint | Enforcement |
|----|-----------|----|
| FC01 | NO_AUTHORITY_ESCALATION | Gate 3 + Gate 8 check authority == ZERO |
| FC02 | STALE_EVIDENCE_BLOCKS | Gate 7 rejects evidence > 300 seconds old |
| FC03 | CONTRADICTED_EVIDENCE_BLOCKS | Gate 6 detects and blocks contradictions |
| FC04 | MISSING_REQUIRED_EVIDENCE_BLOCKS | Gate 7 requires all evidence types, timeout to BLOCKED |
| FC05 | CANARY_FAILURE_BLOCKS | Gate 5: error_rate>5% or latency>200ms or rollback |
| FC06 | HASH_MISMATCH_BLOCKS | Gate 2: any hash mismatch blocks |
| FC07 | ALL_GATES_MUST_PASS_FOR_PROMOTION | DecisionCartridge.final_verdict = PASS IFF all 8 = PASS |
| FC08 | NO_MANUAL_OVERRIDE_OF_GATE_VERDICTS | GateVerdict immutable (INSERT only, no UPDATE) |

---

### Three Integration Points

#### 1. HP Infrastructure (24/7 Worker Machines)

**Inputs to Guardian:**
- MachineHealthReport (Gate 4): {machine_id, health_status, error_count, heartbeat, clock_offset}
- FencingTokenProof (Gate 4): {token_hash, epoch, expiry, signature}
- ArtifactDeploymentManifest (Gate 5/canary): {candidate_id, paths, checksums}

**Outputs from Guardian:**
- PromotionApproval (Gate 8): {candidate_id, authority=ZERO, sealed_cartridge}
- BLOCKED_Signal: {candidate_id, blocking_gate, reason}
- NOT_PROVEN_Signal: {candidate_id, waiting_gates, ETA}

**Constraints:**
- Heartbeat < 60 seconds
- Clock skew < 5 seconds
- Fencing token not expired
- Restart/sleep/clock-jump detected → BLOCKED

#### 2. NinjaTrader Batch Engine (Order/Execution Interface)

**Inputs to Guardian:**
- StrategyExecutionIntent: {side, entry, stop, target, quantity, validity}
- OrderExecutionProof: {order_id, fill_price, fill_time, acknowledgment}

**Outputs from Guardian:**
- PromotionApproval (PASS): Order eligible for submission
- BLOCKED_Signal: Do not execute (no retry)
- NOT_PROVEN_Signal: Wait for resolution

**Constraints:**
- Authority=ZERO always (no escalation signal)
- Live orders forbidden (live_enabled=false)
- Broker orders forbidden (broker_orders_allowed=false)

#### 3. UI Control Center (Phone, Tablet, Desktop)

**Inputs to Guardian:**
- DashboardStateRequest: {user_role, sensitive_data_flag}
- ManualApprovalRequest (optional): {owner_id, candidate_id, signature}

**Outputs from Guardian:**
- GuardianStateSnapshot: {phase, authority, gates[], verdicts[], evidence_status, final_verdict, promotion_ready, truth_age_seconds}
- TruthBar: {is_fresh, age_seconds, stale_since, warning_level}
- PromotionStatus: {candidate_id, gate_results, blocking_gates, approval_status}

**Constraints:**
- Display Authority=ZERO on all screens
- Show truth_age and stale warnings (> 300s = red)
- Read-only (no authority grants, no verdict overrides)
- Admin/public toggle filters sensitive data

---

## Key Invariants (Must Be Verified in Code Review)

### Authority Lock (Non-Negotiable)

```python
# Hardcoded check in every gate entry
if candidate.authority != ZERO:
    return BLOCKED, "authority_not_zero"
```

**No conditionals. No fallback. No escalation path.**

### Evidence Immutability

```python
# All evidence inserted, never updated
class EvidenceRecord:
    evidence_id: UUID  # immutable
    observation: JSON  # immutable
    is_contradicted: bool = False  # set by contradiction detection, not user input
```

### Verdict Immutability

```python
# Verdicts append-only
class GateVerdict:
    verdict_id: UUID  # immutable
    verdict: enum  # immutable
    # No UPDATE path exists
```

### Gate Ordering

```
Gate 1 (Schema) → Gate 2 (Hash) → Gate 3 (Authority) → Gate 4 (Health)
  → Gate 5 (Canary) → Gate 6 (Consistency) → Gate 7 (Freshness) → Gate 8 (Arbiter)
```

**Sequential execution. No parallel evaluation.**

---

## What Is NOT Frozen (Implementation Details)

### Technology Choices

- Database (SQL vs NoSQL)
- ORM framework (EF vs Dapper vs SQLAlchemy)
- API framework (ASP.NET vs Flask vs FastAPI)
- Containerization (Docker vs other)

### Code Architecture

- Namespace organization
- Class hierarchies (as long as immutability constraints enforced)
- Error handling patterns
- Logging implementation

### Deployment Topology

- Where Guardian runs (Cloud vs on-premise)
- How verdicts are transmitted (message queue vs REST)
- Scaling strategy (horizontal vs vertical)

---

## Version Control

**Frozen Documents:**
- GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json ← V1 (immutable)
- GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md ← V1 (immutable)
- GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md ← V1 (immutable)
- GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md ← V1 (immutable)

**Change Control:**
- Bugs discovered: file issue, patch in PATCH release (V1.1)
- Clarifications: add appendix, don't modify frozen sections
- New requirements: wait for Phase 3, new major version (V2)
- Authority invariant changes: Owner approval + Domain Architect review (unlikely)

---

## Onboarding Sequence (M02/M03 Start)

**For Guardian Enforcement Engineers:**

1. Read: GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md (Executive Summary → Authority Invariant)
2. Review: GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json (entities, tuples, relationships)
3. Study: GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md (per-gate logic, test cases)
4. Implement: Gates 1–8 following guide (copy test cases verbatim)
5. Verify: GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md (100+ checks)
6. Sign-Off: Technical reviewer confirms all items passed

**For QA/Testers:**

1. Read: GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md (Verdict Types + Constraints)
2. Reference: GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md (test cases section)
3. Execute: Verification checklist (4 test cases per gate × 8 gates = 32 tests minimum)
4. Document: Pass/fail for each test case
5. Sign-Off: QA lead confirms 32/32 tests passed

**For UI/Integration Teams:**

1. Read: GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md (Integration Points section)
2. Understand: GuardianStateSnapshot output schema (JSON)
3. Implement: UI display for gates[], verdicts[], truth_age, stale_warnings
4. Verify: Authority=ZERO visible on all screens, read-only enforced
5. Test: Integration with Guardian API

---

## Risk Mitigation

### Critical Risks (Phase 2)

| Risk | Mitigation |
|------|-----------|
| R01: Canary PASS lacks closure evidence | Gate 5 produces explicit evidence (CanaryRun). Evidence must be fresh, timestamped, non-contradicted. |
| R04: HP restart/sleep/clock jump | Gate 4 monitors heartbeat/clock. Gate 7 enforces freshness (300s). Temporal ordering validated in Gate 6. |
| R03: UI mistaken for authority | Visual lock: Authority=ZERO displayed on all screens. UI docs emphasize read-only role. |

---

## Milestone Summary

| Milestone | Status | Date | Owner |
|-----------|--------|------|-------|
| **M01 — Freeze** | COMPLETE | 2026-09-07 | Domain Architect |
| M02 — HP Infra | STARTING | 2026-09-08 | HP 24/7 Team |
| M03 — Guardian | STARTING | 2026-09-08 | Guardian Enforcement |
| M04 — UI | STARTING | 2026-09-08 | UI Design |
| M05 — Integration | WAITING | 2026-09-15 | All lanes |
| M06 — Cert | WAITING | 2026-09-17 | Architect + Guardian |
| M07 — Owner review | WAITING | 2026-09-19 | Owner |

**Critical Path:** M01 ✓ → M03 → M05 → M06 → M07

---

## Appendix: Quick Command Reference

**Developers implementing Gates:**

```
1. Open: GUARDIAN_GATE_IMPLEMENTATION_GUIDE.md
2. Find: [Your Gate Number]
3. Copy: Input/Output schema
4. Copy: All test cases
5. Implement: Gate logic to pass all test cases
6. Test: Run checklist
7. Review: Code review with technical reviewer
```

**QA verifying implementation:**

```
1. Open: GUARDIAN_CONSTRAINT_VERIFICATION_CHECKLIST.md
2. Find: [Your Gate]
3. Execute: All test cases from Implementation Guide
4. Record: Pass/fail for each
5. Sign: Verification item (checkbox)
6. Report: To QA lead when all 100+ items complete
```

---

## Sign-Off

| Role | Responsibility | Date |
|------|-----------------|------|
| **Domain Architect** | Froze domain model, verified Authority invariant | 2026-09-07 |
| **Guardian Lead** | Reviews spec, owns implementation plan | TBD |
| **Technical Reviewer** | Signs off on code adherence to frozen model | TBD |
| **QA Lead** | Executes verification checklist | TBD |

---

## Document Control

**Classification:** Technical Specification (Frozen)  
**Audience:** Guardian Team, QA, Integration Engineers, Architects  
**Distribution:** Internal (FlipFlop HQ project directory)  
**Change Authority:** Domain Architect (for corrections), Owner (for major changes)  
**Retention:** Permanent (audit trail)  

---

**Guardian Phase 2 Domain Model: FROZEN AND LOCKED**

Authority Invariant: ZERO (immutable)  
Failure Policy: FAIL_CLOSED  
Implementation Start: 2026-09-08  

**Status: READY FOR IMPLEMENTATION**

