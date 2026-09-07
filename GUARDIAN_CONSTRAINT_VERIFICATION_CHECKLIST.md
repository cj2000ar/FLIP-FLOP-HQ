# Guardian Domain Model — Constraint Verification Checklist

**Status:** PHASE_2_FROZEN  
**Purpose:** Verification that implementation adheres to frozen domain model  
**Approver:** Domain Architect + Guardian Enforcement Lead  
**Date:** 2026-09-07  

---

## Pre-Implementation Verification (M01 Exit Criteria)

### Authority Invariant Lock

- [ ] Authority enum defines only ZERO (no ONE, no SCALED, no escalation options in schema)
- [ ] AuthorityTuple immutable after creation (no update path in code)
- [ ] All 7 entity models hardcoded authority=ZERO default (not read from input)
- [ ] Gate 3 (AUTHORITY_POLICY_COMPLIANCE) implements immutable check on authority field
- [ ] Gate 8 (FINAL_ARBITER) re-verifies authority == ZERO before promotion approval
- [ ] Database schema constraint: authority column has CHECK (authority = 'ZERO')
- [ ] API validation: any input with authority != ZERO rejected at entry point

**Verification Method:** Code review + schema audit + static analysis  
**Pass Criteria:** All 7 checks completed and signed off

---

### Entity Immutability Guarantees

**ReleaseGate:**
- [ ] gate_id, gate_order, gate_version immutable after creation
- [ ] policy_ref immutable after first verdict
- [ ] Database: no UPDATE path on these fields
- [ ] Code: constructor only, no setters

**GateVerdict:**
- [ ] verdict_id, gate_id, correlation_id, verdict, event_time immutable (append-only record)
- [ ] Database: INSERT only, no UPDATE
- [ ] API: no PATCH/PUT endpoint for verdict

**EvidenceRecord:**
- [ ] evidence_id, evidence_type, source_system, observation immutable
- [ ] observed_at, recorded_at immutable
- [ ] Database: INSERT only, no UPDATE on immutable fields
- [ ] is_contradicted only set via explicit contradiction detection (not user input)

**AuthorityPolicy:**
- [ ] policy_id, policy_version, authority_level, target_gate, required_checks immutable
- [ ] locked_at timestamp prevents all modifications once set
- [ ] Database: INSERT only, no UPDATE after locked_at

**DecisionCartridge:**
- [ ] cartridge_id, correlation_id, candidate_id, gate_verdicts, final_verdict immutable
- [ ] Database: INSERT only, no UPDATE
- [ ] Sealed before any verdict revision can occur

**CanaryRun:**
- [ ] canary_id, candidate_id, correlation_id, artifact_hash, deployment_time immutable
- [ ] result immutable after observation_window_seconds elapses
- [ ] Database: result field UPDATE-allowed only once, before marked immutable

**DeploymentCandidate:**
- [ ] candidate_id, correlation_id, artifact_hashes, passport_hash, side immutable
- [ ] source_system, created_at immutable
- [ ] gate_results, canary_evidence_id, owner_approval_id APPEND-only (new verdicts added, not replaced)
- [ ] promotion_ready derived from DecisionCartridge.final_verdict (not directly settable)

**Verification Method:** ORM audit (check allowable operations per entity)  
**Pass Criteria:** Immutability enforced by database schema + ORM configuration

---

## Gate Logic Verification (M03 Start Checklist)

### Gate 1: SCHEMA_AND_IDENTITY

- [ ] Checks candidate_schema version against whitelist (known versions only)
- [ ] Rejects schema version not in whitelist (BLOCKED verdict)
- [ ] Validates artifact_hashes object structure: exactly 3 keys (strategy, engine, ui)
- [ ] Each hash field: non-empty string, SHA256 format (64 hex chars or base64)
- [ ] passport_hash: non-empty, SHA256 format
- [ ] correlation_id: valid UUID format
- [ ] correlation_id uniqueness check: query database, reject if exists
- [ ] Verdict immutable after issuance

