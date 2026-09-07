# Phase 2 Skill Roadmap — Matt Skills Sequence per Workstream

**Prepared:** 2026-09-07  
**For:** FlipFlop HQ Phase 2 Implementation Teams  
**Period:** Sep 8–19, 2026  
**Authority:** ZERO (LOCKED)  

---

## Overview

This roadmap specifies the recommended Matt skills sequence for each Phase 2 workstream, from frozen domain to code review sign-off. **Skills are applied in sequence, not parallel.** Each skill builds on the prior skill's output.

**Key Principle:** Frozen domains are locked. Skills clarify ambiguity, convert specs to tickets, implement to spec, and verify conformance to frozen invariants.

---

## Workstream Skill Sequences

### Workstream 1: Guardian Enforcement (M03: Sep 8–12)

**Duration:** 5 days (40 engineer-hours)  
**Lead:** Guardian Team Lead  
**Parallel to:** HP (M02), Batch + UI (M04)

#### Skill 1: `domain-modeling` (Optional, if clarification needed)
**When:** Sep 8 morning (if questions about frozen Guardian domain)  
**Duration:** 2–4 hours  
**Input:** GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md, gate logic questions  
**Output:** Clarified gate diagrams, edge case handling, test case refinement  
**Use Case:** If gate 5 (canary execution) threshold logic unclear, or if gate 6 (evidence consistency) temporal ordering needs visualization.

**Example Prompt:**
```
Skill: domain-modeling
Workstream: Guardian Enforcement
Task: Clarify Gate 5 (CANARY_EXECUTION) error_rate > 5% threshold.
  What constitutes "error"? How is error_rate calculated?
  What's the rollback logic if canary fails?
Domain: GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md (Gates section)
Constraints: Authority=ZERO must be verified in canary rollback path.
```

**Output Expected:**
- Gate 5 error calculation formula
- Canary rollback decision tree
- Edge cases (partial rollback, recovery)
- Authority check in rollback logic

---

#### Skill 2: `to-spec` (Required)
**When:** Sep 8 (morning through afternoon)  
**Duration:** 8 hours  
**Input:** GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md (frozen gates)  
**Output:** Per-gate detailed implementation specifications (1 spec per gate, 8 total)  
**Deliverable:** 8 markdown specs, each ~500 words, covering:
- Gate logic (input → processing → output)
- All verdict types (PASS|BLOCKED|NOT_PROVEN)
- Test cases (positive, negative, edge cases)
- Integration points (who calls this gate, who receives verdict)
- Error handling (exception cases, retry logic)

**Example Per-Gate Output (Gate 1: SCHEMA_AND_IDENTITY):**
```markdown
## Gate 1: SCHEMA_AND_IDENTITY

**Input:**
- DeploymentCandidate: {candidate_id, artifact_hashes, passport_hash, ...}
- Check: candidate_id globally unique? Artifact schema valid? Required fields present?

**Processing:**
1. Verify candidate_id not duplicate (check database)
2. Validate schema (all fields present, types correct)
3. Verify passport_hash non-null

**Verdicts:**
- PASS: Schema valid, ID unique, all fields present
- BLOCKED: Duplicate ID, schema invalid, missing required field
- NOT_PROVEN: Unable to check (transient database error)

**Test Cases:**
- Positive: Valid candidate, all checks pass → PASS
- Negative: Duplicate ID → BLOCKED
- Negative: Missing field → BLOCKED
- Edge case: Transient DB error → NOT_PROVEN (timeout retry)

**Integration:**
- Upstream: DeploymentCandidate ingestion
- Downstream: Gate 2 (HASH_INTEGRITY) receives verdict
- Authority check: If candidate.authority != ZERO, block (upstream catch)
```

**Guardian `to-spec` Output:**
- Gate 1 spec (SCHEMA_AND_IDENTITY)
- Gate 2 spec (HASH_INTEGRITY)
- Gate 3 spec (AUTHORITY_POLICY_COMPLIANCE)
- Gate 4 spec (MACHINE_HEALTH_AND_READINESS)
- Gate 5 spec (CANARY_EXECUTION)
- Gate 6 spec (EVIDENCE_CONSISTENCY)
- Gate 7 spec (FRESHNESS_AND_STALENESS)
- Gate 8 spec (FINAL_ARBITER)

---

#### Skill 3: `to-tickets` (Required)
**When:** Sep 8 (afternoon through evening)  
**Duration:** 4 hours  
**Input:** 8 gate implementation specs (from Skill 2)  
**Output:** 8 developer tickets (1 per gate), each covering:
- Acceptance criteria (tests from spec)
- Implementation guidance (algorithm, pseudocode)
- Dependencies (prior gates, external services)
- Estimated effort (hours)

**Example Ticket (Gate 1):**
```
Title: Implement Gate 1 (SCHEMA_AND_IDENTITY)

Acceptance Criteria:
[ ] Gate 1 accepts DeploymentCandidate input
[ ] Validates schema (all required fields present)
[ ] Checks candidate_id global uniqueness (database query)
[ ] Returns PASS if all checks pass
[ ] Returns BLOCKED if ID duplicate or schema invalid
[ ] Returns NOT_PROVEN if transient DB error
[ ] Timeout after 30s → NOT_PROVEN
[ ] Authority check: upstream catch (gate 1 assumes authority pre-filtered)

Effort Estimate: 6 hours (1 developer-day)

Dependencies:
- Database schema (candidate table must exist)
- DeploymentCandidate entity (ORM model)
- Logger (for NOT_PROVEN reasons)

Test Cases to Implement:
1. Valid candidate, all fields → PASS
2. Duplicate candidate_id → BLOCKED
3. Missing required field → BLOCKED
4. DB transient error → NOT_PROVEN + retry
5. Timeout (30s) → NOT_PROVEN + escalate to BLOCKED
```

**Guardian `to-tickets` Output:** 8 tickets

---

#### Skill 4: `tdd` (Required)
**When:** Sep 9–11 (days 2–4, Gates 1–8 in parallel or sequence)  
**Duration:** 24 hours (3 developers × 8 hours, or 1 developer × 24 hours over 3 days)  
**Input:** 8 implementation specs + tickets  
**Output:** 
- 32 test cases (4 per gate: positive, negative, edge, timeout)
- Red-green-refactor cycle for each gate
- Pass/fail evidence for each test case

**Skill Invocation per Gate:**

Dev 1 (Gates 1–3):
```
Skill: tdd
Workstream: Guardian Enforcement
Gates: 1 (SCHEMA_AND_IDENTITY), 2 (HASH_INTEGRITY), 3 (AUTHORITY_POLICY_COMPLIANCE)
Duration: 8 hours (Gates 1–3, ~2.5 hours per gate)

Red Phase:
1. Write failing test: test_gate1_duplicate_id_blocked()
   - Input: duplicate candidate_id
   - Expected: BLOCKED verdict
   - Run test (fail expected)

Green Phase:
2. Implement Gate 1 logic (minimal to pass test)
   - Check database for duplicate
   - Return BLOCKED if found

Refactor Phase:
3. Clean up code, add error handling
4. Run all tests for Gate 1 (4 tests must pass)

Repeat for Gates 2–3
```

