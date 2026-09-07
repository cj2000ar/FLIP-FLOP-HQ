# Guardian 8-Gate Implementation Guide

**Status:** PHASE_2_FROZEN  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**Last Updated:** 2026-09-07  

---

## Quick Reference: Gate Entry/Exit Logic

### Gate 1: SCHEMA_AND_IDENTITY

**Input:** DeploymentCandidate object

**Checks:**
```
✓ candidate_schema version matches known schema
✓ artifact_hashes object has keys: strategy, engine, ui
✓ artifact_hashes[*] all non-empty SHA256
✓ passport_hash non-empty SHA256
✓ correlation_id UUID format and globally unique
```

**Output:** GateVerdict

| Condition | Verdict | Reasoning |
|-----------|---------|-----------|
| All checks pass | PASS | schema_and_identity_valid |
| Schema mismatch | BLOCKED | schema_version_unknown |
| Missing hash | BLOCKED | artifact_hash_missing |
| Duplicate correlation_id | BLOCKED | correlation_id_duplicate |
| Passport empty | BLOCKED | passport_hash_missing |

---

### Gate 2: HASH_INTEGRITY

**Input:** DeploymentCandidate + ArtifactSource evidence records

**Checks:**
```
✓ source_sha256(strategy) == candidate.artifact_hashes.strategy
✓ source_sha256(engine) == candidate.artifact_hashes.engine
✓ source_sha256(ui) == candidate.artifact_hashes.ui
✓ source_sha256(passport) == candidate.passport_hash
✗ Detect contradictions: if two sources disagree on same hash
```

**Evidence Sources:**
- HP_INFRA → artifact_hashes.strategy
- ENGINE_BUILD → artifact_hashes.engine
- UI_BUILD → artifact_hashes.ui
- CONTROL_SYSTEM → passport_hash

**Output:** GateVerdict

| Condition | Verdict | Reasoning |
|-----------|---------|-----------|
| All hashes match | PASS | hash_integrity_verified |
| strategy hash mismatch | BLOCKED | artifact_strategy_hash_mismatch |
| engine hash mismatch | BLOCKED | artifact_engine_hash_mismatch |
| ui hash mismatch | BLOCKED | artifact_ui_hash_mismatch |
| passport hash mismatch | BLOCKED | passport_hash_mismatch |
| Two sources disagree | BLOCKED | hash_contradiction_detected |
| Source not yet available | NOT_PROVEN | artifact_source_unavailable |

---

### Gate 3: AUTHORITY_POLICY_COMPLIANCE

**Input:** DeploymentCandidate + AuthorityPolicy + AuthorityTuple

**Hard Checks (Immutable):**
```
✓ authority == ZERO (not SCALED, not ONE, not escalated)
✓ live_enabled == false (not true, not null)
✓ broker_orders_allowed == false (not true, not null)
✓ control_mutation_allowed == false (not true, not null)
✗ Any value != expected → BLOCKED immediately
```

**Policy Checks:**
```
✓ policy_schema_version matches expected
✓ policy.target_gate == current_gate_id
✓ policy.authority_level == ZERO
✓ policy.all_checks_must_pass == true
✓ policy.stale_blocks == true
```

**Output:** GateVerdict

| Condition | Verdict | Reasoning |
|-----------|---------|-----------|
| All hard checks pass, policy valid | PASS | authority_policy_compliant |
| authority != ZERO | BLOCKED | authority_not_zero |
| live_enabled = true | BLOCKED | live_enabled_violation |
| broker_orders_allowed = true | BLOCKED | broker_orders_enabled |
| control_mutation_allowed = true | BLOCKED | control_mutation_enabled |
| Policy not loaded | NOT_PROVEN | policy_not_available |

---

### Gate 4: MACHINE_HEALTH_AND_READINESS

**Input:** HP Infra health reports + FencingToken

**Checks (All Required):**
```
✓ For each machine in fleet:
  ✓ health_status == HEALTHY (not ERROR, not UNKNOWN, not RECOVERING)
  ✓ error_count == 0 (not > 0)
  ✓ last_heartbeat age < 60 seconds (not stale)
  ✓ clock_offset < 5 seconds absolute value (not drifted)
✓ fencing_token:
  ✓ token_hash matches known value
  ✓ epoch <= current_epoch (not future)
  ✓ expiry > current_time (not expired)
✗ Detect restart/sleep anomaly (heartbeat gap > 120 seconds)
```