**Test Cases:**
```
PASS_CASE_1: Valid schema, 3 hashes, passport, unique correlation_id
  → Verdict = PASS, Reasoning = "schema_and_identity_valid"

BLOCK_CASE_1: Unknown schema version
  → Verdict = BLOCKED, Reasoning = "schema_version_unknown"

BLOCK_CASE_2: Missing engine hash
  → Verdict = BLOCKED, Reasoning = "artifact_hash_missing"

BLOCK_CASE_3: Duplicate correlation_id in database
  → Verdict = BLOCKED, Reasoning = "correlation_id_duplicate"

NOT_PROVEN_CASE_1: Passport not available
  → Verdict = NOT_PROVEN, Reasoning = "passport_hash_missing"
```

**Pass Criteria:** 5/5 test cases pass + verdict immutability verified

---

### Gate 2: HASH_INTEGRITY

- [ ] Fetches artifact_hashes from source system (HP_INFRA, ENGINE_BUILD, UI_BUILD, CONTROL)
- [ ] Compares source_sha256(strategy) == candidate.artifact_hashes.strategy
- [ ] Compares source_sha256(engine) == candidate.artifact_hashes.engine
- [ ] Compares source_sha256(ui) == candidate.artifact_hashes.ui
- [ ] Compares source_sha256(passport) == candidate.passport_hash
- [ ] Detects contradiction: if two different sources report different hash for same artifact
- [ ] On contradiction, marks evidence.is_contradicted = true and returns BLOCKED
- [ ] Timeout mechanism: if source unavailable after 5 minutes, returns NOT_PROVEN

**Test Cases:**
```
PASS_CASE_1: All 4 hashes match from sources
  → Verdict = PASS, Reasoning = "hash_integrity_verified"

BLOCK_CASE_1: Source reports different strategy hash
  → Verdict = BLOCKED, Reasoning = "artifact_strategy_hash_mismatch"

BLOCK_CASE_2: Two sources disagree on same hash
  → Verdict = BLOCKED, Reasoning = "hash_contradiction_detected"

NOT_PROVEN_CASE_1: Source not yet available
  → Verdict = NOT_PROVEN, Reasoning = "artifact_source_unavailable"
```

**Pass Criteria:** 4/4 test cases pass + contradiction detection verified

---

### Gate 3: AUTHORITY_POLICY_COMPLIANCE

- [ ] Reads AuthorityTuple for candidate
- [ ] Hard check: authority == ZERO (no conditionals, no fallback)
  - [ ] If authority != ZERO, immediately return BLOCKED with "authority_not_zero"
- [ ] Hard check: live_enabled == false (no conditionals, no fallback)
  - [ ] If live_enabled != false, immediately return BLOCKED with "live_enabled_violation"
- [ ] Hard check: broker_orders_allowed == false
  - [ ] If broker_orders_allowed != false, immediately return BLOCKED with "broker_orders_enabled"
- [ ] Hard check: control_mutation_allowed == false
  - [ ] If control_mutation_allowed != false, immediately return BLOCKED with "control_mutation_enabled"
- [ ] Loads AuthorityPolicy for gate
- [ ] Validates policy_schema version known
- [ ] Validates policy.target_gate == current_gate_id
- [ ] Validates policy.authority_level == ZERO
- [ ] Validates policy.all_checks_must_pass == true (fail-closed default)
- [ ] Validates policy.stale_blocks == true (fail-closed default)

**Test Cases:**
```
PASS_CASE_1: All hard checks pass, policy valid
  → Verdict = PASS, Reasoning = "authority_policy_compliant"

BLOCK_CASE_1: authority = ONE (escalation attempt)
  → Verdict = BLOCKED, Reasoning = "authority_not_zero"

BLOCK_CASE_2: live_enabled = true
  → Verdict = BLOCKED, Reasoning = "live_enabled_violation"

BLOCK_CASE_3: broker_orders_allowed = true
  → Verdict = BLOCKED, Reasoning = "broker_orders_enabled"

BLOCK_CASE_4: control_mutation_allowed = true
  → Verdict = BLOCKED, Reasoning = "control_mutation_enabled"

NOT_PROVEN_CASE_1: Policy not yet loaded
  → Verdict = NOT_PROVEN, Reasoning = "policy_not_available"
```

**Pass Criteria:** 6/6 test cases pass + hard checks code-reviewed for zero conditionals

