# Guardian Enforcement Phase 2 — Frozen Domain Model Specification

**Status:** PHASE_2_FROZEN_M01  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**Live Status:** OFF (LOCKED IMMUTABLE)  
**Date:** 2026-09-07  
**Owner:** Domain Architect  

---

## Executive Summary

This specification freezes the Guardian domain model for Phase 2 implementation. Seven core entities, four frozen tuples, eight sequential gates, and three integration points define a fail-closed deployment arbitration system with Authority=ZERO hard-locked throughout.

**Key invariant:** No code path may escalate authority, enable live trading, permit broker orders, or mutate control. All gates must pass for promotion. Stale, missing, or contradictory evidence blocks deployment.

---

## Domain Entities (7 Core)

### 1. ReleaseGate

**Purpose:** Permitting decision point. Evaluates evidence, applies policy, produces verdict.

**Immutable Fields:**
- `gate_id` (UUID): Unique identifier
- `gate_order` (1–8): Sequential position in evaluation pipeline
- `gate_version` (semver): Schema version
- `policy_ref` (UUID): Reference to AuthorityPolicy governing this gate
- `required_evidence_types` (array): Types of evidence required for evaluation

**Mutable Fields:**
- `stale_threshold_seconds` (int, default 300): Max age of fresh evidence

**Constraints:**
- Gate order 1–8, no gaps, no duplicates
- Policy reference must exist
- Immutable after first verdict issued
- Stale threshold >= 60 seconds

**Lifecycle:**
```
Created → Awaiting Evidence → Evaluates Evidence → Issues Verdict → Sealed
```

---

### 2. GateVerdict

**Purpose:** Immutable outcome of gate evaluation. Binary domain: PASS, BLOCKED, NOT_PROVEN.

**Immutable Fields:**
- `verdict_id` (UUID): Unique verdict identifier
- `gate_id` (UUID): Which gate issued this verdict
- `correlation_id` (UUID): Links verdict to deployment candidate
- `verdict` (enum: PASS | BLOCKED | NOT_PROVEN)
- `event_time` (timestamp): When verdict was issued
- `knowledge_time` (timestamp): When evidence was known
- `authority_used` (enum: ZERO): Authority level at verdict

**Mutable Fields:**
- `reasoning` (string): Human-readable explanation
- `evidence_id` (UUID): Primary evidence evaluated
- `secondary_evidence_ids` (array): Supporting evidence
- `policy_hash` (SHA256): Hash of applied policy

**Constraints:**
- Verdict immutable after creation (audit-only append)
- event_time <= knowledge_time
- authority_used must be ZERO (hard-locked)
- Stale evidence (> gate.stale_threshold) forces NOT_PROVEN
- Gate ID foreign key must exist

**Verdicts Explained:**
- **PASS:** All required checks met. Candidate may proceed.
- **BLOCKED:** Blocking condition detected (mismatch, policy violation, canary failure, evidence contradiction, stale/missing evidence, authority escalation attempt).
- **NOT_PROVEN:** Required evidence unavailable or incomplete. Gate cannot yet decide.

---

### 3. EvidenceRecord

**Purpose:** Factual observation about deployment candidate, infrastructure, or system state. Sources: hash verification, canary results, policy evaluation, machine health.

**Immutable Fields:**
- `evidence_id` (UUID): Unique identifier
- `evidence_type` (string): Category (e.g., HASH_MATCH, CANARY_PASS, POLICY_CHECK, MACHINE_HEALTH)
- `source_system` (string): Origin (e.g., HP_INFRA, GUARDIAN_HASH, CANARY_ENGINE)
- `observation` (JSON): Fact payload (structure varies by type)
- `observed_at` (timestamp): When fact was observed
- `recorded_at` (timestamp): When Guardian recorded it
- `checksum` (SHA256): Integrity seal

**Mutable Fields:**
- `is_contradicted` (boolean, default false): Newer evidence contradicts this
- `contradicted_by` (array): Evidence IDs that contradict this

**Constraints:**
- Evidence ID globally unique
- Evidence type immutable
- Observation payload immutable (copy-on-write)
- Observed_at <= recorded_at
- No cascade delete (retention for audit)

---

### 4. AuthorityPolicy

**Purpose:** Rules governing what evidence suffices for gate verdict. Defines thresholds, required checks, contradictions.