**Output:** GateVerdict

| Condition | Verdict | Reasoning |
|-----------|---------|-----------|
| All machines healthy, fence valid, clock OK | PASS | machine_health_ready |
| Any machine in ERROR state | BLOCKED | machine_error_detected |
| Any heartbeat stale > 60 seconds | BLOCKED | heartbeat_stale |
| Clock skew > 5 seconds | BLOCKED | clock_skew_excessive |
| Fencing token expired | BLOCKED | fencing_token_expired |
| Restart/sleep detected (heartbeat gap > 120s) | BLOCKED | machine_restart_detected |
| Heartbeat not yet received | NOT_PROVEN | heartbeat_unavailable |

---

### Gate 5: CANARY_EXECUTION

**Input:** CanaryRun object + observation_window elapsed

**Observation Window:** 300 seconds (immutable)

**Checks (After window complete):**
```
✓ canary_result != FAIL and != TIMEOUT and != INCOMPLETE
✓ error_rate <= 0.05 (5% or less)
✓ latency_p99_ms < 200 (sub-200ms)
✓ rollback_triggered == false
✓ observed_at + observation_window_seconds <= now
```

**Result Enum:**
- PASS: Cohort healthy, error rate low, latency acceptable
- FAIL: Cohort errors or performance degradation
- TIMEOUT: Observation window exceeded without result
- INCOMPLETE: Observation window closed but results missing

**Output:** GateVerdict

| Condition | Verdict | Reasoning |
|-----------|---------|-----------|
| All metrics pass | PASS | canary_execution_passed |
| error_rate > 5% | BLOCKED | canary_error_rate_high |
| latency_p99 >= 200ms | BLOCKED | canary_latency_high |
| result = FAIL or TIMEOUT or INCOMPLETE | BLOCKED | canary_failure |
| rollback_triggered = true | BLOCKED | canary_rollback_initiated |
| Observation window not elapsed | NOT_PROVEN | canary_observation_incomplete |

---

### Gate 6: EVIDENCE_CONSISTENCY

**Input:** All EvidenceRecord objects collected so far + existing verdicts

**Contradiction Detection:**
```
✓ Load all evidence records for this correlation_id
✓ For each evidence_type:
  ✓ Check no two records contradict (same type, conflicting observation)
  ✓ Check temporal ordering: newer shouldn't reverse older (unless explicitly)
  ✓ Check is_contradicted flag: if true, verdict = BLOCKED
✓ Verify:
  ✓ Hash evidence: no two different hashes for same artifact
  ✓ Policy evidence: no two conflicting policy checks
  ✓ Canary evidence: doesn't contradict hash evidence
  ✓ Event timestamps consistent with knowledge timestamps
```

**Output:** GateVerdict

| Condition | Verdict | Reasoning |
|-----------|---------|-----------|
| No contradictions, timestamps valid | PASS | evidence_consistency_confirmed |
| Two different hashes for same artifact | BLOCKED | hash_contradiction |
| Policy checks contradict | BLOCKED | policy_contradiction |
| Canary contradicts hash evidence | BLOCKED | canary_hash_contradiction |
| Evidence.is_contradicted = true | BLOCKED | contradicted_evidence_present |
| Temporal ordering violation | BLOCKED | temporal_ordering_invalid |
| Evidence still being collected | NOT_PROVEN | evidence_collection_incomplete |

---

### Gate 7: FRESHNESS_AND_STALENESS

**Input:** All EvidenceRecord objects + current timestamp

**Stale Threshold:** 300 seconds (hard-locked, immutable)

**Checks:**
```
✓ For each required_evidence_type:
  ✓ At least one record exists for this type
  ✓ Most recent record.recorded_at <= now - 300 seconds? NO (not stale)
  ✓ Most recent record.observed_at <= now - 300 seconds? NO (not stale)
✓ Hash evidence: age < 300 seconds
✓ Canary evidence: age < 300 seconds
✓ Policy evidence: age < 300 seconds
✓ Machine health: age < 300 seconds
```

**Output:** GateVerdict

| Condition | Verdict | Reasoning |
|-----------|---------|-----------|
| All required evidence fresh | PASS | evidence_freshness_confirmed |
| Any evidence older than 300s | BLOCKED | evidence_stale |
| Required evidence missing | BLOCKED | required_evidence_missing |
| No evidence records exist | NOT_PROVEN | evidence_not_collected |

