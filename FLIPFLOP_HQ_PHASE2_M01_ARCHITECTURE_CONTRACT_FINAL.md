# FlipFlop HQ Phase 2 — M01 Architecture Contract (FINAL)

**Status:** FROZEN AND LOCKED  
**Authority:** ZERO (HARD-LOCKED IMMUTABLE)  
**Date:** 2026-09-07  
**Owner:** Technical Architect  
**Distribution:** FlipFlop HQ Phase 2 Team  

---

## Executive Summary

**M01 Freeze Complete.** Four frozen domain models (Guardian Enforcement, HP 24/7 Infrastructure, NinjaTrader Batch, UI Design) are locked and ready for parallel implementation (M02–M04). This architecture contract consolidates:

- **31 frozen tuples** (immutable, hashable, timestamped)
- **34 core entities** (7 Guardian + 7 Batch + 8 HP + 12 UI)
- **25+ fail-closed constraints** (no authority escalation, no stale evidence, no contradictions)
- **4 authority invariants** (ZERO, LIVE=OFF, BROKER_ORDERS=NONE, CONTROL_MUTATION=NONE)
- **5 integration matrix** (Guardian ↔ HP, Guardian ↔ Batch, Guardian ↔ UI, HP ↔ Batch, Batch ↔ UI)
- **10 critical risks** (R01–R10) with mitigation strategies

**Authority Invariant Status:** CANNOT CHANGE. Every implementation must verify this lock throughout.

---

## Authority Invariant (NON-NEGOTIABLE)

```
AUTHORITY = ZERO           (no escalation ever)
LIVE = OFF                 (paper-only, no real orders)
BROKER_ORDERS = NONE       (no broker execution)
CONTROL_MUTATION = NONE    (artifacts immutable after creation)
FAILURE_POLICY = FAIL_CLOSED (stale/missing/contradictory blocks promotion)
```

**Hard-locked in:**
- Guardian Gate 3 (authority check)
- Guardian Gate 8 (final arbiter check)
- Batch constraint gate CG01 (no escalation)
- Every UI control (Authority=ZERO display, read-only)
- HP machine role: FENCING_TOKEN validation (prevent unauthorized promotion)

---

## Workstream Summaries (4 Parallel Lanes)

### Workstream 1: Guardian Enforcement (M03: Sep 8–12)

**Purpose:** Fail-closed deployment arbitration. Evaluates 8 gates in sequence. All must PASS for promotion.

**Entities:** 7 core  
- ReleaseGate (permitting checkpoint)
- GateVerdict (PASS|BLOCKED|NOT_PROVEN)
- EvidenceRecord (facts, hashes, canary results)
- AuthorityPolicy (rules governing thresholds)
- DecisionCartridge (immutable snapshot of all 8 gate results)
- CanaryRun (controlled test deployment)
- DeploymentCandidate (artifact bundle)

**Frozen Tuples:** 4  
1. AuthorityTuple: (authority=ZERO, live=false, broker=false, mutation=false, approval_id)
2. StrategyIdentityTuple: (side, sha256, passport_id, gate_version, verification_state)
3. GateDecisionTuple: (gate_id, correlation_id, input_hashes, evidence_id, verdict, event_time, knowledge_time)
4. DeploymentCandidateTuple: (candidate_id, artifact_hashes, passport_hash, gate_results, canary_evidence_id, authority, approval_id)

**Sequential Gates:** 8  
1. SCHEMA_AND_IDENTITY — Bad schema, duplicate ID, missing hash
2. HASH_INTEGRITY — Hash mismatch, contradiction
3. AUTHORITY_POLICY_COMPLIANCE — Authority≠ZERO, live=true, mutation=true
4. MACHINE_HEALTH_AND_READINESS — Machine error, heartbeat stale, clock drift, restart
5. CANARY_EXECUTION — Error rate>5%, latency>200ms, rollback
6. EVIDENCE_CONSISTENCY — Contradiction, temporal ordering violation
7. FRESHNESS_AND_STALENESS — Evidence >300s old, missing evidence
8. FINAL_ARBITER — Prior gate blocked/not_proven, authority escalation

**Constraints:** 8 fail-closed  
- FC01: NO_AUTHORITY_ESCALATION (Gate 3 + Gate 8)
- FC02: STALE_EVIDENCE_BLOCKS (Gate 7, >300s rejects)
- FC03: CONTRADICTED_EVIDENCE_BLOCKS (Gate 6 detects + blocks)
- FC04: MISSING_REQUIRED_EVIDENCE_BLOCKS (Gate 7 timeout to BLOCKED)
- FC05: CANARY_FAILURE_BLOCKS (Gate 5, error>5% or latency>200ms)
- FC06: HASH_MISMATCH_BLOCKS (Gate 2, any mismatch)
- FC07: ALL_GATES_MUST_PASS_FOR_PROMOTION (DecisionCartridge.final_verdict = PASS IFF all 8 PASS)
- FC08: NO_MANUAL_OVERRIDE_OF_GATE_VERDICTS (GateVerdict immutable, INSERT-only)