Dev 2 (Gates 4–6):
```
Skill: tdd
Workstream: Guardian Enforcement
Gates: 4 (MACHINE_HEALTH_AND_READINESS), 5 (CANARY_EXECUTION), 6 (EVIDENCE_CONSISTENCY)
Duration: 8 hours (Gates 4–6, ~2.5 hours per gate)

(Same red-green-refactor cycle)
```

Dev 3 (Gates 7–8):
```
Skill: tdd
Workstream: Guardian Enforcement
Gates: 7 (FRESHNESS_AND_STALENESS), 8 (FINAL_ARBITER)
Duration: 8 hours (Gates 7–8, 4 hours per gate)

(Same red-green-refactor cycle)
```

**Guardian `tdd` Output:**
- 32 passing test cases (4 per gate)
- Code coverage > 90%
- All negative tests (authority != ZERO, stale evidence, etc.) pass

---

#### Skill 5: `implement` (Required)
**When:** Sep 11–12 (days 4–5)  
**Duration:** 8 hours (implementation refinement, clean-up, integration)  
**Input:** 8 passing gate implementations (from Skill 4)  
**Output:** 
- All 8 gates integrated into sequential pipeline
- Gate → Gate data flow verified
- DecisionCartridge built (immutable snapshot of all 8 verdicts)
- Integration with HP (Gate 4 receives MachineRoleTuple)
- Integration with Batch (GateDecisionTuple array produced)

**Skill Invocation:**
```
Skill: implement
Workstream: Guardian Enforcement
Gates: 1–8 (sequential pipeline)
Duration: 8 hours

Tasks:
1. Integrate gates 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
   - Gate 1 output (candidate_id valid?) → Gate 2 input
   - Gate 2 output (hashes match?) → Gate 3 input
   - ... continue sequential pipeline ...

2. Build DecisionCartridge (immutable verdict snapshot)
   - Collect all 8 GateDecisionTuple
   - Compute final_verdict = PASS IFF all 8 PASS
   - Hash/sign cartridge

3. Integrate with HP (Gate 4)
   - Gate 4 receives MachineRoleTuple from HP (heartbeat, clock, fencing)
   - Validate < 60s, < 5s offset, token valid
   - Return BLOCKED if not

4. Produce GateDecisionTuple array for Batch
   - Each gate produces: (gate_id, verdict, evidence_id, event_time, knowledge_time)
   - Batch receives array of 8 tuples

5. Test sequential execution (gates 1 → 8, no parallel)
   - Candidate flows through all gates
   - Verdicts collected in order
```

**Guardian `implement` Output:**
- Sequential gate pipeline (1 → 8)
- DecisionCartridge (immutable snapshot)
- HP integration (Gate 4 receives heartbeat/clock/fencing)
- Batch integration (GateDecisionTuple array)
- Integration tests passing

---

#### Skill 6: `code-review` (Required)
**When:** Sep 12 (end of day, before handoff)  
**Duration:** 4 hours  
**Input:** Complete Guardian implementation (gates 1–8, integrations)  
**Output:** 
- Code review sign-off checklist (100+ items)
- Authority invariant verified in code
- Immutability enforced (verdicts INSERT-only)
- Fail-closed constraints verified (8 FC01–FC08 checks)

**Skill Invocation:**
```
Skill: code-review
Workstream: Guardian Enforcement
Review Depth: FULL (authority invariant critical)
Duration: 4 hours (technical reviewer)

Checklist Items (Sample):

Authority Lock:
[ ] Gate 3 checks authority == ZERO (returns BLOCKED if not)
[ ] Gate 8 re-verifies authority == ZERO (final check)
[ ] No code path escalates authority (grep for "ZERO.authority" — should only be checks, never sets)
[ ] No conditionals allow authority bypass

Immutability:
[ ] GateVerdict class: verdict immutable (no setter after init)
[ ] EvidenceRecord class: observation immutable (no setter after init)
[ ] DecisionCartridge class: verdicts immutable (no setter after init)
[ ] Database: INSERT verdicts, never UPDATE verdicts (check ORM code)

Fail-Closed Constraints:
[ ] FC01: Authority check in Gate 3 + Gate 8
[ ] FC02: Stale evidence check (> 300s) in Gate 7 returns BLOCKED
[ ] FC03: Contradiction detection (Gate 6) blocks contradicted evidence
[ ] FC04: Missing evidence (Gate 7) blocks after timeout
[ ] FC05: Canary failure (error > 5%, latency > 200ms) blocks in Gate 5
[ ] FC06: Hash mismatch (Gate 2) blocks any mismatch
[ ] FC07: All gates must PASS (DecisionCartridge.final_verdict = PASS IFF all 8 PASS)
[ ] FC08: No manual override (verdicts INSERT-only, no UPDATE path)

Integration:
[ ] HP integration: Gate 4 receives MachineRoleTuple (heartbeat, clock, fencing)
[ ] Batch integration: GateDecisionTuple array produced (8 verdicts)
[ ] UI integration: GuardianStateSnapshot produced (authority lock, all gates, verdicts)

Error Handling:
[ ] NOT_PROVEN timeout (30s) → escalates to BLOCKED (fail-closed)
[ ] DB transient error → NOT_PROVEN (retry logic)
[ ] Invalid candidate → BLOCKED (not escalated)

Logging:
[ ] All verdicts logged (evidence_id, verdict, reason, timestamp)
[ ] Authority checks logged (every attempt to bypass ZERO logged)
[ ] Blocking decisions logged (reason for BLOCKED, evidence contradiction, etc.)

Performance:
[ ] Gate 1 < 100ms (schema check)
[ ] Gate 2 < 200ms (hash computation)
[ ] Gate 3 < 50ms (authority check)
[ ] Gate 4 < 100ms (heartbeat check)
[ ] Gate 5 < 500ms (canary evaluation)
[ ] Gates 6–8 < 300ms (consistency, freshness, arbiter)
[ ] Total pipeline < 2 seconds

Reviewer Sign-Off:
[ ] All 100+ checklist items verified
[ ] Authority invariant locked in code (no escalation possible)
[ ] Fail-closed constraints enforced (all 8 FC01–FC08)
[ ] Ready for QA + integration testing
```

**Guardian `code-review` Output:**
- Code review sign-off
- Authority invariant verified (no bypass paths)
- Immutability enforced (verdicts immutable)
- Fail-closed constraints verified (all 8 FC01–FC08)
- Ready for M05 integration testing

---

### Workstream 2: HP 24/7 Infrastructure (M02: Sep 8–11)

**Duration:** 4 days (24 engineer-hours)  
**Lead:** HP Team Lead  
**Parallel to:** Guardian (M03), Batch + UI (M04)

#### Skill 1: `to-spec` (Required)
**When:** Sep 8 (morning)  
**Duration:** 4 hours  
**Input:** HP section of M01 architecture contract  
**Output:** Detailed HP implementation specs:
- MachineRole entity + health, fencing, storage specs
- Heartbeat mechanism (< 60s, sequence tracking)
- Clock sync detection (NTP offset < 5s)
- Fencing token validation (expiry + signature)
- Durable storage write-once enforcement
- Receipt generation + verification