---

### Gate 4: MACHINE_HEALTH_AND_READINESS

- [ ] Iterates over all machines in fleet
- [ ] For each machine: health_status in [HEALTHY] (not [ERROR, UNKNOWN, RECOVERING])
- [ ] For each machine: error_count == 0 (not > 0)
- [ ] For each machine: (now - last_heartbeat).seconds < 60 (heartbeat fresh)
- [ ] For each machine: abs(clock_offset) < 5 (clock skew within tolerance)
- [ ] Detects restart anomaly: heartbeat gap > 120 seconds → BLOCKED
- [ ] Validates FencingToken:
  - [ ] fencing_token_hash matches known value
  - [ ] fencing_token_epoch <= current_epoch (not future)
  - [ ] fencing_token_expiry > now (not expired)
- [ ] If any check fails, returns BLOCKED
- [ ] If heartbeat not yet received, returns NOT_PROVEN with timeout counter

**Test Cases:**
```
PASS_CASE_1: All machines healthy, fence valid, clock OK
  → Verdict = PASS, Reasoning = "machine_health_ready"

BLOCK_CASE_1: One machine health_status = ERROR
  → Verdict = BLOCKED, Reasoning = "machine_error_detected"

BLOCK_CASE_2: Heartbeat age = 61 seconds (stale)
  → Verdict = BLOCKED, Reasoning = "heartbeat_stale"

BLOCK_CASE_3: Clock offset = 6 seconds
  → Verdict = BLOCKED, Reasoning = "clock_skew_excessive"

BLOCK_CASE_4: Fencing token expired
  → Verdict = BLOCKED, Reasoning = "fencing_token_expired"

BLOCK_CASE_5: Heartbeat gap = 130 seconds (restart detected)
  → Verdict = BLOCKED, Reasoning = "machine_restart_detected"

NOT_PROVEN_CASE_1: Heartbeat not yet received
  → Verdict = NOT_PROVEN, Reasoning = "heartbeat_unavailable"
```

**Pass Criteria:** 7/7 test cases pass + restart detection threshold verified (120s)

---

### Gate 5: CANARY_EXECUTION

- [ ] Blocks until CanaryRun.observation_window_seconds elapsed (300s immutable)
- [ ] After window: checks CanaryRun.result field
- [ ] result = PASS: checks error_rate <= 0.05 AND latency_p99 < 200 AND rollback_triggered = false
- [ ] result = FAIL: returns BLOCKED
- [ ] result = TIMEOUT or INCOMPLETE: returns BLOCKED
- [ ] If window not elapsed, returns NOT_PROVEN
- [ ] Timeout mechanism: if 5 minutes exceed observation window start, returns BLOCKED

**Test Cases:**
```
PASS_CASE_1: error_rate=2%, latency_p99=150ms, no rollback
  → Verdict = PASS, Reasoning = "canary_execution_passed"

BLOCK_CASE_1: error_rate = 7% (> 5%)
  → Verdict = BLOCKED, Reasoning = "canary_error_rate_high"

BLOCK_CASE_2: latency_p99 = 220ms (>= 200ms)
  → Verdict = BLOCKED, Reasoning = "canary_latency_high"

BLOCK_CASE_3: result = FAIL
  → Verdict = BLOCKED, Reasoning = "canary_failure"

BLOCK_CASE_4: rollback_triggered = true
  → Verdict = BLOCKED, Reasoning = "canary_rollback_initiated"

NOT_PROVEN_CASE_1: Canary still running (window not elapsed)
  → Verdict = NOT_PROVEN, Reasoning = "canary_observation_incomplete"

BLOCK_CASE_5: Canary timeout (5 minutes exceeded)
  → Verdict = BLOCKED, Reasoning = "canary_timeout"
```

**Pass Criteria:** 7/7 test cases pass + observation window (300s) immutable + timeout (5m) enforced

---

### Gate 6: EVIDENCE_CONSISTENCY

- [ ] Loads all EvidenceRecord objects for correlation_id
- [ ] Detects contradictions:
  - [ ] Two HASH_MATCH records with different hash values for same artifact → BLOCKED
  - [ ] Two POLICY_CHECK records with conflicting policy results → BLOCKED
  - [ ] CANARY_PASS contradicts HASH_MISMATCH → BLOCKED