**Exit Criteria (M03):**
- 8/8 gates implemented + tested
- All 8 verdicts (PASS|BLOCKED|NOT_PROVEN) tested
- Negative authority tests pass (BLOCKED if authority≠ZERO)
- Integration tests with HP (heartbeat, clock, fencing)
- Integration tests with Batch (GateDecisionTuple → BatchVerdictTuple)
- Integration tests with UI (GuardianStateSnapshot display)
- Code review signed-off

---

### Workstream 2: HP 24/7 Infrastructure (M02: Sep 8–11)

**Purpose:** Machine lifecycle, health monitoring, durable storage, fail-closed fencing.

**Entities:** 8 core  
- MachineRole (RED_DRAGON, HP worker, version, config)
- MachineHealth (heartbeat, clock, restart detection)
- FencingToken (authorization, epoch, expiry, signature)
- DurableStorage (write-once archive, path, retention)
- HeartbeatRecord (machine alive proof)
- RestartDetection (cold start, warm start, recovery)
- ClockState (NTP sync, skew detection)
- DurableReceipt (archive write confirmation, HP → Batch)

**Frozen Tuples:** 5  
1. MachineRoleTuple: (machine_id, role, version, config_hash, fencing_epoch, health, truth_age)
2. HeartbeatTuple: (heartbeat_id, machine_id, timestamp, health_status, clock_offset, sequence)
3. FencingTokenTuple: (token_id, machine_id, epoch, expiry, signature_hash, authority_lock)
4. DurableStorageTuple: (storage_id, path, retention_years, immutable_hash, retrieval_metadata, hp_receipt)
5. DurableReceiptTuple: (receipt_id, timestamp, storage_path, confirmation_hash, archive_status)

**Constraints:** 6 fail-closed  
- HP01: HEARTBEAT_FRESHNESS (< 60 seconds, else stale)
- HP02: CLOCK_SYNC (NTP offset < 5 seconds)
- HP03: FENCING_TOKEN_VALID (not expired, signature verified)
- HP04: RESTART_DETECTED (cold/warm start, recovery state)
- HP05: DURABLE_STORAGE_WRITE_ONCE (no updates/deletes)
- HP06: RECEIPT_REQUIRED_BEFORE_VERIFIED (DurableReceipt before archive_status=VERIFIED)

**Integration Points:**
- **Guardian (Gate 4):** MachineRoleTuple (health, heartbeat, truth_age)
- **Batch (Archive):** DurableReceiptTuple (storage confirmation)
- **UI (Dashboard):** MachineRoleTuple display (machine status, heartbeat, truth_age)

**Exit Criteria (M02):**
- Heartbeat mechanism tested (< 60s)
- Clock sync detection working (NTP offset < 5s)
- Fencing token validation working
- Restart/cold-start recovery tested
- Durable storage write-once enforced
- Receipt generation + verification tested
- Integration tests with Guardian Gate 4
- Integration tests with Batch archive write
- Code review signed-off

---

### Workstream 3: NinjaTrader Batch (M04: Sep 8–14)

**Purpose:** End-of-day batch execution (market close → export → alerts → summary → archive → CLOSED).

**Entities:** 7 core  
- BatchRun (session span: market_open → market_close)
- BatchVerdict (aggregates Guardian 8-gate verdicts + compliance + tax + archive)
- DayReport (trade_count, P&L, risk_metrics, alert_count)
- AlertRecord (trade alert, anomaly, severity, escalation)
- ComplianceBundle (tax_summary, receipt_hashes, audit_trail, certification)
- TaxDataArchive (write-once tax data, 7-year retention)
- ArchiveRecord (immutable archive entry in HP durable storage)

**Frozen Tuples:** 6  
1. BatchRunTuple: (batch_id, run_date, market_open_time, market_close_time, mode, correlation_id)
2. DayReportTuple: (report_id, batch_id, trade_count, pnl_summary, risk_metrics, alert_count, export_time)
3. AlertRecordTuple: (alert_id, batch_id, severity, alert_type, message, timestamp, escalation_flag)
4. ComplianceBundleTuple: (bundle_id, batch_id, tax_summary, receipt_hashes, audit_trail, certification_time)
5. ArchiveRecordTuple: (archive_record_id, batch_id, storage_path, retention_years, immutable_hash, retrieval_metadata)
6. BatchVerdictTuple: (verdict_id, batch_id, guardian_gate_results, compliance_passed, tax_verified, archive_verified, batch_status)

**Batch Lifecycle:** PENDING → PROCESSING → CLOSED → ARCHIVED  
- Authority=ZERO verified at creation
- Mode: PAPER|SHADOW|ANALYSIS (never LIVE)
- Guardian 8-gate verdicts aggregated
- Compliance bundle certified (locks tax data)
- Archive written to HP durable storage
- HP receipt required before VERIFIED
- Closed_at marks data immutability (no further changes)