**HP `to-spec` Output:**
- Heartbeat spec (interval, timeout, recovery)
- Clock sync spec (NTP check, offset threshold)
- Fencing token spec (validation, renewal)
- Durable storage spec (write-once, path immutability)
- Receipt spec (format, verification)

---

#### Skill 2: `to-tickets` (Required)
**When:** Sep 8 (late morning)  
**Duration:** 2 hours  
**Input:** HP implementation specs (from Skill 1)  
**Output:** 4 developer tickets:
- Ticket 1: Heartbeat mechanism + clock sync (Day 1–2)
- Ticket 2: Fencing token validation (Day 2)
- Ticket 3: Durable storage write-once (Day 3)
- Ticket 4: Receipt generation + verification (Day 3)

**HP `to-tickets` Output:** 4 tickets

---

#### Skill 3: `tdd` (Required)
**When:** Sep 9 (Day 2, morning through afternoon)  
**Duration:** 8 hours  
**Input:** HP specs + tickets  
**Output:** 
- Heartbeat test cases (< 60s pass, > 60s fail, sequence tracking)
- Clock sync test cases (< 5s pass, > 5s fail, NTP error)
- Fencing token test cases (valid pass, expired fail, signature fail)
- Durable storage test cases (write-once enforced, no updates)
- Receipt test cases (generation, verification, format)

**HP `tdd` Red-Green-Refactor Cycles:**

Heartbeat (2 hours):
```
Red: test_heartbeat_fresh_less_60s_passes()
Green: Implement heartbeat check (< 60s)
Refactor: Clean up, add edge case handling

Red: test_heartbeat_stale_greater_60s_fails()
Green: Implement stale detection (> 60s blocks)
Refactor: Clean up

Red: test_heartbeat_sequence_tracking()
Green: Implement sequence counter
Refactor: Verify monotonic increase
```

Clock Sync (2 hours):
```
Red: test_clock_offset_less_5s_passes()
Green: Implement NTP offset check
Refactor: Handle NTP errors gracefully

Red: test_clock_offset_greater_5s_fails()
Green: Implement clock drift detection
Refactor: Logging

Red: test_clock_jump_detected_blocks()
Green: Detect sudden clock jumps
Refactor: Recovery path
```

Fencing Token (2 hours):
```
Red: test_fencing_token_valid_passes()
Green: Implement token validation (expiry, signature)
Refactor: Clean up

Red: test_fencing_token_expired_fails()
Green: Implement expiry check
Refactor: Edge case handling
```

Durable Storage + Receipt (2 hours):
```
Red: test_durable_storage_write_once()
Green: Implement INSERT-only (reject UPDATE)
Refactor: Error handling

Red: test_receipt_generated_verified()
Green: Generate receipt, verify hash
Refactor: Format validation
```

**HP `tdd` Output:**
- 20 passing test cases
- Code coverage > 90%
- All negative tests pass

---

#### Skill 4: `implement` (Required)
**When:** Sep 10–11 (Days 3–4)  
**Duration:** 8 hours  
**Input:** 20 passing tests (from Skill 3)  
**Output:** 
- MachineRole entity + all health/fencing/storage entities
- Heartbeat mechanism integrated
- Clock sync detection working
- Fencing token validation working
- Durable storage write-once + receipt generation

**HP `implement` Output:**
- All 8 HP entities implemented
- All 5 HP tuples validated
- All 6 fail-closed constraints (HP01–HP06) enforced
- Integration with Guardian Gate 4
- Integration with Batch archive write

---

#### Skill 5: `code-review` (Required)
**When:** Sep 11 (end of day)  
**Duration:** 2 hours  
**Input:** Complete HP implementation  
**Output:** 
- Code review sign-off
- Write-once enforcement verified
- Receipt verification working
- Integration points tested

**HP `code-review` Output:**
- Code review sign-off
- Write-once + receipt verified
- Integration ready for M05

---

### Workstream 3: NinjaTrader Batch (M04: Sep 8–14)

**Duration:** 7 days (48 engineer-hours)  
**Lead:** Batch Team Lead  
**Parallel to:** Guardian (M03), HP (M02), UI (M04)

#### Skill 1: `to-spec` (Required)
**When:** Sep 8 (morning)  
**Duration:** 6 hours  
**Input:** NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md  
**Output:** Detailed Batch implementation specs:
- Batch lifecycle state machine (PENDING → PROCESSING → CLOSED → ARCHIVED)
- Guardian verdict aggregation (8 gates required)
- BatchVerdictTuple logic (APPROVED = all 8 PASS + compliance + tax + archive)
- Compliance bundle certification (locks tax data)
- Archive write coordination (HP durable storage)
- Immutability enforcement (closed_at marks lock)

**Batch `to-spec` Output:**
- Batch lifecycle spec
- Verdict aggregation spec
- Compliance bundle spec
- Archive write spec
- Immutability enforcement spec

---

#### Skill 2: `to-tickets` (Required)
**When:** Sep 8 (afternoon)  
**Duration:** 4 hours  
**Input:** Batch implementation specs (from Skill 1)  
**Output:** 6 developer tickets:
- Ticket 1: Batch lifecycle state machine
- Ticket 2: Guardian verdict aggregation (8-gate input)
- Ticket 3: Compliance bundle certification
- Ticket 4: Archive write coordination (HP integration)
- Ticket 5: Immutability enforcement (closed_at, constraint gates)
- Ticket 6: Alert generation + report finalization

**Batch `to-tickets` Output:** 6 tickets

---

#### Skill 3: `tdd` (Required)
**When:** Sep 9–11 (Days 2–4, morning/afternoon)  
**Duration:** 16 hours  
**Input:** Batch specs + tickets  
**Output:** 
- 24 test cases (state machine, verdict aggregation, compliance, archive, immutability)

**Batch `tdd` Red-Green-Refactor Cycles:**

Batch Lifecycle (4 hours):
```
Red: test_batch_pending_to_processing()
Green: Implement state transition PENDING → PROCESSING
Refactor: Add timing checks (market_close_time)

Red: test_batch_processing_to_closed()
Green: Implement state transition PROCESSING → CLOSED
Refactor: Set closed_at timestamp

Red: test_batch_closed_to_archived()
Green: Implement state transition CLOSED → ARCHIVED
Refactor: Verify HP receipt received

Red: test_batch_immutable_after_close()
Green: Reject UPDATE after closed_at
Refactor: Error handling
```

Verdict Aggregation (4 hours):
```
Red: test_batch_all_8_gates_pass_approved()
Green: Implement APPROVED when all 8 PASS
Refactor: Clean up

Red: test_batch_any_gate_blocked_blocked()
Green: Implement BLOCKED when any gate BLOCKED
Refactor: Priority ordering

Red: test_batch_any_gate_not_proven_not_proven()
Green: Implement NOT_PROVEN when any gate NOT_PROVEN
Refactor: Timeout handling (5min → BLOCKED)

Red: test_batch_missing_gates_timeout()
Green: Implement timeout if gates incomplete
Refactor: Logging
```