**Immutable Fields:**
- `policy_id` (UUID): Unique identifier
- `policy_name` (string): Human-readable name
- `policy_version` (semver): Version number
- `authority_level` (enum: ZERO): Hard-locked to ZERO
- `target_gate` (UUID): Which gate this policy governs
- `required_checks` (array): Mandatory checks (e.g., SCHEMA_VALID, HASH_MATCH, NO_CONTRADICTIONS)
- `contradictory_states` (array): Evidence combinations that force BLOCKED

**Mutable Fields:**
- `all_checks_must_pass` (boolean, default true)
- `stale_blocks` (boolean, default true)
- `owner_approval_required` (boolean, default false)

**Constraints:**
- Immutable after first use
- all_checks_must_pass defaults to true (fail-closed)
- stale_blocks defaults to true (fail-closed)
- Cannot be modified after locked_at timestamp

---

### 5. DecisionCartridge

**Purpose:** Immutable snapshot of a deployment candidate's journey through all 8 gates. Final verdict bundle.

**Immutable Fields:**
- `cartridge_id` (UUID): Unique identifier
- `correlation_id` (UUID): Links to deployment candidate
- `candidate_id` (UUID): Deployment candidate ID
- `gate_verdicts` (array): All 8 gate results
- `final_verdict` (enum: PASS | BLOCKED | NOT_PROVEN): Aggregate verdict
- `evidence_root_hash` (SHA256): Hash of all evidence used
- `policy_root_hash` (SHA256): Hash of all policies applied
- `authority` (enum: ZERO): Authority at cartridge sealing
- `created_at` (timestamp)

**Constraints:**
- All 8 gates must have verdicts before cartridge completion
- final_verdict = PASS only if all 8 gates = PASS
- final_verdict = BLOCKED if any gate = BLOCKED
- final_verdict = NOT_PROVEN if any gate = NOT_PROVEN and none = BLOCKED
- No modification after creation

---

### 6. CanaryRun

**Purpose:** Controlled test deployment of candidate artifact to canary cohort. Generates evidence for gate evaluation.

**Immutable Fields:**
- `canary_id` (UUID): Unique identifier
- `candidate_id` (UUID): Deployment candidate under test
- `correlation_id` (UUID): Traceability ID
- `artifact_hash` (SHA256): Hash of artifact being tested
- `cohort_machines` (array): Machine identifiers in cohort
- `deployment_time` (timestamp): When canary started
- `observation_window_seconds` (int, default 300): Duration of observation

**Mutable Fields:**
- `result` (enum: PASS | FAIL | INCOMPLETE | TIMEOUT)
- `error_rate` (float, 0–1): Fraction of machines with errors
- `latency_p99_ms` (float): 99th percentile latency
- `rollback_triggered` (boolean)
- `evidence_id` (UUID): EvidenceRecord generated by this run

**Constraints:**
- One active canary per candidate
- Result immutable after observation_window_seconds
- Error rate in [0, 1]
- Rollback_triggered only if result != PASS
- Cohort size <= total machine fleet

---

### 7. DeploymentCandidate

**Purpose:** Artifact bundle awaiting gate evaluations. Contains hashes, passport, and links to gate verdicts.

**Immutable Fields:**
- `candidate_id` (UUID): Unique identifier
- `correlation_id` (UUID): Traceability ID
- `artifact_hashes` (object): {strategy_sha256, engine_sha256, ui_sha256}
- `passport_hash` (SHA256): Hash of CONTROL passport
- `side` (enum: BUY | SELL | BOTH): Which strategy side(s)
- `source_system` (string): Origin (e.g., NINJA_INFRA, DEV_BRANCH)
- `authority` (enum: ZERO): Authority at creation
- `created_at` (timestamp)

**Mutable Fields:**
- `gate_results` (array): {gate_id, verdict_id, verdict} — populated as gates evaluate
- `canary_evidence_id` (UUID): From canary run
- `decision_cartridge_id` (UUID): Final DecisionCartridge
- `owner_approval_id` (UUID): Owner who approved (if policy requires)
- `promotion_ready` (boolean): true only if final_verdict = PASS
- `status` (enum): STAGING → IN_GATES → (BLOCKED | APPROVED) → (DEPLOYED | ROLLED_BACK)