**Constraints:** 8 fail-closed (CG01–CG08)  
- CG01: NO_AUTHORITY_ESCALATION (authority == ZERO always)
- CG02: BATCH_DATA_IMMUTABLE_AFTER_CLOSE (closed_at locks all data)
- CG03: VERDICT_REQUIRES_ALL_GATES_PASS (APPROVED IFF all 8 gates PASS + compliance + tax + archive)
- CG04: GUARDIAN_GATES_MUST_COMPLETE (all 8 required before close)
- CG05: COMPLIANCE_LOCK (no updates after certification)
- CG06: ARCHIVE_WRITE_ONCE (ArchiveRecord INSERT-only)
- CG07: HP_DURABLE_RECEIPT (receipt required before VERIFIED)
- CG08: RETENTION_ENFORCED (no purge before retention_until)

**Verdict Decision:**
- **APPROVED:** All 8 gates PASS + compliance_passed + tax_verified + archive_verified
- **BLOCKED:** Any gate BLOCKED or verification failed
- **NOT_PROVEN:** Any gate NOT_PROVEN (timeout 5min → BLOCKED)

**Integration Points:**
- **Guardian:** GateDecisionTuple (8 verdicts) → BatchVerdictTuple
- **HP:** ArchiveRecord written → HP durable storage → DurableReceiptTuple
- **UI:** BatchStatusSnapshot (read-only), alert array, report summary, authority lock

**Exit Criteria (M04):**
- Batch lifecycle state machine (PENDING → PROCESSING → CLOSED → ARCHIVED) working
- Guardian verdict aggregation (all 8 gates required, APPROVED logic)
- Compliance bundle certification (locks data)
- Archive write coordination (HP durable storage + receipt)
- Alert generation + escalation
- Report finalization + export
- All constraint gates (CG01-CG08) enforced
- Authority=ZERO locked throughout
- Data immutable after batch close
- Integration tests with Guardian (all gates) + HP (archive write + receipt)
- Code review signed-off

---

### Workstream 4: UI Design (M04: Sep 8–14)

**Purpose:** Phone (cockpit), tablet (workspace), desktop (full command center). Display Guardian state, Batch status, HP health. Truth bar (age of evidence).

**Entities:** 12 core  
- ControlCenter (master dashboard container)
- PhoneCockpit (compact mobile view, critical alerts only)
- TabletWorkspace (medium view, summary + chart)
- DesktopCommand (full view, all data, drill-down)
- GuardianStateDisplay (gates[], verdicts[], final_verdict, authority_lock)
- TruthBar (age_seconds, is_fresh, stale_warning, warning_level)
- BatchStatusDisplay (verdict_status, alert_array, report_summary)
- MachineHealthDisplay (heartbeat, clock_offset, fencing_token_status)
- CanaryDisplay (execution_status, error_rate, latency, evidence)
- AlertPanel (severity, type, escalation, resolution)
- ReportSummary (trade_count, P&L, risk_metrics)
- OwnerApprovalPanel (read-only, no authority grants)

**Frozen Tuples:** 10  
1. GuardianStateSnapshotTuple: (state_id, phase, authority, gates[], verdicts[], evidence_status, final_verdict, promotion_ready, truth_age_seconds)
2. TruthBarTuple: (truth_id, is_fresh, age_seconds, stale_since, warning_level, last_update)
3. PhoneCockpitTuple: (cockpit_id, critical_alert_count, authority_lock, promotion_status, truth_bar)
4. TabletWorkspaceTuple: (workspace_id, summary_chart, gate_progress, batch_status, machine_health)
5. DesktopCommandTuple: (command_id, full_gates[], verdicts[], batch_details, hp_metrics, evidence_drill_down)
6. BatchStatusSnapshotTuple: (batch_snapshot_id, verdict_status, alert_array, report_summary, guardian_gate_results)
7. MachineHealthSnapshotTuple: (health_id, heartbeat, clock_offset, fencing_token_valid, restart_detected, truth_age)
8. CanaryExecutionDisplayTuple: (canary_display_id, execution_status, error_rate, latency, rollback_flag)
9. AlertPanelTuple: (alert_panel_id, severity, alert_type, message, escalation_flag, resolution_status)
10. OwnerApprovalPanelTuple: (approval_panel_id, candidate_id, promotion_ready, authority_lock, signature_placeholder)

**Form Factors & Constraints:**
- **Phone:** 320–480px width, critical alerts only, Authority=ZERO lock (red/green)
- **Tablet:** 600–1024px, summary view + chart, full gate status, machine health
- **Desktop:** 1200px+, full command center, drill-down capability, evidence tree

**Truth Age Indicators:**
- Fresh (green): < 60 seconds
- Warning (yellow): 60–300 seconds
- Stale (red): > 300 seconds

**Authority Display (All Forms):**
- "Authority: ZERO" (red lock icon, immutable)
- "Live: OFF" (red/off indicator)
- Read-only (no buttons to grant authority, approve verdicts, or override gates)

**Integration Points:**
- **Guardian:** GuardianStateSnapshot input (read-only display)
- **Batch:** BatchStatusSnapshot input (read-only display)
- **HP:** MachineRoleTuple input (health, heartbeat, truth_age)