Compliance + Archive (4 hours):
```
Red: test_compliance_bundle_certification()
Green: Implement certification (locks tax data)
Refactor: Immutability check

Red: test_archive_write_to_hp()
Green: Write ArchiveRecord to HP durable storage
Refactor: Path immutability

Red: test_archive_receipt_verified()
Green: Receive DurableReceiptTuple, verify hash
Refactor: Error handling

Red: test_archive_status_verified()
Green: Set archive_status = VERIFIED when receipt confirmed
Refactor: Logging
```

Immutability Enforcement (4 hours):
```
Red: test_batch_data_immutable_after_close()
Green: Reject UPDATE after closed_at
Refactor: All constraint gates

Red: test_compliance_immutable_after_cert()
Green: Reject UPDATE after certified_at
Refactor: Cascade checks

Red: test_archive_write_once()
Green: Reject UPDATE/DELETE of ArchiveRecord
Refactor: Database trigger enforcement

Red: test_retention_enforced()
Green: Reject purge before retention_until
Refactor: Compliance reporting
```

**Batch `tdd` Output:**
- 24 passing test cases
- Code coverage > 90%
- All fail-closed constraints verified (CG01–CG08)

---

#### Skill 4: `implement` (Required)
**When:** Sep 12–13 (Days 5–6)  
**Duration:** 16 hours  
**Input:** 24 passing tests (from Skill 3)  
**Output:** 
- Batch lifecycle state machine implemented + tested
- Guardian verdict aggregation working (all 8 gates)
- Compliance bundle certification working
- Archive write coordination (HP integration) working
- Immutability enforcement (database constraints) working

**Batch `implement` Output:**
- All 7 Batch entities implemented
- All 6 Batch tuples validated
- All 8 constraint gates (CG01–CG08) enforced
- Integration with Guardian (GateDecisionTuple → BatchVerdictTuple)
- Integration with HP (ArchiveRecord write + DurableReceiptTuple)

---

#### Skill 5: `code-review` (Required)
**When:** Sep 14 (end of day)  
**Duration:** 4 hours  
**Input:** Complete Batch implementation  
**Output:** 
- Code review sign-off
- Verdict all-or-nothing logic verified
- Immutability enforced throughout
- Integration points tested

**Batch `code-review` Output:**
- Code review sign-off
- Verdict aggregation verified (APPROVED = all gates PASS + compliance + tax + archive)
- Immutability verified (closed_at, certified_at, write-once)
- Integration ready for M05

---

### Workstream 4: UI Design (M04: Sep 8–14)

**Duration:** 7 days (40 engineer-hours)  
**Lead:** UI Team Lead  
**Parallel to:** Guardian (M03), HP (M02), Batch (M04)

#### Skill 1: `to-spec` (Required)
**When:** Sep 8 (morning)  
**Duration:** 4 hours  
**Input:** UI Design section of M01 architecture contract  
**Output:** Detailed UI implementation specs:
- Phone cockpit (320–480px, critical alerts, Authority=ZERO lock)
- Tablet workspace (600–1024px, summary + chart, gate status)
- Desktop command center (1200px+, full drill-down, evidence tree)
- Truth bar (age_seconds, < 60s green, 60–300s yellow, > 300s red)
- Guardian state display (all 8 gates + verdicts + authority)
- Batch status display (verdict, alerts, report)
- HP health display (heartbeat, clock, fencing)

**UI `to-spec` Output:**
- Phone cockpit spec
- Tablet workspace spec
- Desktop command center spec
- Truth bar spec
- Guardian state display spec
- Batch status display spec
- HP health display spec

---

#### Skill 2: `prototype` (Required)
**When:** Sep 8–9 (Days 1–2, morning through afternoon)  
**Duration:** 8 hours  
**Input:** UI specs (from Skill 1)  
**Output:** 
- HTML/CSS prototypes (responsive, phone/tablet/desktop)
- Truth bar component (interactive age display)
- Authority lock visual (red/locked indicator)
- Gate status display (8 gates, PASS|BLOCKED|NOT_PROVEN colors)

**UI `prototype` Red-Green-Refactor:**

Phone Cockpit (2 hours):
```
Red: Create HTML structure (mobile 320px width)
Green: Add critical alerts (severity colors)
Refactor: Responsive breakpoints, Authority lock display

Red: Style truth bar (age_seconds)
Green: Color changes (< 60s green, > 300s red)
Refactor: Animation, refresh button
```

Tablet Workspace (2 hours):
```
Red: Create HTML structure (tablet 600–1024px)
Green: Add summary chart (P&L over time)
Refactor: Responsive to desktop size

Red: Add gate status display (8 gates progress)
Green: Style progress bar
Refactor: Interactive drill-down
```

Desktop Command Center (2 hours):
```
Red: Create HTML structure (desktop 1200px+)
Green: Add full data display (all gates, verdicts, evidence)
Refactor: Drill-down capability, evidence tree

Red: Add batch status display
Green: Alert array (sorted by severity)
Refactor: Cascading disclosure
```

Integration (2 hours):
```
Red: Connect truth bar to Guardian state
Green: Update age_seconds in real time
Refactor: Responsive updates across all form factors
```

**UI `prototype` Output:**
- Phone cockpit HTML/CSS (responsive)
- Tablet workspace HTML/CSS (responsive)
- Desktop command center HTML/CSS (responsive)
- Truth bar component (interactive)
- Authority lock visual (all form factors)

---

#### Skill 3: `tdd` (Required)
**When:** Sep 9–10 (Days 2–3, afternoon through evening)  
**Duration:** 8 hours  
**Input:** UI prototypes + specs  
**Output:** 
- Component tests (truth bar age calculation, stale warning, read-only enforcement)
- Integration tests (Guardian state snapshot → UI display)
- Responsive tests (mobile, tablet, desktop breakpoints)

**UI `tdd` Test Cases:**

Truth Bar Component (2 hours):
```
Red: test_truth_bar_fresh_less_60s_green()
Green: Display age, color green
Refactor: Responsive sizing

Red: test_truth_bar_warning_60_to_300s_yellow()
Green: Display age, color yellow, warning text
Refactor: Animation

Red: test_truth_bar_stale_greater_300s_red()
Green: Display age, color red, stale warning
Refactor: Escalation visual

Red: test_truth_bar_updates_realtime()
Green: Age updates every second
Refactor: Performance optimization
```

Authority Lock (2 hours):
```
Red: test_authority_zero_displayed_phone()
Green: "Authority: ZERO" visible on phone
Refactor: Responsive sizing

Red: test_authority_zero_displayed_tablet()
Green: "Authority: ZERO" visible on tablet
Refactor: Lock icon sizing

Red: test_authority_zero_displayed_desktop()
Green: "Authority: ZERO" visible on desktop
Refactor: Emphasized display

Red: test_read_only_enforced_no_buttons()
Green: No authority grant buttons
Refactor: Disable styling
```