**Constraints:**
- Artifact hashes immutable
- Promotion_ready = true only if DecisionCartridge.final_verdict = PASS
- Owner_approval_id required if gate policy requires approval
- Status transitions one-way (no reversals)
- Authority always ZERO

---

## Entity Relationships

| Source | Target | Cardinality | Foreign Key | Semantics |
|--------|--------|-------------|-------------|-----------|
| ReleaseGate | GateVerdict | 1:N | gate_id | Gate produces many verdicts (one per candidate) |
| GateVerdict | EvidenceRecord | 1:N | evidence_id | Verdict references primary and secondary evidence |
| AuthorityPolicy | ReleaseGate | 1:N | policy_ref | Policy governs one or more gates |
| DeploymentCandidate | DecisionCartridge | 1:1 | decision_cartridge_id | Each candidate gets one final cartridge |
| DeploymentCandidate | CanaryRun | 1:N | candidate_id | Candidate may have multiple canary runs |
| CanaryRun | EvidenceRecord | 1:1 | evidence_id | Canary run generates evidence |
| DeploymentCandidate | EvidenceRecord | 1:N | — | Candidate accumulates evidence from multiple sources |
| DecisionCartridge | GateVerdict | 1:N | — | Cartridge seals all verdicts from candidate's gate journey |

---

## Frozen Tuples

### AuthorityTuple

```
(authority, live_enabled, broker_orders_allowed, control_mutation_allowed, owner_approval_id)
```

**Values (IMMUTABLE):**
- `authority` = ZERO (no escalation permitted)
- `live_enabled` = false (paper-only mode)
- `broker_orders_allowed` = false (no real orders)
- `control_mutation_allowed` = false (no artifact changes)
- `owner_approval_id` = UUID or null (depends on policy)

**Semantics:** Defines hard governance boundary. Checked on every gate entry. No code path may violate these constraints.

**Constraint Checks:**
```
IF authority != ZERO THEN FAIL_CLOSED
IF live_enabled != false THEN FAIL_CLOSED
IF broker_orders_allowed != false THEN FAIL_CLOSED
IF control_mutation_allowed != false THEN FAIL_CLOSED
```

---

### StrategyIdentityTuple

```
(side, sha256, passport_id, release_gate_version, verification_state)
```

**Example:**
```
(BUY, "657F9C62DEADBEEFCAFEBABE...", "FLIP_FLOP_CONTROL_V1.4", "1.0.0", PROVEN)
```

**Semantics:** Uniquely identifies a strategy artifact and its verification status.

**Fields:**
- `side` (IMMUTABLE): BUY or SELL (independent strategies)
- `sha256` (IMMUTABLE): Content hash of strategy code
- `passport_id` (IMMUTABLE): Identifier from CONTROL passport
- `release_gate_version` (IMMUTABLE): Gate schema version
- `verification_state` (MUTABLE): ASSERTED | PROVEN | CONTRADICTED

**Rules:**
- BUY and SELL are separate identity tuples (each requires distinct hash match and canary)
- Verification state updated by Gate 2 (HASH_INTEGRITY) and Gate 6 (EVIDENCE_CONSISTENCY)
- Once CONTRADICTED, candidate blocked and held for human review

---

### GateDecisionTuple

```
(gate_id, correlation_id, input_hashes, evidence_id, verdict, event_time, knowledge_time)
```

**Semantics:** Immutable record of a gate's single decision. Audit trail cannot be modified. Verdict binding: once PASS or BLOCKED, cannot be revisited.

**Fields:**
- `gate_id` (IMMUTABLE): Which gate
- `correlation_id` (IMMUTABLE): Links to deployment candidate
- `input_hashes` (IMMUTABLE): SHA256 array of all input evidence
- `evidence_id` (IMMUTABLE): Primary evidence evaluated
- `verdict` (IMMUTABLE): PASS | BLOCKED | NOT_PROVEN
- `event_time` (IMMUTABLE): When issued
- `knowledge_time` (IMMUTABLE): When evidence was known

**Constraints:**
- event_time <= knowledge_time (cannot know before decision)
- input_hashes non-empty
- verdict one of three allowed states
- evidence_id must exist in EvidenceRecord table

---

### DeploymentCandidateTuple

```
(candidate_id, artifact_hashes, passport_hash, gate_results, canary_evidence_id, authority, owner_approval_id)
```