**Constraints:** 7 fail-closed  
- UI01: READ_ONLY (UI cannot grant authority, override verdicts, approve/block)
- UI02: AUTHORITY_DISPLAY_LOCK (Authority=ZERO on all screens, all form factors)
- UI03: TRUTH_AGE_DISPLAY (visible on all forms, > 300s = red warning)
- UI04: GATE_STATUS_DISPLAY (all 8 gates + verdicts visible, truth-age per gate)
- UI05: ADMIN_PUBLIC_TOGGLE (admin shows all data, public filters sensitive fields)
- UI06: NO_MANUAL_OVERRIDE (no way to override gate verdicts, batch verdicts, or authority)
- UI07: STALE_WARNING_ESCALATION (> 300s = red, encourages data refresh)

**Exit Criteria (M04):**
- Phone cockpit (320–480px) working, critical alerts, Authority=ZERO lock visible
- Tablet workspace (600–1024px) working, summary + chart, full gate status
- Desktop command center (1200px+) working, full drill-down capability
- Truth bar on all form factors (age, stale detection, warning)
- Guardian state display (gates[], verdicts[], final_verdict, authority_lock)
- Batch status display (verdict, alerts, report summary)
- HP machine health display (heartbeat, clock, fencing token)
- Admin/public toggle filtering tested
- Read-only enforcement (no authority grants, no verdict overrides)
- Authority=ZERO lock visible and emphasized on all screens
- Integration tests with Guardian (state snapshots)
- Integration tests with Batch (status snapshots)
- Integration tests with HP (machine health)
- Code review signed-off

---

## Consolidated Entity List (34 Total)

### Guardian Enforcement (7)
1. ReleaseGate
2. GateVerdict
3. EvidenceRecord
4. AuthorityPolicy
5. DecisionCartridge
6. CanaryRun
7. DeploymentCandidate

### HP 24/7 Infrastructure (8)
8. MachineRole
9. MachineHealth
10. FencingToken
11. DurableStorage
12. HeartbeatRecord
13. RestartDetection
14. ClockState
15. DurableReceipt

### NinjaTrader Batch (7)
16. BatchRun
17. BatchVerdict
18. DayReport
19. AlertRecord
20. ComplianceBundle
21. TaxDataArchive
22. ArchiveRecord

### UI Design (12)
23. ControlCenter
24. PhoneCockpit
25. TabletWorkspace
26. DesktopCommand
27. GuardianStateDisplay
28. TruthBar
29. BatchStatusDisplay
30. MachineHealthDisplay
31. CanaryDisplay
32. AlertPanel
33. ReportSummary
34. OwnerApprovalPanel

---

## Consolidated Tuple Schemas (31 Frozen)

### Guardian (4 Tuples)
1. **AuthorityTuple** — (authority, live, broker, mutation, approval_id) — IMMUTABLE
2. **StrategyIdentityTuple** — (side, sha256, passport_id, gate_version, verification_state) — IMMUTABLE
3. **GateDecisionTuple** — (gate_id, correlation_id, input_hashes, evidence_id, verdict, event_time, knowledge_time) — IMMUTABLE
4. **DeploymentCandidateTuple** — (candidate_id, artifact_hashes, passport_hash, gate_results, canary_evidence_id, authority, approval_id) — IMMUTABLE

### HP Infrastructure (5 Tuples)
5. **MachineRoleTuple** — (machine_id, role, version, config_hash, fencing_epoch, health, truth_age) — IMMUTABLE
6. **HeartbeatTuple** — (heartbeat_id, machine_id, timestamp, health_status, clock_offset, sequence) — IMMUTABLE
7. **FencingTokenTuple** — (token_id, machine_id, epoch, expiry, signature_hash, authority_lock) — IMMUTABLE
8. **DurableStorageTuple** — (storage_id, path, retention_years, immutable_hash, retrieval_metadata, hp_receipt) — IMMUTABLE
9. **DurableReceiptTuple** — (receipt_id, timestamp, storage_path, confirmation_hash, archive_status) — IMMUTABLE

### Batch (6 Tuples)
10. **BatchRunTuple** — (batch_id, run_date, market_open_time, market_close_time, mode, correlation_id) — IMMUTABLE
11. **DayReportTuple** — (report_id, batch_id, trade_count, pnl_summary, risk_metrics, alert_count, export_time) — IMMUTABLE
12. **AlertRecordTuple** — (alert_id, batch_id, severity, alert_type, message, timestamp, escalation_flag) — IMMUTABLE
13. **ComplianceBundleTuple** — (bundle_id, batch_id, tax_summary, receipt_hashes, audit_trail, certification_time) — IMMUTABLE
14. **ArchiveRecordTuple** — (archive_record_id, batch_id, storage_path, retention_years, immutable_hash, retrieval_metadata) — IMMUTABLE
15. **BatchVerdictTuple** — (verdict_id, batch_id, guardian_gate_results, compliance_passed, tax_verified, archive_verified, batch_status) — IMMUTABLE