Gate Display (2 hours):
```
Red: test_8_gates_displayed_all_form_factors()
Green: All 8 gates visible (phone summary, tablet detailed, desktop full)
Refactor: Responsive layout

Red: test_verdict_colors_pass_blocked_not_proven()
Green: Green (PASS), red (BLOCKED), yellow (NOT_PROVEN)
Refactor: Accessibility (patterns + colors)

Red: test_gate_drill_down_desktop()
Green: Click gate → evidence tree shows
Refactor: Animation
```

Responsive (2 hours):
```
Red: test_phone_320px_layout()
Green: Cockpit displays correctly at 320px
Refactor: Touch-friendly spacing

Red: test_tablet_768px_layout()
Green: Workspace displays correctly at 768px
Refactor: Multi-column layout

Red: test_desktop_1200px_layout()
Green: Command center displays correctly at 1200px
Refactor: Full-width content
```

**UI `tdd` Output:**
- 16+ passing test cases
- Code coverage > 85%

---

#### Skill 4: `implement` (Required)
**When:** Sep 11–13 (Days 4–6)  
**Duration:** 16 hours  
**Input:** 16 passing tests (from Skill 3)  
**Output:** 
- Phone cockpit component (fully functional, responsive)
- Tablet workspace component (fully functional, responsive)
- Desktop command center component (fully functional, responsive)
- Truth bar component (age display, stale warning)
- Guardian state snapshot binding (real-time updates)
- Batch status snapshot binding (alerts, report)
- HP health snapshot binding (machine status)

**UI `implement` Output:**
- All 12 UI entities implemented
- All 10 UI tuples validated
- All 7 fail-closed constraints (UI01–UI07) enforced (read-only, authority display)
- Responsive design (phone, tablet, desktop)
- Integration with Guardian, Batch, HP APIs

---

#### Skill 5: `code-review` (Required)
**When:** Sep 14 (end of day)  
**Duration:** 4 hours  
**Input:** Complete UI implementation  
**Output:** 
- Code review sign-off
- Read-only enforcement verified (no authority grants, verdict overrides)
- Authority=ZERO display verified (all form factors)
- Truth bar implementation verified (age, stale warning)

**UI `code-review` Output:**
- Code review sign-off
- Read-only + authority lock verified
- Responsive design verified
- Integration ready for M05

---

## Cross-Workstream Skills (M05: Sep 15–16)

### M05: Integration Testing

**Skill 1: `grilling` (Required)**
**When:** Sep 15 (morning)  
**Duration:** 4 hours  
**Input:** Complete implementations (Guardian, HP, Batch, UI)  
**Output:** 
- Stress-test Guardian ↔ HP integration (heartbeat stale, clock jump, fencing expired)
- Stress-test Guardian ↔ Batch integration (incomplete verdicts, timeout)
- Stress-test Batch ↔ HP integration (archive write failure, receipt missing)
- Stress-test all ↔ UI integration (stale snapshots, display issues)

**Skill Invocation:**
```
Skill: grilling
Workstream: Phase 2 M05 Integration
Duration: 4 hours (all teams)

Stress Tests:

Guardian ↔ HP:
- What if heartbeat stale (> 60s)? → Gate 4 BLOCKED ✓
- What if clock jump (> 5s)? → Gate 4 BLOCKED ✓
- What if fencing token expired? → Gate 4 BLOCKED ✓
- What if HP unreachable? → Gate 4 NOT_PROVEN → timeout → BLOCKED ✓

Guardian ↔ Batch:
- What if only 7 of 8 gates received? → Batch NOT_PROVEN → timeout → BLOCKED ✓
- What if Gate 5 (canary) BLOCKED? → Batch BLOCKED ✓
- What if Gate 3 (authority) != ZERO? → Guardian BLOCKED + Batch BLOCKED ✓

Batch ↔ HP:
- What if archive write fails? → Batch BLOCKED ✓
- What if HP receipt missing? → Archive status not VERIFIED, Batch waits ✓
- What if archive data corrupted (hash mismatch)? → Batch BLOCKED ✓

All ↔ UI:
- What if Guardian snapshot stale (> 300s)? → UI truth bar red + warning ✓
- What if Batch snapshot missing? → UI shows "waiting" state ✓
- What if HP health snapshot delayed? → UI shows stale indicator ✓

Failure Scenarios:
- Database transaction rollback (corrupt state)?
- Network partition (Gate 4 waits forever)?
- Timer expired (NOT_PROVEN timeout → BLOCKED)?
```

**Skill `grilling` Output:**
- Integration assumptions validated
- Stress test scenarios documented
- Failure modes identified + mitigations confirmed

---

**Skill 2: `resolving-merge-conflicts` (Required)**
**When:** Sep 15 (afternoon)  
**Duration:** 2 hours  
**Input:** 4 parallel branches (M02/M03/M04 work)  
**Output:** 
- All branches merged into master/integration branch
- Conflicts resolved (schema changes, tuple definitions, integration points)
- Tests re-run on merged branch (all 100+ tests pass)

**Skill Invocation:**
```
Skill: resolving-merge-conflicts
Workstream: Phase 2 M05 Merge
Duration: 2 hours (tech lead + integration engineer)

Merge Strategy:
1. Merge M02 (HP) → master
   - Run HP tests (20 passing)
   - Verify write-once + receipt

2. Merge M03 (Guardian) → master
   - Run Guardian tests (32 passing)
   - Verify gates 1–8 + sequential pipeline
   - Resolve conflicts with M02 (Guardian Gate 4 expects MachineRoleTuple from HP)

3. Merge M04 (Batch) → master
   - Run Batch tests (24 passing)
   - Verify lifecycle + verdict aggregation
   - Resolve conflicts with M02 (Batch expects DurableReceiptTuple from HP)
   - Resolve conflicts with M03 (Batch expects GateDecisionTuple array from Guardian)

4. Merge M04 (UI) → master
   - Run UI tests (16 passing)
   - Verify responsive design
   - Resolve conflicts with all (UI expects snapshots from Guardian, Batch, HP)

5. Full integration test suite (all 92+ tests pass on merged master)
```

**Skill `resolving-merge-conflicts` Output:**
- Master branch unified (all 4 workstreams)
- All 92+ tests passing
- Integration conflicts resolved
- Ready for M06 certification

---

**Skill 3: `code-review` (Required, at scale)**
**When:** Sep 16 (morning, before handoff to M06)  
**Duration:** 4 hours  
**Input:** Merged master branch (all 4 workstreams)  
**Output:** 
- Full-depth code review (authority invariant across all workstreams)
- Immutability verification (no UPDATE paths for verdicts, evidence, batch data, archives)
- Fail-closed verification (all 25+ constraints enforced)
- Integration verification (all 6 integration checkpoints validated)