**Semantics:** Deployment bundle with fixed content, mutable gate journey. Cannot change artifacts after creation. Gate results and canary evidence append-only.

**Fields:**
- `candidate_id` (IMMUTABLE): Unique ID
- `artifact_hashes` (IMMUTABLE): {strategy_sha256, engine_sha256, ui_sha256}
- `passport_hash` (IMMUTABLE): CONTROL passport hash
- `gate_results` (APPEND-ONLY): {gate_id, verdict} entries
- `canary_evidence_id` (MUTABLE): From CanaryRun
- `authority` (IMMUTABLE): ZERO
- `owner_approval_id` (MUTABLE, nullable): Owner ID if policy requires

**Promotion Rules:**
- **To APPROVED:** Requires `gate_results.all_verdicts = PASS` AND (owner_approval_id present if policy requires)
- **To DEPLOYED:** Requires `decision_cartridge.final_verdict = PASS` AND no contradictions in evidence
- **To BLOCKED:** Any gate verdict = BLOCKED
- **To ROLLED_BACK:** Canary failure OR evidence contradiction detected

---

## Eight Gates + Verdicts

### Gate 1: SCHEMA_AND_IDENTITY

**Purpose:** Validates deployment candidate structure and artifact identity.

**Required Checks:**
- Candidate schema valid
- Artifact hashes present (strategy, engine, UI)
- Passport hash present
- Correlation ID valid and unique

**Blocking Conditions:**
- Schema validation fails
- Any required hash missing
- Correlation ID malformed or duplicated

**Not-Proven Conditions:**
- Passport not yet available from CONTROL

**Possible Verdicts:** PASS | BLOCKED | NOT_PROVEN

---

### Gate 2: HASH_INTEGRITY

**Purpose:** Verifies artifact content hashes match expected values from source.

**Required Checks:**
- strategy_sha256_matches
- engine_sha256_matches
- ui_sha256_matches
- passport_hash_matches

**Blocking Conditions:**
- Any artifact hash mismatch
- Passport hash mismatch
- Hash source contradicts stored hash
- Evidence contradiction (multiple hash sources disagree)

**Not-Proven Conditions:**
- Artifact not yet fetched
- Hash source unavailable
- Hash verification in progress

**Possible Verdicts:** PASS | BLOCKED | NOT_PROVEN

---

### Gate 3: AUTHORITY_POLICY_COMPLIANCE

**Purpose:** Confirms all policy checks pass: authority=ZERO, live=false, no mutations.

**Required Checks:**
- authority_equals_zero
- live_enabled_false
- broker_orders_false
- control_mutation_false
- policy_schema_valid
- no_authority_escalation_attempted

**Blocking Conditions:**
- authority != ZERO
- live_enabled = true
- broker_orders_allowed = true
- control_mutation_allowed = true
- Any attempt to escalate authority

**Not-Proven Conditions:**
- Policy not yet loaded
- Policy schema validation in progress

**Possible Verdicts:** PASS | BLOCKED | NOT_PROVEN

---

### Gate 4: MACHINE_HEALTH_AND_READINESS

**Purpose:** Verifies HP infrastructure is healthy and ready to receive deployment.

**Required Checks:**
- no_open_errors_in_fleet
- all_machines_healthy
- fencing_token_valid
- heartbeat_recent (< 60 seconds)
- clock_within_tolerance (< 5 seconds skew)

**Blocking Conditions:**
- Any machine in error state
- Fencing token expired
- Clock skew > 5 seconds
- Heartbeat stale > 60 seconds
- Any machine reports restart/sleep/recovery anomaly

**Not-Proven Conditions:**
- Heartbeat not yet received
- Health check in progress
- Fencing token validation pending

**Possible Verdicts:** PASS | BLOCKED | NOT_PROVEN

---

### Gate 5: CANARY_EXECUTION

**Purpose:** Runs controlled canary deployment and evaluates results.

**Required Checks:**
- canary_deployment_success
- error_rate_lt_threshold (< 5%)
- latency_p99_lt_threshold (< 200 ms)
- no_rollback_triggered
- observation_window_complete (300 seconds)

**Blocking Conditions:**
- Canary deployment fails
- Error rate > 5%
- Latency p99 > 200 ms
- Rollback triggered
- Any critical error in cohort
- Canary timeout (> 5 minutes)

**Not-Proven Conditions:**
- Canary still running
- Observation window not complete
- Canary results not yet available