- [ ] Checks EvidenceRecord.is_contradicted flag: if true for any record, return BLOCKED
- [ ] Validates temporal ordering: newer event_time should not reverse older observation
- [ ] If evidence still being collected or contradiction resolution pending, returns NOT_PROVEN

**Test Cases:**
```
PASS_CASE_1: No contradictions, timestamps ordered correctly
  → Verdict = PASS, Reasoning = "evidence_consistency_confirmed"

BLOCK_CASE_1: Two different hashes for same artifact
  → Verdict = BLOCKED, Reasoning = "hash_contradiction"

BLOCK_CASE_2: Policy checks contradict
  → Verdict = BLOCKED, Reasoning = "policy_contradiction"

BLOCK_CASE_3: Canary passes but hash evidence contradicts
  → Verdict = BLOCKED, Reasoning = "canary_hash_contradiction"

BLOCK_CASE_4: evidence.is_contradicted = true
  → Verdict = BLOCKED, Reasoning = "contradicted_evidence_present"

BLOCK_CASE_5: Temporal ordering violated (newer contradicts older)
  → Verdict = BLOCKED, Reasoning = "temporal_ordering_invalid"

NOT_PROVEN_CASE_1: Evidence still being collected
  → Verdict = NOT_PROVEN, Reasoning = "evidence_collection_incomplete"
```

**Pass Criteria:** 7/7 test cases pass + temporal ordering validation code-reviewed

---

### Gate 7: FRESHNESS_AND_STALENESS

- [ ] Loads all EvidenceRecord objects for correlation_id
- [ ] Checks gate.required_evidence_types
- [ ] For each required type:
  - [ ] At least one record exists (not missing)
  - [ ] Most recent record.recorded_at <= (now - 300s)? NO → must be fresh
  - [ ] Most recent record.observed_at <= (now - 300s)? NO → must be fresh
- [ ] Hash evidence: most recent timestamp < 300 seconds old
- [ ] Canary evidence: most recent timestamp < 300 seconds old
- [ ] Policy evidence: most recent timestamp < 300 seconds old
- [ ] Machine health evidence: most recent timestamp < 300 seconds old
- [ ] If any evidence > 300s old, returns BLOCKED
- [ ] If required evidence missing, returns BLOCKED
- [ ] If no evidence collected yet, returns NOT_PROVEN

**Test Cases:**
```
PASS_CASE_1: All required evidence < 300s old
  → Verdict = PASS, Reasoning = "evidence_freshness_confirmed"

BLOCK_CASE_1: Hash evidence = 301 seconds old
  → Verdict = BLOCKED, Reasoning = "evidence_stale"

BLOCK_CASE_2: Required evidence type missing
  → Verdict = BLOCKED, Reasoning = "required_evidence_missing"

NOT_PROVEN_CASE_1: Evidence not yet collected
  → Verdict = NOT_PROVEN, Reasoning = "evidence_not_collected"
```

**Pass Criteria:** 4/4 test cases pass + stale threshold (300s) hardcoded + NOT_PROVEN timeout enforced

---

### Gate 8: FINAL_ARBITER

- [ ] Loads all prior verdicts (gates 1–7)
- [ ] For each prior verdict:
  - [ ] If verdict = BLOCKED, return BLOCKED with reason from blocking gate
  - [ ] If verdict = NOT_PROVEN, return NOT_PROVEN with waiting gates listed
- [ ] If all prior verdicts = PASS:
  - [ ] Check authority still == ZERO (no escalation occurred)
  - [ ] Check owner_approval_id present if policy requires approval
  - [ ] Assemble DecisionCartridge (gates[], verdicts[], final_verdict, evidence_root_hash, policy_root_hash)
  - [ ] Seal cartridge (set created_at, immutable flag)
  - [ ] Return PASS with "final_arbiter_approved"