### UI (10 Tuples)
16. **GuardianStateSnapshotTuple** — (state_id, phase, authority, gates[], verdicts[], evidence_status, final_verdict, promotion_ready, truth_age_seconds) — IMMUTABLE
17. **TruthBarTuple** — (truth_id, is_fresh, age_seconds, stale_since, warning_level, last_update) — IMMUTABLE
18. **PhoneCockpitTuple** — (cockpit_id, critical_alert_count, authority_lock, promotion_status, truth_bar) — IMMUTABLE
19. **TabletWorkspaceTuple** — (workspace_id, summary_chart, gate_progress, batch_status, machine_health) — IMMUTABLE
20. **DesktopCommandTuple** — (command_id, full_gates[], verdicts[], batch_details, hp_metrics, evidence_drill_down) — IMMUTABLE
21. **BatchStatusSnapshotTuple** — (batch_snapshot_id, verdict_status, alert_array, report_summary, guardian_gate_results) — IMMUTABLE
22. **MachineHealthSnapshotTuple** — (health_id, heartbeat, clock_offset, fencing_token_valid, restart_detected, truth_age) — IMMUTABLE
23. **CanaryExecutionDisplayTuple** — (canary_display_id, execution_status, error_rate, latency, rollback_flag) — IMMUTABLE
24. **AlertPanelTuple** — (alert_panel_id, severity, alert_type, message, escalation_flag, resolution_status) — IMMUTABLE
25. **OwnerApprovalPanelTuple** — (approval_panel_id, candidate_id, promotion_ready, authority_lock, signature_placeholder) — IMMUTABLE

**All tuples:**
- Content immutable (no updates to history)
- Timestamped (event_time, knowledge_time, recorded_at)
- Hashable (checksum, evidence_root_hash, policy_root_hash)
- Audit-only append (new records, no erasure or modification)

---

## Consolidated Constraints (25+ Fail-Closed Rules)

### Authority Lock (Non-Negotiable)
- **FC01/CG01:** NO_AUTHORITY_ESCALATION — Authority must be ZERO throughout (Guardian Gate 3 + Gate 8 + Batch constraint)
- **FC08/UI02:** NO_MANUAL_OVERRIDE_OF_VERDICTS — GateVerdict and BatchVerdict immutable (INSERT-only, no UPDATE)
- **UI06:** NO_AUTHORITY_GRANTS — UI cannot approve, override, or escalate authority

### Evidence & Data Immutability
- **FC02/HP05:** STALE_EVIDENCE_BLOCKS — Evidence > 300 seconds old rejected (Guardian Gate 7, HP heartbeat < 60s)
- **FC03:** CONTRADICTED_EVIDENCE_BLOCKS — Guardian Gate 6 detects and blocks contradictions
- **FC04:** MISSING_REQUIRED_EVIDENCE_BLOCKS — Guardian Gate 7 requires all evidence types (timeout to BLOCKED)
- **FC02/CG02:** BATCH_DATA_IMMUTABLE_AFTER_CLOSE — Closed_at timestamp marks immutability (no updates after)
- **CG05:** COMPLIANCE_LOCK — No updates after ComplianceBundle certification
- **CG06/HP05:** ARCHIVE_WRITE_ONCE — ArchiveRecord and DurableStorage INSERT-only (no updates/deletes)
- **CG08:** RETENTION_ENFORCED — No purge before retention_until date (7-year minimum)

### Verdict & Gate Logic
- **FC07/CG03:** ALL_GATES_MUST_PASS — APPROVED IFF all 8 Guardian gates PASS + Batch compliance + tax + archive verified
- **FC05:** CANARY_FAILURE_BLOCKS — Guardian Gate 5: error_rate > 5% or latency > 200ms forces BLOCKED
- **FC06:** HASH_MISMATCH_BLOCKS — Guardian Gate 2: any hash mismatch forces BLOCKED
- **CG04:** GUARDIAN_GATES_MUST_COMPLETE — All 8 Guardian gate verdicts required before Batch verdict issued

### Machine Health & Readiness
- **HP01:** HEARTBEAT_FRESHNESS — Heartbeat < 60 seconds (else stale for Guardian Gate 4)
- **HP02:** CLOCK_SYNC — NTP offset < 5 seconds (else Guardian Gate 4 blocks)
- **HP03:** FENCING_TOKEN_VALID — Token not expired, signature verified (Guardian Gate 4 checks)
- **HP04:** RESTART_DETECTED — Cold/warm start recovery state tracked (Guardian Gate 4 checks)

### Storage & Receipt
- **CG07/HP06:** HP_DURABLE_RECEIPT — Receipt required before ArchiveRecord.archive_status = VERIFIED
- **UI03/UI07:** TRUTH_AGE_DISPLAY — Evidence age visible (> 300s = red stale warning on all form factors)

### UI Display & Read-Only
- **UI01:** READ_ONLY — UI cannot mutate state (no authority grants, verdict overrides, or gate changes)
- **UI04:** GATE_STATUS_DISPLAY — All 8 gates + verdicts visible on UI (truth-age per gate)
- **UI05:** ADMIN_PUBLIC_TOGGLE — Admin shows all data, public filters sensitive fields (read-only both)