**Possible Verdicts:** PASS | BLOCKED | NOT_PROVEN

---

### Gate 6: EVIDENCE_CONSISTENCY

**Purpose:** Detects and blocks contradictory evidence from multiple sources.

**Required Checks:**
- no_contradicted_hashes
- no_contradicted_policies
- no_contradicted_canary_results
- evidence_timestamps_consistent
- event_ordering_valid (no temporal violations)

**Blocking Conditions:**
- Evidence contradiction detected
- Hash conflict (two different hashes for same artifact)
- Policy conflict (contradictory checks from different sources)
- Canary contradiction with hash evidence
- Temporal ordering violation (newer evidence contradicts older)
- is_contradicted flag set on any required evidence

**Not-Proven Conditions:**
- Evidence not yet collected
- Contradiction resolution pending

**Possible Verdicts:** PASS | BLOCKED | NOT_PROVEN

---

### Gate 7: FRESHNESS_AND_STALENESS

**Purpose:** Enforces evidence freshness: blocks if any evidence stale or missing.

**Stale Threshold:** 300 seconds (hard-locked)

**Required Checks:**
- all_evidence_fresh_le_stale_threshold
- no_missing_required_evidence
- hash_evidence_age_lt_300s
- canary_evidence_age_lt_300s
- policy_evidence_age_lt_300s

**Blocking Conditions:**
- Any evidence older than 300 seconds
- Required evidence missing
- Evidence not yet timestamp-verified
- Evidence recorded > 300 seconds ago

**Not-Proven Conditions:**
- Evidence collection in progress
- Age verification pending

**Possible Verdicts:** PASS | BLOCKED | NOT_PROVEN

---

### Gate 8: FINAL_ARBITER

**Purpose:** Aggregate gate: confirms all prior gates passed, no escalation, owner approval if required.

**Required Checks:**
- all_prior_gates_passed (gates 1–7)
- authority_still_zero
- no_authority_escalation_detected
- owner_approval_present_if_required
- decision_cartridge_sealed_properly

**Blocking Conditions:**
- Any prior gate = BLOCKED
- Any prior gate = NOT_PROVEN
- Authority escalation attempted
- Owner approval missing when policy requires
- Decision cartridge not properly sealed
- Evidence contradictions present

**Not-Proven Conditions:**
- Decision cartridge not yet assembled
- Prior gates still evaluating

**Possible Verdicts:** PASS | BLOCKED | NOT_PROVEN

**Special Rules:**
- If any gate 1–7 = NOT_PROVEN, gate 8 = NOT_PROVEN
- If any gate 1–7 = BLOCKED, gate 8 = BLOCKED
- Only if all gates 1–7 = PASS does gate 8 evaluate to PASS

---

## Verdict Types

### PASS

**Condition:** Gate evidence requirements met. Candidate may proceed.

**Semantics:** Affirmative. All required checks passed, no blocking conditions detected, evidence fresh and consistent.

**Downstream Effect:**
- Gate verdict recorded in DecisionCartridge
- If all 8 gates = PASS, DecisionCartridge.final_verdict = PASS
- DeploymentCandidate.promotion_ready = true
- Candidate eligible for promotion to APPROVED status

---

### BLOCKED

**Condition:** Evidence negates gate requirement. Candidate cannot proceed.

**Semantics:** Negative. Blocking condition detected:
- Hash mismatch
- Policy violation
- Canary failure
- Evidence contradiction
- Stale evidence
- Authority escalation attempt
- Missing required checks
- Machine health issue
- Fencing/clock anomaly

**Downstream Effect:**
- DecisionCartridge.final_verdict = BLOCKED
- DeploymentCandidate.status = BLOCKED
- Candidate held (no recovery without operator intervention to fix root cause)
- Evidence marked as contradicted (if applicable)
- Blocked gates recorded in DecisionCartridge.blocking_gates[]

---

### NOT_PROVEN

**Condition:** Evidence unavailable or incomplete. Gate cannot decide.

**Semantics:** Indeterminate. Required evidence not yet available, still collecting (e.g., canary running), or resolution pending.