---

### Gate 8: FINAL_ARBITER

**Input:** DeploymentCandidate + all prior verdict_ids (1–7) + DecisionCartridge (incomplete)

**Aggregate Checks:**
```
✓ Load all prior verdicts (gates 1–7)
✓ For each prior verdict:
  ✓ verdict != BLOCKED? (if blocked, this gate = BLOCKED)
  ✓ verdict != NOT_PROVEN? (if not_proven, this gate = NOT_PROVEN)
✓ If all prior = PASS:
  ✓ authority still == ZERO? (no escalation occurred)
  ✓ owner_approval_id present if policy requires?
  ✓ DecisionCartridge can be sealed (all gate_verdicts[] populated)
```

**Output:** GateVerdict (Final)

| Condition | Verdict | Reasoning |
|-----------|---------|-----------|
| All gates 1–7 = PASS, authority OK, approval OK, cartridge sealed | PASS | final_arbiter_approved |
| Any gate 1–7 = BLOCKED | BLOCKED | prior_gate_blocked |
| Any gate 1–7 = NOT_PROVEN | NOT_PROVEN | prior_gate_not_proven |
| authority escalation detected | BLOCKED | authority_escalation_attempted |
| owner_approval missing when required | BLOCKED | approval_missing |
| DecisionCartridge not sealed | NOT_PROVEN | decision_cartridge_incomplete |

---

## Verdict Recording (All Gates)

**After evaluation, create GateVerdict:**

```python
verdict = GateVerdict(
    verdict_id=uuid(),
    gate_id=gate_id,
    correlation_id=candidate.correlation_id,
    verdict=PASS | BLOCKED | NOT_PROVEN,
    reasoning="human_readable_explanation",
    evidence_id=primary_evidence.evidence_id,  # Can be null for NOT_PROVEN
    secondary_evidence_ids=[...],  # Supporting evidence
    event_time=now,
    knowledge_time=now,  # Or when evidence was known
    authority_used=ZERO,
    policy_hash=sha256(applied_policy)
)

# Store in database (immutable)
save(verdict)

# Update candidate
candidate.gate_results.append({
    gate_id: verdict.gate_id,
    verdict_id: verdict.verdict_id,
    verdict: verdict.verdict
})
```

---

## Decision Cartridge Assembly (After Gate 8)

**Once all 8 gates have verdicts:**

```python
cartridge = DecisionCartridge(
    cartridge_id=uuid(),
    correlation_id=candidate.correlation_id,
    candidate_id=candidate.candidate_id,
    gate_verdicts=[
        {gate_id: gates[i].gate_id, verdict_id: verdicts[i].verdict_id, verdict: verdicts[i].verdict}
        for i in range(1, 9)
    ],
    final_verdict=compute_final_verdict(verdicts[1:9]),
    blocking_gates=[g.gate_id for g in verdicts if g.verdict == BLOCKED],
    not_proven_gates=[g.gate_id for g in verdicts if g.verdict == NOT_PROVEN],
    evidence_root_hash=sha256(all_evidence),
    policy_root_hash=sha256(all_policies),
    created_at=now,
    authority=ZERO,
    owner_approval_id=candidate.owner_approval_id
)

# Store (immutable)
save(cartridge)

# Update candidate
candidate.decision_cartridge_id = cartridge.cartridge_id
candidate.promotion_ready = (cartridge.final_verdict == PASS)
candidate.status = (APPROVED if promotion_ready else BLOCKED)
```

---

## Fail-Closed Sentinel (Every Gate)

**Before issuing any verdict, check:**

```python
def fail_closed_check(candidate, gate_id):
    # FC01: Authority must be ZERO
    if candidate.authority != ZERO:
        return BLOCKED, "authority_not_zero"
    
    # FC02: Check stale evidence
    for evidence in get_evidence(candidate.correlation_id):
        if (now - evidence.recorded_at).seconds > 300:
            return BLOCKED, "evidence_stale"
    
    # FC03: Check for contradictions
    if any(e.is_contradicted for e in get_evidence(candidate.correlation_id)):
        return BLOCKED, "contradicted_evidence_present"
    
    # FC04: Check for missing required evidence
    gate = get_gate(gate_id)
    for required_type in gate.required_evidence_types:
        if not has_evidence_of_type(candidate.correlation_id, required_type):
            return NOT_PROVEN, f"evidence_{required_type}_missing"
    
    # Pass through to gate-specific logic
    return None, None
```