**Skill `code-review` at Scale:**
```
Skill: code-review
Workstream: Phase 2 M05 → M06 Handoff
Review Depth: FULL (cross-workstream)
Duration: 4 hours (technical reviewer)

Cross-Workstream Authority Invariant:
[ ] Guardian Gate 3: authority == ZERO check (no bypass)
[ ] Guardian Gate 8: final arbiter re-verifies authority == ZERO
[ ] Batch constraint CG01: no batch execution with authority != ZERO
[ ] UI: Authority=ZERO displayed, read-only enforced (no grants, no overrides)
[ ] No escalation path across all 4 workstreams

Cross-Workstream Immutability:
[ ] Guardian: GateVerdict immutable (INSERT-only)
[ ] Guardian: EvidenceRecord immutable (INSERT-only)
[ ] Batch: BatchVerdictTuple immutable (INSERT-only)
[ ] Batch: Data immutable after closed_at (UPDATE rejected)
[ ] HP: ArchiveRecord write-once (INSERT-only)
[ ] UI: Read-only (no state mutations from UI)

Cross-Workstream Integration:
[ ] Guardian → HP: Gate 4 receives MachineRoleTuple (all 6 data points)
[ ] Guardian → Batch: GateDecisionTuple array (all 8 gates)
[ ] Guardian → UI: GuardianStateSnapshot (authority lock, all gates, verdicts)
[ ] Batch → HP: ArchiveRecord written → DurableReceiptTuple received → VERIFIED
[ ] Batch → UI: BatchStatusSnapshot (verdict, alerts, report)
[ ] HP → UI: MachineHealthSnapshot (health, heartbeat, truth_age)

Fail-Closed Constraints (all 25+):
[ ] Guardian FC01–FC08 enforced in code (8 constraints)
[ ] HP HP01–HP06 enforced in code (6 constraints)
[ ] Batch CG01–CG08 enforced in code (8 constraints)
[ ] UI UI01–UI07 enforced in code (7 constraints)

Verdict Logic (All-or-Nothing):
[ ] Guardian: ALL 8 gates must PASS for DecisionCartridge.final_verdict = PASS
[ ] Batch: APPROVED IFF all 8 Guardian gates PASS + compliance + tax + archive
[ ] No conditional escalation, no partial approval, no majority rule

Final Authority Invariant Verification:
[ ] Code inspection: "ZERO" appears only in checks, never assignments
[ ] Git grep: "authority =" searches find no escalation paths
[ ] Compiler: No "TODO" or "FIXME" near authority checks
[ ] Tests: Negative authority tests all passing (authority != ZERO → BLOCKED)
```

**Skill `code-review` Output:**
- Cross-workstream code review sign-off
- Authority invariant verified (no bypass paths)
- Immutability enforced (verdicts, evidence, batch data, archives)
- Integration verified (all 6 checkpoints)
- Ready for M06 certification review

---

## M06 Certification Skills (Sep 17–18)

### M06: Ultra-Deep Code Review + Security Review

**Skill 1: `code-review` (Ultra-Depth)**
**When:** Sep 17 (full day)  
**Duration:** 8 hours (technical reviewer + domain architects)  
**Input:** Master branch (all 4 workstreams, fully integrated)  
**Output:** 
- Authority invariant verified in every code path (no escalation possible)
- Fail-closed constraints enforced in every gate, constraint, and UI element
- Immutability verified (no UPDATE paths, no manual overrides)
- Integration points validated (all 6 checkpoints working correctly)

**Skill Invocation:**
```
Skill: code-review
Workstream: Phase 2 M06 Certification
Review Depth: ULTRA (line-by-line authority invariant verification)
Duration: 8 hours (technical reviewer + domain architects)

Ultra-Deep Checklist:

Authority Invariant (Line-by-Line):
[ ] Guardian Gate 3: if (authority != ZERO) → BLOCKED (hardcoded)
[ ] Guardian Gate 8: if (authority != ZERO) → BLOCKED (hardcoded)
[ ] Batch CG01: if (authority != ZERO) → BLOCKED (hardcoded)
[ ] All 3 checks must return BLOCKED, never escalate
[ ] No conditional bypass paths
[ ] No environment variable override (AUTHORITY_OVERRIDE forbidden)
[ ] No database flag to escalate (authority column locked to ZERO)

Immutability (Database Level):
[ ] GateVerdict table: PRIMARY KEY (verdict_id), no UPDATE trigger defined
[ ] EvidenceRecord table: PRIMARY KEY (evidence_id), no UPDATE trigger defined
[ ] BatchRun table: UPDATE rejected after closed_at (database trigger)
[ ] ComplianceBundle table: UPDATE rejected after certified_at (database trigger)
[ ] ArchiveRecord table: no DELETE, no UPDATE allowed (database constraints)
[ ] Verify triggers on all 5 immutable tables

Fail-Closed Constraints (Code Inspection):
[ ] FC01: authority check in Gate 3 + Gate 8 (2 places)
[ ] FC02: Gate 7 checks evidence age (if age > 300s → BLOCKED)
[ ] FC03: Gate 6 detects contradictions (if contradicted → BLOCKED)
[ ] FC04: Gate 7 requires all evidence types (if missing → timeout → BLOCKED)
[ ] FC05: Gate 5 checks error_rate > 5% (if true → BLOCKED)
[ ] FC06: Gate 2 checks hash match (if mismatch → BLOCKED)
[ ] FC07: DecisionCartridge logic (PASS IFF all 8 PASS, no shortcuts)
[ ] FC08: GateVerdict INSERT-only (verify no UPDATE code path)

Integration Verification:
[ ] Guardian Gate 4 calls HP.getMachineRoleTuple() (expects heartbeat, clock, fencing)
[ ] Guardian issues GateDecisionTuple array to Batch (8 tuples, one per gate)
[ ] Batch produces BatchVerdictTuple (APPROVED logic: all 8 PASS + compliance + tax + archive)
[ ] Batch sends ArchiveRecord to HP durable storage (path immutable)
[ ] Batch receives DurableReceiptTuple from HP (receipt_id, confirmation_hash)
[ ] UI displays GuardianStateSnapshot (authority lock, all 8 gates, verdicts)
[ ] UI displays BatchStatusSnapshot (verdict, alerts, report summary)
[ ] UI displays MachineHealthSnapshot (heartbeat, clock, fencing)
[ ] All snapshots read-only (no state mutations from UI)

Verdict Logic Verification:
[ ] Guardian final_verdict = PASS IFF gates[0..7].verdict == PASS (no exceptions)
[ ] Batch batch_status = APPROVED IFF (all 8 gates PASS AND compliance AND tax AND archive) (no exceptions)
[ ] Batch batch_status = BLOCKED IFF (any gate BLOCKED OR verification failed) (fail-closed)
[ ] Batch batch_status = NOT_PROVEN IFF (any gate NOT_PROVEN AND timeout not reached) (fail-closed on timeout)

Test Coverage Verification:
[ ] Negative authority tests (authority != ZERO → BLOCKED) all passing
[ ] Negative evidence tests (stale/missing/contradicted → BLOCKED) all passing
[ ] Gate ordering tests (sequential 1 → 8, no parallel) passing
[ ] Immutability tests (UPDATE after close → error) passing
[ ] Archive write-once tests (UPDATE/DELETE after write → error) passing
[ ] Verdict all-or-nothing tests (partial gates → NOT_APPROVED) passing
[ ] Integration tests (all 6 checkpoints) passing

Security Verification:
[ ] No SQL injection (parameterized queries)
[ ] No privilege escalation (authority hard-locked)
[ ] No data corruption path (immutable + write-once enforced)
[ ] No override mechanism (no UI buttons, no environment flags)
[ ] No timing attack on authority check (all paths take same time)

Performance Verification:
[ ] Gate 1: < 100ms (schema check)
[ ] Gate 2: < 200ms (hash computation)
[ ] Gate 3: < 50ms (authority check)
[ ] Gate 4: < 100ms (heartbeat check)
[ ] Gate 5: < 500ms (canary evaluation)
[ ] Gates 6–8: < 300ms
[ ] Total pipeline: < 2 seconds
[ ] Batch verdict aggregation: < 100ms
[ ] UI render (truth bar update): < 50ms

Logging Verification:
[ ] All authority checks logged (timestamp, result, reason)
[ ] All BLOCKED decisions logged (reason, evidence, gate)
[ ] All NOT_PROVEN decisions logged (waiting gates, timeout, reason)
[ ] All archive writes logged (path, hash, receipt)
[ ] No sensitive data in logs (no passwords, private keys)

Reviewer Sign-Off:
[ ] All ultra-deep checklist items verified
[ ] Authority invariant LOCKED (no escalation path exists)
[ ] Fail-closed LOCKED (all 25+ constraints enforced)
[ ] Immutability LOCKED (no UPDATE/DELETE paths)
[ ] Integration LOCKED (all 6 checkpoints working)
[ ] Verdict logic LOCKED (all-or-nothing enforced)
```