**Downstream Effect:**
- DecisionCartridge.final_verdict = NOT_PROVEN (if no gate = BLOCKED)
- DeploymentCandidate.status = IN_GATES (remains waiting)
- Candidate waits for missing evidence (capped at 5-minute timeout per gate)
- If any gate times out on NOT_PROVEN, system escalates to BLOCKED
- Not-proven gates recorded in DecisionCartridge.not_proven_gates[]

---

## Fail-Closed Constraints (8 Hard Rules)

### FC01: NO_AUTHORITY_ESCALATION

**Rule:** Authority must always be ZERO. No code path may escalate authority. Any attempt triggers BLOCKED verdict and FAIL_CLOSED.

**Enforcement:** Gate 3 and Gate 8 check authority == ZERO. Violation = BLOCKED.

**Test:** Attempt to promote candidate with authority=ONE. Must result in BLOCKED with reasoning "authority_escalation_detected".

---

### FC02: STALE_EVIDENCE_BLOCKS

**Rule:** Evidence older than gate.stale_threshold (300 seconds) forces BLOCKED verdict. Never proceed with stale evidence.

**Enforcement:** Gate 7 (FRESHNESS_AND_STALENESS) verifies all evidence timestamps. If any evidence.age > 300s, verdict = BLOCKED.

**Test:** Inject evidence with timestamp 301 seconds old. Must result in BLOCKED.

---

### FC03: CONTRADICTED_EVIDENCE_BLOCKS

**Rule:** If newer evidence contradicts older evidence (hash mismatch, policy reversal, canary failure), verdict = BLOCKED.

**Enforcement:** Gate 6 (EVIDENCE_CONSISTENCY) detects contradictions. EvidenceRecord.is_contradicted flag marks contradicted evidence.

**Test:** Submit hash A, then hash B for same artifact. Second verdict must be BLOCKED with reasoning "hash_contradiction".

---

### FC04: MISSING_REQUIRED_EVIDENCE_BLOCKS

**Rule:** If any gate's required_evidence_types are missing, verdict = BLOCKED or NOT_PROVEN (depending on collection status).

**Enforcement:** Each gate lists required_checks. Missing check = NOT_PROVEN. If timeout > 5 minutes, = BLOCKED.

**Test:** Attempt to promote without hash verification. Must result in NOT_PROVEN (or BLOCKED after timeout).

---

### FC05: CANARY_FAILURE_BLOCKS

**Rule:** If canary error_rate > 5% or latency_p99 > 200 ms or rollback triggered, verdict = BLOCKED.

**Enforcement:** Gate 5 (CANARY_EXECUTION) evaluates CanaryRun.result. Failure = BLOCKED.

**Test:** Inject canary with error_rate=10%. Must result in BLOCKED.

---

### FC06: HASH_MISMATCH_BLOCKS

**Rule:** If artifact content hash doesn't match expected value, verdict = BLOCKED.

**Enforcement:** Gate 2 (HASH_INTEGRITY) verifies all hashes. Mismatch = BLOCKED.

**Test:** Submit artifact with wrong hash. Must result in BLOCKED.

---

### FC07: ALL_GATES_MUST_PASS_FOR_PROMOTION

**Rule:** DeploymentCandidate.promotion_ready = true only if DecisionCartridge.final_verdict = PASS (all 8 gates = PASS).

**Enforcement:** DecisionCartridge logic:
```
final_verdict = PASS IFF all gate_verdicts[0:8].verdict = PASS
final_verdict = BLOCKED IF any gate_verdict.verdict = BLOCKED
final_verdict = NOT_PROVEN IF any gate_verdict.verdict = NOT_PROVEN AND none = BLOCKED
```

**Test:** 7 gates = PASS, 1 gate = NOT_PROVEN. DecisionCartridge.final_verdict must be NOT_PROVEN.

---

### FC08: NO_MANUAL_OVERRIDE_OF_GATE_VERDICTS

**Rule:** Once a gate verdict is issued, it cannot be modified or overridden. All changes require new gate evaluation.

**Enforcement:** GateVerdict.verdict immutable after creation. Any change requires new verdict_id.

**Test:** Attempt to modify verdict_id = X. Must fail with immutability constraint violation.

---

## Integration Points

### HP Infrastructure (24/7 Worker Machines)

**Guardian Role:** Source of machine health evidence, fencing tokens, heartbeats. Receives promotion signals.