---

## Testing Checklist (Per Gate)

### Gate 1: SCHEMA_AND_IDENTITY

- [ ] Valid candidate passes
- [ ] Missing hash field blocks
- [ ] Invalid UUID blocks
- [ ] Duplicate correlation_id blocks

### Gate 2: HASH_INTEGRITY

- [ ] Matching hashes pass
- [ ] Mismatched hash blocks
- [ ] Contradictory sources block
- [ ] Missing source → NOT_PROVEN

### Gate 3: AUTHORITY_POLICY_COMPLIANCE

- [ ] authority=ZERO passes
- [ ] authority=ONE blocks (test escalation attempt)
- [ ] live_enabled=false passes
- [ ] live_enabled=true blocks (test live attempt)
- [ ] broker_orders_allowed=false passes
- [ ] broker_orders_allowed=true blocks
- [ ] control_mutation_allowed=false passes
- [ ] control_mutation_allowed=true blocks

### Gate 4: MACHINE_HEALTH_AND_READINESS

- [ ] All machines healthy passes
- [ ] One machine ERROR blocks
- [ ] Heartbeat stale > 60s blocks
- [ ] Clock skew > 5s blocks
- [ ] Fencing token expired blocks
- [ ] Restart detected (heartbeat gap > 120s) blocks

### Gate 5: CANARY_EXECUTION

- [ ] All metrics pass → passes
- [ ] error_rate > 5% blocks
- [ ] latency_p99 > 200ms blocks
- [ ] result=FAIL blocks
- [ ] Canary still running → NOT_PROVEN

### Gate 6: EVIDENCE_CONSISTENCY

- [ ] No contradictions passes
- [ ] Two different hashes blocks
- [ ] Policy conflict blocks
- [ ] is_contradicted flag blocks
- [ ] Evidence still collecting → NOT_PROVEN

### Gate 7: FRESHNESS_AND_STALENESS

- [ ] All evidence < 300s passes
- [ ] Any evidence > 300s blocks
- [ ] Required evidence missing blocks
- [ ] Evidence not yet collected → NOT_PROVEN

### Gate 8: FINAL_ARBITER

- [ ] All prior = PASS passes
- [ ] Any prior = BLOCKED blocks
- [ ] Any prior = NOT_PROVEN → NOT_PROVEN
- [ ] Authority escalation blocks
- [ ] Owner approval missing blocks (if required by policy)

---

## Timeout Handling

**Per-gate timeout:** 5 minutes (300 seconds)

```python
def evaluate_gate(gate_id, candidate, deadline=now + 5*60):
    while now < deadline:
        result = gate_evaluation(gate_id, candidate)
        if result.verdict != NOT_PROVEN:
            return result
        sleep(1)
    
    # Timeout: escalate NOT_PROVEN to BLOCKED
    return BLOCKED, "gate_evaluation_timeout"
```

---

## Summary: 8-Gate Truth Table

| Gate | Blocks On | NOT_PROVEN On | Passes On |
|------|-----------|---------------|-----------|
| 1 | Schema fail, duplicate ID, missing hash | Passport unavailable | All fields valid |
| 2 | Hash mismatch, contradiction | Source unavailable | All hashes match |
| 3 | authority≠ZERO, live=true, mutation=true | Policy not loaded | Authority frozen ZERO |
| 4 | Machine error, heartbeat stale, clock drift, restart | Heartbeat not arrived | Fleet healthy, clock OK |
| 5 | error_rate>5%, latency>200ms, rollback | Window not complete | All metrics pass |
| 6 | Hash conflict, policy conflict, contradiction | Evidence collecting | No contradictions |
| 7 | Evidence >300s old, missing evidence | Evidence not collected | All evidence <300s |
| 8 | Prior gate blocked, authority escalation, approval missing | Prior gate not_proven | All prior passed, auth zero, approval present |

---

## Authority=ZERO Lock (Every Gate)

**Before ANY verdict:**

```python
HARD_GATE = (candidate.authority == ZERO)
ESCALATION_ATTEMPTED = (input_authority != candidate.authority)

if not HARD_GATE or ESCALATION_ATTEMPTED:
    return BLOCKED, "authority_violation"
```

**This check is non-negotiable across all 8 gates.**

---

**Implementation Complete → Phase 2 Execution (M03: Sep 8–12)**