**Test Cases:**
```
PASS_CASE_1: All gates 1–7 = PASS, authority OK, cartridge sealed
  → Verdict = PASS, Reasoning = "final_arbiter_approved"

BLOCK_CASE_1: Gate 3 = BLOCKED
  → Verdict = BLOCKED, Reasoning = "prior_gate_blocked", Details = Gate 3 reason

NOT_PROVEN_CASE_1: Gate 5 = NOT_PROVEN
  → Verdict = NOT_PROVEN, Reasoning = "prior_gate_not_proven", Details = Gate 5 reason

BLOCK_CASE_2: Authority escalation detected
  → Verdict = BLOCKED, Reasoning = "authority_escalation_attempted"

BLOCK_CASE_3: Owner approval required but missing
  → Verdict = BLOCKED, Reasoning = "approval_missing"

NOT_PROVEN_CASE_2: DecisionCartridge not yet assembled
  → Verdict = NOT_PROVEN, Reasoning = "decision_cartridge_incomplete"
```

**Pass Criteria:** 6/6 test cases pass + DecisionCartridge immutability verified

---

## Fail-Closed Constraint Verification

### FC01: NO_AUTHORITY_ESCALATION

- [ ] Code review: no code path sets authority != ZERO
- [ ] Database schema: authority column has CHECK constraint
- [ ] Gate 3 and Gate 8 both verify authority == ZERO
- [ ] Test case: attempt authority=ONE → BLOCKED in Gate 3
- [ ] Test case: attempt authority=SCALED → BLOCKED in Gate 3

**Pass Criteria:** All 5 items verified

---

### FC02: STALE_EVIDENCE_BLOCKS

- [ ] Gate 7 implements freshness check with 300-second threshold
- [ ] Threshold hardcoded (not configurable)
- [ ] Test case: evidence 300s old → PASS
- [ ] Test case: evidence 301s old → BLOCKED
- [ ] Test case: evidence 3600s old → BLOCKED

**Pass Criteria:** All 5 items verified + threshold immutable

---

### FC03: CONTRADICTED_EVIDENCE_BLOCKS

- [ ] Gate 6 detects hash contradictions (two different hashes for same artifact)
- [ ] Gate 6 detects policy contradictions
- [ ] EvidenceRecord.is_contradicted flag properly set
- [ ] Test case: hash contradiction → BLOCKED
- [ ] Test case: policy contradiction → BLOCKED

**Pass Criteria:** All 5 items verified

---

### FC04: MISSING_REQUIRED_EVIDENCE_BLOCKS

- [ ] Each gate lists required_evidence_types
- [ ] Gate 7 checks all required types present
- [ ] Missing required evidence → NOT_PROVEN
- [ ] Timeout: 5 minutes NOT_PROVEN → BLOCKED
- [ ] Test case: missing hash evidence → NOT_PROVEN initially, then BLOCKED after 5m

**Pass Criteria:** All 5 items verified

---

### FC05: CANARY_FAILURE_BLOCKS

- [ ] Gate 5 evaluates canary result
- [ ] error_rate > 5% → BLOCKED
- [ ] latency_p99 > 200ms → BLOCKED
- [ ] rollback_triggered = true → BLOCKED
- [ ] Test cases for all three conditions

**Pass Criteria:** All 4 items verified + thresholds code-reviewed

---

### FC06: HASH_MISMATCH_BLOCKS

- [ ] Gate 2 verifies all 4 hashes (strategy, engine, ui, passport)
- [ ] Mismatch on any hash → BLOCKED
- [ ] Test cases for each hash type

**Pass Criteria:** All 3 items verified

---

### FC07: ALL_GATES_MUST_PASS_FOR_PROMOTION

- [ ] DecisionCartridge logic: final_verdict = PASS IFF all verdicts = PASS
- [ ] Test case: 7 gates PASS, 1 gate BLOCKED → final_verdict = BLOCKED
- [ ] Test case: 7 gates PASS, 1 gate NOT_PROVEN → final_verdict = NOT_PROVEN
- [ ] Test case: 8 gates PASS → final_verdict = PASS
- [ ] promotion_ready = true IFF final_verdict = PASS

**Pass Criteria:** All 4 items verified

---

### FC08: NO_MANUAL_OVERRIDE_OF_GATE_VERDICTS