**Inputs to Guardian:**
- MachineHealthReport: {machine_id, health_status, error_count, last_heartbeat, clock_offset}
- FencingTokenProof: {token_hash, epoch, expiry, signature}
- ArtifactDeploymentManifest: {candidate_id, artifact_paths, checksums}

**Outputs from Guardian:**
- Gate4Verdict: PASS|BLOCKED|NOT_PROVEN (gates artifact deployment)
- Gate7Verdict: Freshness check (rejects stale health reports)
- PromotionApproval: {candidate_id, authority=ZERO, sealed_decision_cartridge}

**Constraints:**
- Heartbeat must arrive within 60 seconds
- Clock skew must be < 5 seconds
- Fencing token must not be expired
- No machine can receive artifact until Gate 4 + Gate 5 = PASS
- Restart/sleep/clock-jump anomalies block Gate 4

---

### NinjaTrader Batch Engine (Order/Execution Interface)

**Guardian Role:** Consumes promotion decisions. Receives no-go signals for BLOCKED candidates. Follows Guardian arbiter.

**Inputs to Guardian:**
- StrategyExecutionIntent: {side, entry_ticks, stop_ticks, target_ticks, quantity, validity}
- OrderExecutionProof: {order_id, fill_price, fill_time, timestamp, broker_acknowledgment}

**Outputs from Guardian:**
- PromotionApproval: {candidate_id, all_gates_passed, canary_evidence_id, decision_cartridge_sealed}
- BLOCKED_Signal: {candidate_id, blocking_gate_id, reason, no_retry_until=timestamp}
- NOT_PROVEN_Signal: {candidate_id, waiting_gates, estimated_resolution_time}

**Constraints:**
- NinjaTrader Batch must not execute orders if Guardian verdict = BLOCKED
- NinjaTrader Batch must wait for all 8 gates if Guardian verdict = NOT_PROVEN
- NinjaTrader Batch receives NO authority escalation signals (Authority=ZERO always)
- No live orders permitted (live_enabled = false)
- No broker orders sent (broker_orders_allowed = false)

---

### UI Control Center (Phone, Tablet, Desktop)

**Guardian Role:** Displays Guardian state, gate verdicts, evidence status, promotion readiness. Shows truth age and stale warnings.

**Inputs to Guardian:**
- DashboardStateRequest: {user_role, include_sensitive_data}
- ManualApprovalRequest: {owner_id, candidate_id, approval_signature} (optional, policy-dependent)

**Outputs from Guardian:**
- GuardianStateSnapshot: {phase, authority, gates[], verdicts[], evidence_status, final_verdict, promotion_ready, truth_age_seconds}
- TruthBar: {is_fresh, age_seconds, stale_since_timestamp, warning_level}
- PromotionStatus: {candidate_id, gate_results, blocking_gates, approval_status}

**Constraints:**
- UI must display truth_age and stale warnings prominently
- UI must NOT grant authority or override Guardian verdicts
- UI must show Authority=ZERO in all screens (visual enforcement)
- UI must distinguish observed health from Guardian authority (no confusion)
- Admin/public toggle filters sensitive data
- No UI component can trigger gate re-evaluation (read-only)

---

## Authority Invariant (Hard-Locked)

```
AUTHORITY = ZERO (no escalation)
LIVE = OFF (paper-only)
BROKER_ORDERS = NONE (no real orders)
CONTROL_MUTATION = NONE (no artifact changes)
FAILURE_POLICY = FAIL_CLOSED (stale/missing/contradictory evidence blocks)
```

**Status:** CANNOT CHANGE. Every implementation must verify this invariant.

**Enforcement Points:**
1. Gate 3: AUTHORITY_POLICY_COMPLIANCE checks authority == ZERO
2. Gate 8: FINAL_ARBITER re-verifies authority == ZERO
3. UI: Visual display of Authority=ZERO in all screens
4. HP Infra: Never accepts live orders or broker commands
5. NinjaTrader Batch: Only receives PASS/BLOCKED/NOT_PROVEN verdicts, never authority escalation

---

## Critical Risks (Phase 2)

| ID | Risk | Severity | Mitigation |
|----|----|----------|-----------|
| R01 | Canary PASS lacks closure evidence | CRITICAL | Gate 5 requires explicit evidence. Evidence must be fresh, timestamped, and non-contradicted. |
| R04 | HP restart/sleep/clock jump | CRITICAL | Gate 4 monitors heartbeat/clock. Gate 7 enforces freshness. Temporal ordering validated in Gate 6. |
| R03 | UI mistaken for authority | HIGH | Visual lock: Authority=ZERO displayed on all screens. UI docs emphasize read-only role. |