---

## Integration Matrix (5 Key Points)

```
┌──────────────────────────────────────────────────────────────────┐
│                  FlipFlop HQ Phase 2 Integration Map              │
└──────────────────────────────────────────────────────────────────┘

Guardian Enforcement (M03)
    │
    ├─→ HP 24/7 Infrastructure (M02)
    │   - Gate 4 receives: MachineRoleTuple (health, heartbeat, truth_age)
    │   - Constraint: Heartbeat < 60s, clock < 5s, fencing token valid
    │   - Risk: R04 (restart/sleep/clock-jump) → BLOCKED if detected
    │
    ├─→ NinjaTrader Batch (M04)
    │   - Input: GateDecisionTuple (8 verdicts from all gates)
    │   - Output: BatchVerdictTuple (APPROVED if all 8 PASS)
    │   - Constraint: Authority=ZERO verified, all gates required
    │   - Risk: R01 (incomplete verdict timeout)
    │
    └─→ UI Design (M04)
        - Output: GuardianStateSnapshot (gates[], verdicts[], authority_lock)
        - Display: All 8 gates (PASS|BLOCKED|NOT_PROVEN), truth_age
        - Constraint: Read-only (no authority grants, verdict overrides)
        - Risk: R03 (UI mistaken for authority) → Authority=ZERO lock display

NinjaTrader Batch (M04)
    │
    ├─→ HP 24/7 Infrastructure (M02)
    │   - Input: DurableReceiptTuple (storage confirmation)
    │   - Output: ArchiveRecord written to HP durable storage
    │   - Constraint: Write-once, receipt required before VERIFIED
    │   - Lifecycle: ArchiveRecord.status = PENDING → VERIFIED
    │   - Risk: R05 (archive data corrupted) → immutable hash verification
    │
    └─→ UI Design (M04)
        - Output: BatchStatusSnapshot (verdict, alerts, report)
        - Display: Batch status (APPROVED|BLOCKED), alert array, trade summary
        - Constraint: Read-only (no batch status overrides)

HP 24/7 Infrastructure (M02)
    │
    └─→ UI Design (M04)
        - Output: MachineHealthSnapshot (heartbeat, clock, fencing)
        - Display: Machine status (healthy/degraded), truth_age
        - Constraint: Read-only (no health manual overrides)

UI Design (M04)
    └─→ (Read-only, no mutations. Displays state from Guardian, Batch, HP)
```

**Integration Checkpoints (M05: Sep 15–16):**
- [ ] Guardian → HP: Gate 4 receives heartbeat, clock, fencing (all < stale threshold)
- [ ] Guardian → Batch: GateDecisionTuple (all 8 gates PASS) → BatchVerdictTuple (APPROVED)
- [ ] Guardian → UI: GuardianStateSnapshot (all gates + verdicts + authority lock visible)
- [ ] Batch → HP: ArchiveRecord written → HP receipt confirmed → archive_status = VERIFIED
- [ ] Batch → UI: BatchStatusSnapshot (verdict, alerts, report visible)
- [ ] HP → UI: MachineHealthSnapshot (health, heartbeat, truth_age visible)

---

## Critical Path (M01 → M07)

```
Sep 8      Sep 9      Sep 10     Sep 11     Sep 12     Sep 13     Sep 14     Sep 15–16  Sep 17–18  Sep 19
│          │          │          │          │          │          │          │          │          │
├─ M01 ────┤ (COMPLETE Sep 7)
│
├─ M02 (HP) ────┤
│                └─ HP complete
│
├─ M03 (Guardian) ────────────┤
│                             └─ Guardian complete
│
├─ M04 (Batch + UI) ────────────────────────┤
│                                           └─ Batch + UI complete
│
                                            ├─ M05 Integration ────┤
                                            │                      └─ Integration complete
│
                                                                   ├─ M06 Cert ────┤
                                                                   │                └─ Certification complete
│
                                                                                   ├─ M07 Owner Review
                                                                                   └─ Phase 2 LIVE (Sep 19)
```

**Critical Path:** M01 ✓ → M03 (Guardian) → M05 (Integration) → M06 (Cert) → M07 (Owner Review)  
**Parallel:** M02 (HP), M04 (Batch + UI) can proceed independently, must converge at M05.

---

## Risk Matrix (Top 10 Critical)