- [ ] GateVerdict entity has no UPDATE path
- [ ] Database: INSERT only on verdicts table
- [ ] API: no PATCH/PUT endpoint for verdict
- [ ] Test case: attempt to modify verdict → fails with immutability error

**Pass Criteria:** All 4 items verified

---

## Integration Points Verification

### HP Infrastructure Integration

- [ ] Guardian accepts MachineHealthReport in Gate 4
- [ ] Guardian accepts FencingTokenProof in Gate 4
- [ ] Guardian accepts ArtifactDeploymentManifest in Gate 5 (canary deployment)
- [ ] HP receives PromotionApproval from Gate 8 with sealed cartridge
- [ ] HP receives BLOCKED signal if any gate blocks (no artifact deployment)
- [ ] Test: verify heartbeat receipt flows to Gate 4
- [ ] Test: verify fencing token validation in Gate 4
- [ ] Test: verify promotion signal triggers artifact deployment

**Pass Criteria:** All 8 items verified

---

### NinjaTrader Batch Integration

- [ ] Guardian output: PromotionApproval (gates passed, cartridge sealed)
- [ ] Guardian output: BLOCKED_Signal (reason, no_retry_until)
- [ ] Guardian output: NOT_PROVEN_Signal (waiting gates, ETA)
- [ ] NinjaTrader Batch: only executes orders if PASS verdict
- [ ] NinjaTrader Batch: waits on NOT_PROVEN verdict
- [ ] NinjaTrader Batch: rejects BLOCKED verdict (no retry)
- [ ] Test: verify PASS verdict enables order submission to NinjaTrader
- [ ] Test: verify BLOCKED verdict prevents order submission
- [ ] Test: verify NOT_PROVEN verdict delays order submission

**Pass Criteria:** All 9 items verified

---

### UI Dashboard Integration

- [ ] Guardian provides GuardianStateSnapshot to UI
- [ ] GuardianStateSnapshot includes: phase, authority, gates[], verdicts[], evidence_status, final_verdict, promotion_ready, truth_age_seconds
- [ ] UI displays Authority=ZERO on all screens
- [ ] UI displays TruthBar (is_fresh, age_seconds, stale_since_timestamp, warning_level)
- [ ] UI displays stale warnings (> 300s)
- [ ] UI read-only (no authority grants, no verdict overrides)
- [ ] UI supports admin/public toggle
- [ ] Test: verify UI shows Authority=ZERO
- [ ] Test: verify UI shows truth_age and stale warning
- [ ] Test: verify UI blocks any authority override attempts

**Pass Criteria:** All 10 items verified

---

## Pre-Deployment Sign-Off

**Checklist Summary:**

- [ ] Authority Invariant Lock (7/7)
- [ ] Entity Immutability (7 entities verified)
- [ ] Gate 1: SCHEMA_AND_IDENTITY (5/5)
- [ ] Gate 2: HASH_INTEGRITY (4/4)
- [ ] Gate 3: AUTHORITY_POLICY_COMPLIANCE (6/6)
- [ ] Gate 4: MACHINE_HEALTH_AND_READINESS (7/7)
- [ ] Gate 5: CANARY_EXECUTION (7/7)
- [ ] Gate 6: EVIDENCE_CONSISTENCY (7/7)
- [ ] Gate 7: FRESHNESS_AND_STALENESS (4/4)
- [ ] Gate 8: FINAL_ARBITER (6/6)
- [ ] Fail-Closed Constraints (8×5 checks)
- [ ] Integration Points (3 systems × 8–10 checks)

**Total Verification Items:** 100+

**Pass Criteria:** 100% of items verified and signed off

**Sign-Off Authority:** Domain Architect + Guardian Enforcement Lead + Technical Reviewer

---

## Sign-Off Table

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Domain Architect | [TBD] | 2026-09-07 | |
| Guardian Enforcement Lead | [TBD] | 2026-09-07 | |
| Technical Reviewer | [TBD] | 2026-09-07 | |
| QA Lead | [TBD] | 2026-09-07 | |

---

**Document Complete: 2026-09-07**  
**Authority Invariant: LOCKED_IMMUTABLE**  
**Next Phase: M03 Implementation (Sep 8–12)**