**Skill `code-review` Output (M06):**
- Ultra-deep code review sign-off
- Authority invariant LOCKED (no bypass paths)
- Fail-closed LOCKED (all 25+ constraints)
- Immutability LOCKED (verdicts, evidence, batch data, archives)
- Integration LOCKED (all 6 checkpoints)
- Ready for M07 owner review

---

**Skill 2: `security-review` (Required)**
**When:** Sep 18 (morning)  
**Duration:** 4 hours  
**Input:** Master branch (all 4 workstreams)  
**Output:** 
- Security review sign-off
- No privilege escalation paths
- No data corruption paths
- No manual override mechanisms
- All cryptographic operations verified (hash, signature, HMAC)

**Skill Invocation:**
```
Skill: security-review
Workstream: Phase 2 M06 Certification
Duration: 4 hours (security architect)

Security Checklist:

Privilege Escalation:
[ ] Authority hard-locked to ZERO (no escalation possible)
[ ] No administrative bypass (no sudo, no admin role, no environment override)
[ ] No API endpoint for escalation (no /promote, /elevate, /admin)
[ ] Database: authority column non-nullable, default ZERO, no UPDATE path
[ ] Code: grep "authority" returns only checks (== ZERO), never assignments

Data Corruption:
[ ] Immutability enforced (no UPDATE for verdicts, evidence, batch data, archives)
[ ] Write-once enforced (HP durable storage, no DELETE, no UPDATE)
[ ] Hashing verified (checksum on all immutable data)
[ ] No truncation/purge before retention_until date

Manual Override:
[ ] No UI buttons for authority grants (Authority=ZERO displayed, read-only)
[ ] No gate verdict overrides (verdicts INSERT-only in database)
[ ] No batch status overrides (BatchVerdictTuple immutable)
[ ] No archive modifications (write-once, no manual intervention)

Cryptography:
[ ] Hash algorithm: SHA256 (FIPS 140-2 approved)
[ ] Signature algorithm: RSA-2048 or ECDSA-256 (fencing token)
[ ] HMAC for integrity (receipt verification)
[ ] No deprecated algorithms (MD5, SHA1 forbidden)
[ ] No hardcoded keys (all keys from secure vault)

API Security:
[ ] Guardian API: authentication required (API key or JWT)
[ ] Batch API: authentication required
[ ] HP API: authentication required (internal only)
[ ] UI API: read-only (no side effects from UI)
[ ] Rate limiting: configured to prevent DDoS

Logging Security:
[ ] No sensitive data logged (passwords, private keys, PII)
[ ] All authority checks logged (audit trail)
[ ] Logs immutable (write to WORM storage if possible)
[ ] Log retention: 7 years (regulatory requirement)

Incident Response:
[ ] If authority check fails: log + alert + BLOCK (no retry)
[ ] If evidence contradicted: log + block + alert
[ ] If archive corrupted: log + alert + no-recover (immutable)
[ ] If HP unreachable: timeout + NOT_PROVEN → BLOCKED (fail-closed)

Compliance:
[ ] SOC 2 Type II requirements met (access controls, logging, immutability)
[ ] GDPR compliance (PII handling, retention, deletion)
[ ] SEC compliance (market data handling, order execution, audit trail)
```

**Skill `security-review` Output:**
- Security review sign-off
- No privilege escalation paths
- No data corruption paths
- No override mechanisms
- Cryptography verified (SHA256, signatures, HMAC)
- Audit trail secured (immutable, 7-year retention)
- Incident response verified
- Ready for M07 owner review

---

## M07 Owner Review Skill (Sep 19)

### M07: Handoff + Owner Approval

**Skill 1: `handoff` (Required)**
**When:** Sep 19 (full day)  
**Duration:** 8 hours  
**Input:** 
- Master branch (all 4 workstreams, certified)
- Code review sign-off (authority invariant, fail-closed, immutability)
- Security review sign-off (no escalation, no override, cryptography verified)
- Test results (all 100+ tests passing)
- Integration checkpoints (all 6 validated)

**Output:** 
- Evidence package (all frozen domains, all constraints, all tests, all reviews)
- Owner approval checklist
- Phase 2 readiness certification