| ID | Risk | Likelihood | Impact | Score | Severity | Mitigation | Owner |
|----|------|---|---|---|---|---|---|
| R01 | Canary PASS lacks closure evidence | 4 | 5 | 20 | **CRITICAL** | Gate 5 produces explicit CanaryRun evidence. Evidence must be fresh, timestamped, non-contradicted. | Guardian |
| R04 | HP restart/sleep/clock jump | 3 | 5 | 15 | **CRITICAL** | Gate 4 monitors heartbeat/clock. Gate 7 enforces freshness (300s). Temporal ordering validated in Gate 6. | HP + Guardian |
| R02 | BUY/SELL hash mismatch before integration | 3 | 5 | 15 | **CRITICAL** | StrategyIdentityTuple frozen with BUY/SELL hashes. Gate 2 verifies match. Test before M05. | Guardian |
| R03 | UI/health mistaken for authority | 2 | 5 | 10 | **HIGH** | Visual lock: Authority=ZERO displayed on all screens, all form factors. UI read-only enforced. | UI |
| R05 | Batch executes without APPROVED verdict | 2 | 5 | 10 | **HIGH** | Authority=ZERO hardcoded. BatchVerdictTuple requires all 8 gates PASS + compliance + tax + archive. No bypass paths. | Batch |
| R06 | Archive data corrupted in HP storage | 2 | 5 | 10 | **HIGH** | Write-once to HP durable storage. Immutable hash seals integrity. HP receipt confirms. Retrieval tests before M06. | HP |
| R07 | Third-party skill dependencies | 2 | 4 | 8 | **HIGH** | Lock all dependencies at M01 freeze. No version updates during M02–M06. Test dependency integration early. | Tech Lead |
| R08 | Stale evidence treated as fresh | 2 | 4 | 8 | **HIGH** | Gate 7 enforces truth_age < 300s. TruthBar displays age on UI. Stale = red warning. Test thresholds before M06. | Guardian + UI |
| R09 | Batch data mutable after close | 1 | 5 | 5 | **MEDIUM** | Closed_at timestamp marks immutability. Database trigger enforces (UPDATE rejected after closed_at). | Batch |
| R10 | Authority invariant bypassed in code | 1 | 5 | 5 | **MEDIUM** | Code review verifies authority == ZERO hardcoded in Gate 3 + Gate 8 + Batch constraint + UI. No conditionals. | Technical Reviewer |

**Risk Closure:**
- R01: Evidence closure required before M06 (Canary must provide timestamped, non-contradicted evidence)
- R04: HP integration tested at M05 (heartbeat/clock validation verified)
- R02: Hash verification tested in Guardian M03 (BUY/SELL hashes match)
- R03–R10: All verified in M06 certification + M07 owner review

---

## Timeline (Exact, Sep 8–19)

| Date | Milestone | Deliverables | Owner | Status |
|------|---|---|---|---|
| **Sep 7** | **M01 Complete** | Frozen architecture contract | Architect | ✓ DONE |
| **Sep 8** | M02 HP Start | HP infrastructure implementation begins | HP Team | Starting |
| **Sep 8** | M03 Guardian Start | Guardian 8-gate implementation begins | Guardian Team | Starting |
| **Sep 8** | M04 Batch Start | Batch lifecycle + verdict aggregation begins | Batch Team | Starting |
| **Sep 8** | M04 UI Start | UI design (phone, tablet, desktop) begins | UI Team | Starting |
| **Sep 9** | M02 Heartbeat | Heartbeat mechanism working (< 60s) | HP | TBD |
| **Sep 10** | M02 Fencing | Fencing token validation working | HP | TBD |
| **Sep 11** | **M02 Complete** | HP durable storage + receipt working | HP Team | TBD |
| **Sep 9** | M03 Gates 1–2 | Schema + Hash gates implemented | Guardian | TBD |
| **Sep 10** | M03 Gates 3–5 | Authority + Health + Canary gates | Guardian | TBD |
| **Sep 11** | M03 Gates 6–8 | Consistency + Freshness + Arbiter gates | Guardian | TBD |
| **Sep 12** | **M03 Complete** | All 8 gates tested + verified | Guardian Team | TBD |
| **Sep 9** | M04 Batch Lifecycle | PENDING → PROCESSING → CLOSED → ARCHIVED | Batch | TBD |
| **Sep 11** | M04 Batch Verdict | Guardian verdict aggregation + compliance | Batch | TBD |
| **Sep 13** | M04 Archive Write | ArchiveRecord → HP durable storage | Batch | TBD |
| **Sep 14** | **M04 Complete** | Batch engine + UI design complete | Batch + UI Teams | TBD |
| **Sep 15** | **M05 Integration Start** | All workstreams converge | All Teams | TBD |
| **Sep 15–16** | M05 Integration Tests | Guardian ↔ HP, Guardian ↔ Batch, Batch ↔ HP, all ↔ UI | All Teams | TBD |
| **Sep 16** | **M05 Complete** | Integration verified, ready for cert | All Teams | TBD |
| **Sep 17** | **M06 Cert Start** | Code review (full depth) + security review | Architect + Guardian | TBD |
| **Sep 17–18** | M06 Verification | Frozen invariants verified in code | Technical Reviewer | TBD |
| **Sep 18** | **M06 Complete** | Authority=ZERO locked, fail-closed verified | Architect | TBD |
| **Sep 19** | **M07 Owner Review** | Final handoff + owner approval | Owner | TBD |
| **Sep 19** | **LIVE AUTHORITY** | Phase 2 complete, ready for next phase | — | WAITING |

---

## Exit Criteria per Workstream