---

## Phase 2 Implementation Timeline

| Milestone | Dates | Status | Owner |
|-----------|-------|--------|-------|
| M01 — Freeze (this doc) | Sep 8, 09–18 ET | READY | Technical Architect |
| M02 — HP Infra | Sep 8–11 ET | PARALLEL | HP 24/7 |
| M03 — Guardian | Sep 8–12 ET | PARALLEL | Guardian Enforcement |
| M04 — UI | Sep 8–14 ET | PARALLEL | UI Design |
| M05 — Integration | Sep 15–16 ET | WAITING | All lanes |
| M06 — Cert | Sep 17–18 ET | WAITING | Architect + Guardian |
| M07 — Owner review | Sep 19 ET | WAITING | Owner |

**Critical path:** M01 → M03 → M05 → M06 → M07

---

## Implementation Checklist (Phase 2 Lanes)

### Guardian Enforcement Lane (M03: Sep 8–12)

**Deliverables:**
- [ ] 8-gate engine (Gates 1–8 implement exact logic above)
- [ ] Hash verifier (Gate 2 SHA256 matching)
- [ ] Fail-closed sentinel (Gates 3, 7, 8 enforce constraints)
- [ ] Bitemporal receipts (event_time vs knowledge_time audit trail)

**Exit Criteria:**
- [ ] 8/8 gates produce verdicts
- [ ] Negative authority tests pass (authority=ONE rejected)
- [ ] Stale evidence tests pass (300+ second old evidence blocked)
- [ ] Contradiction tests pass (hash conflicts detected and blocked)

### UI Design Lane (M04: Sep 8–14)

**Deliverables:**
- [ ] Phone cockpit (compact authority display)
- [ ] Tablet workspace (side-by-side gates + evidence)
- [ ] Desktop full (8 gates, truth bar, decision cartridge)
- [ ] Truth bar (age_seconds, stale warning, refresh)
- [ ] Guardian seal (Authority=ZERO visual lock)

**Exit Criteria:**
- [ ] Critical truth visible on all form factors
- [ ] Stale detection working (> 300s = red)
- [ ] No UI component grants authority

### HP 24/7 Infrastructure Lane (M02: Sep 8–11)

**Deliverables:**
- [ ] Fencing token (heartbeat + epoch)
- [ ] Restart recovery (reconstruct state, no re-send)
- [ ] Sleep/clock detection (5-second tolerance)
- [ ] Durable storage (evidence persists across restart)

**Exit Criteria:**
- [ ] Duplicate writer rejected
- [ ] Restart reconstructs state
- [ ] Restore drill passes

---

## Appendix: Glossary

| Term | Definition |
|------|-----------|
| **Authority** | Permission level for deployment actions. Frozen at ZERO (no escalation). |
| **Candidate** | Deployment artifact bundle awaiting gate evaluations. |
| **Cartridge** | Immutable snapshot of all 8 gate verdicts. Final decision record. |
| **Correlation ID** | UUID linking candidate → verdicts → evidence → decision cartridge. |
| **Evidence** | Factual observation from source system (hash, canary, policy, health). |
| **Gate** | Sequential permitting checkpoint. Evaluates evidence, applies policy, produces verdict. |
| **Live** | Authority to execute real broker orders. Locked OFF. |
| **NOT_PROVEN** | Indeterminate verdict: evidence unavailable or incomplete. |
| **Passport** | CONTROL artifact identifier. Immutable. |
| **PASS** | Affirmative verdict: all checks met, proceed. |
| **BLOCKED** | Negative verdict: blocking condition detected, candidate held. |
| **Stale** | Evidence older than gate.stale_threshold (300 seconds). Blocks promotion. |
| **Truth** | Evidence freshness indicator. Age_seconds displayed in UI. |
| **Verdict** | Gate outcome: PASS, BLOCKED, or NOT_PROVEN. Immutable after issue. |

---

**Document Frozen:** 2026-09-07T00:00:00Z  
**Authority Invariant:** LOCKED_IMMUTABLE  
**Next Phase:** Implementation M02/M03 parallel lanes begin 2026-09-08  
**Contact:** Domain Architect