**Skill Invocation:**
```
Skill: handoff
Workstream: Phase 2 M07 Owner Review
Duration: 8 hours (architect + owner)

Evidence Package Contents:

Frozen Domains (Locked):
✓ Guardian Enforcement (7 entities, 4 tuples, 8 gates, 8 constraints)
✓ HP 24/7 Infrastructure (8 entities, 5 tuples, 6 constraints)
✓ NinjaTrader Batch (7 entities, 6 tuples, 8 constraints)
✓ UI Design (12 entities, 10 tuples, 7 constraints)
✓ Total: 34 entities, 31 tuples, 25+ constraints

Implementation Evidence:
✓ Guardian: 8/8 gates implemented, 32 tests passing
✓ HP: 5/5 mechanisms (heartbeat, clock, fencing, storage, receipt), 20 tests passing
✓ Batch: lifecycle, verdict aggregation, compliance, archive, 24 tests passing
✓ UI: phone, tablet, desktop, truth bar, 16 tests passing
✓ Total: 92+ tests passing, 100% coverage of frozen specs

Authority Invariant Evidence:
✓ Guardian Gate 3: authority == ZERO check (hardcoded, no bypass)
✓ Guardian Gate 8: authority == ZERO re-verify (final arbiter)
✓ Batch CG01: authority == ZERO enforced
✓ UI: Authority=ZERO displayed on all screens, read-only enforced
✓ Database: authority column locked (ZERO only, no UPDATE)
✓ Zero escalation paths found (code review + security review)

Fail-Closed Constraints Evidence:
✓ Guardian FC01–FC08 (8/8 constraints, code verified)
✓ HP HP01–HP06 (6/6 constraints, code verified)
✓ Batch CG01–CG08 (8/8 constraints, code verified)
✓ UI UI01–UI07 (7/7 constraints, code verified)
✓ Total: 29/29 constraints enforced, tests passing

Immutability Evidence:
✓ Guardian verdicts: INSERT-only, 0 UPDATE paths
✓ Guardian evidence: INSERT-only, 0 UPDATE paths
✓ Batch data: UPDATE rejected after closed_at (database trigger)
✓ Batch compliance: UPDATE rejected after certified_at
✓ HP archives: write-once, 0 UPDATE/DELETE paths
✓ UI: read-only (no state mutations)

Integration Evidence:
✓ Guardian ↔ HP: Gate 4 receives MachineRoleTuple (heartbeat, clock, fencing)
✓ Guardian ↔ Batch: GateDecisionTuple array (all 8 gates)
✓ Guardian ↔ UI: GuardianStateSnapshot (authority, gates, verdicts)
✓ Batch ↔ HP: ArchiveRecord → HP → DurableReceiptTuple (write-once + receipt)
✓ Batch ↔ UI: BatchStatusSnapshot (verdict, alerts, report)
✓ HP ↔ UI: MachineHealthSnapshot (health, heartbeat)
✓ All 6 integration checkpoints validated

Verdict Logic Evidence:
✓ Guardian: ALL 8 gates must PASS for final_verdict = PASS (0 shortcuts)
✓ Batch: APPROVED IFF (all 8 gates PASS + compliance + tax + archive) (0 shortcuts)
✓ Fail-closed: stale/missing/contradicted evidence → BLOCKED (no retry without fresh evidence)
✓ NOT_PROVEN timeout: 5-minute wait → BLOCKED (fail-closed on timeout)

Risk Mitigation Evidence:
✓ R01 (Canary closure): Gate 5 produces explicit CanaryRun evidence, timestamped, non-contradicted
✓ R04 (HP restart/sleep/clock): Gate 4 monitors heartbeat/clock, Gate 7 enforces freshness
✓ R02 (BUY/SELL hash mismatch): Gate 2 verifies match before M05 integration
✓ R03 (UI mistaken for authority): Authority=ZERO hardcoded, read-only UI enforced
✓ All 10 critical risks mitigated (R01–R10)

Owner Approval Checklist:
[ ] I have reviewed the frozen domains (Guardian, HP, Batch, UI)
[ ] I have reviewed the implementation (34 entities, 31 tuples, 25+ constraints)
[ ] I have reviewed the code (authority invariant locked, fail-closed enforced, immutable)
[ ] I have reviewed the test results (92+ tests passing, 100% frozen spec coverage)
[ ] I have reviewed the security report (no escalation, no override, cryptography verified)
[ ] I confirm Authority = ZERO throughout Phase 2
[ ] I confirm LIVE = OFF (paper-only, no real orders)
[ ] I confirm all gates are LOCKED and fail-closed
[ ] I approve Phase 2 implementation for go-live decision
```

**Skill `handoff` Output:**
- Evidence package (all frozen domains, implementations, tests, reviews)
- Owner approval checklist (signed)
- Phase 2 readiness certification
- **Phase 2 Ready for Live Authority Decision (Sep 19)**

---

## Skill Summary Matrix

| Workstream | M02 | M03 | M04 | M05 | M06 | M07 |
|---|---|---|---|---|---|---|
| **Guardian** | — | to-spec → to-tickets → tdd → implement → code-review | — | grilling / merge / code-review | code-review (ultra) | — |
| **HP** | to-spec → to-tickets → tdd → implement → code-review | — | — | grilling / merge / code-review | code-review (ultra) | — |
| **Batch** | — | — | to-spec → to-tickets → tdd → implement → code-review | grilling / merge / code-review | code-review (ultra) | — |
| **UI** | — | — | to-spec → prototype → tdd → implement → code-review | grilling / merge / code-review | code-review (ultra) | — |
| **Cross-Workstream** | — | — | — | grilling / merge / code-review | code-review (ultra) + security-review | handoff |

---

## Estimated Effort per Skill

| Skill | Duration | Effort (Hours) | Owner |
|---|---|---|---|
| domain-modeling | Optional | 2–4 | Guardian Lead |
| to-spec (Guardian) | 1 day | 8 | Guardian Lead |
| to-spec (HP) | 0.5 days | 4 | HP Lead |
| to-spec (Batch) | 0.75 days | 6 | Batch Lead |
| to-spec (UI) | 0.5 days | 4 | UI Lead |
| to-tickets (Guardian) | 0.5 days | 4 | Guardian Lead |
| to-tickets (HP) | 0.25 days | 2 | HP Lead |
| to-tickets (Batch) | 0.5 days | 4 | Batch Lead |
| prototype (UI) | 1 day | 8 | UI Designer |
| tdd (Guardian) | 3 days | 24 | Guardian Devs (3×) |
| tdd (HP) | 1 day | 8 | HP Dev |
| tdd (Batch) | 2 days | 16 | Batch Devs (2×) |
| tdd (UI) | 1 day | 8 | UI Dev |
| implement (Guardian) | 1 day | 8 | Guardian Devs |
| implement (HP) | 2 days | 8 | HP Dev |
| implement (Batch) | 2 days | 16 | Batch Devs |
| implement (UI) | 2 days | 16 | UI Dev |
| code-review (Guardian/HP/Batch/UI) | 1 day each | 4 × 4 | Tech Reviewer (1 day per workstream) |
| grilling (M05) | 0.5 days | 4 | All Teams |
| merge (M05) | 0.25 days | 2 | Tech Lead |
| code-review (M05 merged) | 0.5 days | 4 | Tech Reviewer |
| code-review (M06 ultra) | 1 day | 8 | Tech Reviewer + Architects |
| security-review (M06) | 0.5 days | 4 | Security Architect |
| handoff (M07) | 1 day | 8 | Architect + Owner |
| **TOTAL** | **Sep 8–19 (12 days)** | **~200 engineer-hours** | Multiple Teams |

---

## Document Control

**Classification:** Implementation Roadmap (Frozen)  
**Audience:** FlipFlop HQ Phase 2 Team  
**Distribution:** Internal  
**Change Authority:** Architect (for corrections), Owner (for major changes)  
**Retention:** Permanent (audit trail)  
**Roadmap Date:** 2026-09-07  
**Implementation Period:** Sep 8–19, 2026  
**Status:** READY FOR TEAM DISTRIBUTION  

---

**Phase 2 Skill Roadmap: LOCKED AND READY**

Authority Invariant: ZERO (hard-locked, non-negotiable)  
Failure Policy: FAIL_CLOSED (stale/missing/contradictory blocks)  
Matt Skills Sequence: domain-modeling → to-spec → to-tickets → tdd → implement → code-review  
Estimated Effort: ~200 engineer-hours (Sep 8–19)  

**Status: READY FOR IMPLEMENTATION KICKOFF (Sep 8 09:00 ET)**