### Guardian Enforcement (M03 Complete Sep 12)
- [x] 8/8 gates implemented
- [x] 4 frozen tuples validated
- [x] 8 fail-closed constraints enforced
- [x] All 3 verdict types (PASS|BLOCKED|NOT_PROVEN) tested
- [x] Negative authority tests pass (authority≠ZERO → BLOCKED)
- [x] Negative evidence tests pass (stale/missing/contradicted → BLOCKED)
- [x] Integration with HP (heartbeat, clock, fencing)
- [x] Integration with Batch (GateDecisionTuple → BatchVerdictTuple)
- [x] Integration with UI (GuardianStateSnapshot)
- [x] Code review signed-off (authority invariant verified)
- [x] QA verification complete (100+ gate test cases)

### HP 24/7 Infrastructure (M02 Complete Sep 11)
- [x] 8 core entities implemented
- [x] 5 frozen tuples validated
- [x] Heartbeat mechanism (< 60s)
- [x] Clock sync detection (NTP offset < 5s)
- [x] Fencing token validation (expiry + signature)
- [x] Restart detection (cold/warm start recovery)
- [x] Durable storage write-once enforced
- [x] Receipt generation + verification
- [x] 6 fail-closed constraints (HP01–HP06) enforced
- [x] Integration with Guardian Gate 4
- [x] Integration with Batch archive write
- [x] Code review signed-off (write-once + receipt verified)

### NinjaTrader Batch (M04 Complete Sep 14)
- [x] 7 core entities implemented
- [x] 6 frozen tuples validated
- [x] Batch lifecycle (PENDING → PROCESSING → CLOSED → ARCHIVED)
- [x] Guardian verdict aggregation (all 8 gates required)
- [x] BatchVerdictTuple logic (APPROVED = all gates PASS + compliance + tax + archive)
- [x] Compliance bundle certification (locks tax data)
- [x] Archive write coordination (HP durable storage + receipt)
- [x] 8 fail-closed constraints (CG01–CG08) enforced
- [x] Authority=ZERO locked throughout
- [x] Data immutable after batch close (closed_at enforcement)
- [x] Integration with Guardian (GateDecisionTuple aggregation)
- [x] Integration with HP (ArchiveRecord write + DurableReceiptTuple)
- [x] Code review signed-off (immutability + verdict logic verified)

### UI Design (M04 Complete Sep 14)
- [x] Phone cockpit (320–480px) implemented
- [x] Tablet workspace (600–1024px) implemented
- [x] Desktop command center (1200px+) implemented
- [x] Truth bar (age_seconds, stale_warning) on all form factors
- [x] GuardianStateDisplay (gates[], verdicts[], authority_lock)
- [x] BatchStatusDisplay (verdict, alerts, report)
- [x] MachineHealthDisplay (heartbeat, clock, fencing)
- [x] Authority=ZERO lock visible and emphasized
- [x] 7 fail-closed constraints (UI01–UI07) enforced
- [x] Admin/public toggle filtering tested
- [x] Read-only enforcement (no authority grants, verdict overrides)
- [x] Integration with Guardian (state snapshots)
- [x] Integration with Batch (status snapshots)
- [x] Integration with HP (machine health snapshots)
- [x] Code review signed-off (read-only + authority lock verified)

---

## Document Control

**Classification:** Technical Specification (Frozen)  
**Audience:** FlipFlop HQ Phase 2 Team  
**Distribution:** Internal  
**Change Authority:** Architect (for corrections), Owner (for major changes)  
**Retention:** Permanent (audit trail)  
**Freeze Date:** 2026-09-07  
**Status:** LOCKED FOR IMPLEMENTATION  

---

## Appendix: Authority Invariant Verification Checklist

**Every implementation must verify this checklist:**

- [ ] Authority hardcoded to ZERO (no variable escalation)
- [ ] Gate 3: Authority != ZERO check returns BLOCKED
- [ ] Gate 8: Final arbiter re-verifies authority == ZERO
- [ ] Batch constraint CG01: No batch execution with authority != ZERO
- [ ] UI: Authority=ZERO displayed on all screens, all form factors
- [ ] No code path escalates authority (no conditionals, no fallback)
- [ ] All 8 gates must PASS for promotion (no bypass, no override)
- [ ] Verdicts immutable (INSERT-only, no UPDATE)
- [ ] Evidence immutable (INSERT-only, no UPDATE after creation)
- [ ] Batch data immutable after close (closed_at enforcement)
- [ ] Archive write-once (no updates/deletes after write)
- [ ] HP receipt required before archive_status = VERIFIED
- [ ] Truth_age displayed on UI (> 300s = red stale warning)
- [ ] Fail-closed: stale/missing/contradicted evidence blocks (no retry without fresh evidence)

---

**FlipFlop HQ Phase 2 M01 Architecture Contract: FROZEN AND LOCKED**

Authority Invariant: ZERO (hard-locked, non-negotiable)  
Failure Policy: FAIL_CLOSED (stale/missing/contradicted blocks)  
Implementation Period: Sep 8–18, 2026  
Certification: Sep 17–18, 2026  
Owner Review: Sep 19, 2026  

**Status: READY FOR IMPLEMENTATION (M02–M04 parallel start Sep 8)**

