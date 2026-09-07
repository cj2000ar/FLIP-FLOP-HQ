# Phase 2 M01 → M02/M03/M04 Handoff Document

**Prepared:** 2026-09-07  
**For:** Matt Team (Guardian, HP, Batch, UI implementation)  
**Status:** READY FOR HANDOFF  
**Authority:** ZERO (LOCKED)  

---

## What Is Locked (Non-Negotiable)

### Authority Invariant (Cannot Change)
```
AUTHORITY = ZERO           (no escalation ever)
LIVE = OFF                 (paper-only, no real orders)
BROKER_ORDERS = NONE       (no broker execution)
CONTROL_MUTATION = NONE    (artifacts immutable)
FAILURE_POLICY = FAIL_CLOSED (stale/missing/contradictory blocks)
```

**Status:** Hardcoded in Guardian Gate 3 + Gate 8, Batch constraint CG01, every UI screen.  
**No conditionals. No fallback. No escalation path.**

### Frozen Tuples (31 Total, Immutable)
All tuple schemas are locked. No field additions, deletions, or type changes.
- Guardian: 4 tuples (AuthorityTuple, StrategyIdentityTuple, GateDecisionTuple, DeploymentCandidateTuple)
- HP: 5 tuples (MachineRoleTuple, HeartbeatTuple, FencingTokenTuple, DurableStorageTuple, DurableReceiptTuple)
- Batch: 6 tuples (BatchRunTuple, DayReportTuple, AlertRecordTuple, ComplianceBundleTuple, ArchiveRecordTuple, BatchVerdictTuple)
- UI: 10 tuples (GuardianStateSnapshotTuple, TruthBarTuple, PhoneCockpitTuple, TabletWorkspaceTuple, DesktopCommandTuple, BatchStatusSnapshotTuple, MachineHealthSnapshotTuple, CanaryExecutionDisplayTuple, AlertPanelTuple, OwnerApprovalPanelTuple)

### Frozen Constraints (25+ Fail-Closed Rules)
All constraints locked. No weakening, no conditional paths, no manual overrides.
- Guardian: 8 fail-closed (FC01–FC08)
- HP: 6 fail-closed (HP01–HP06)
- Batch: 8 fail-closed (CG01–CG08)
- UI: 7 fail-closed (UI01–UI07)

### Gate Ordering (Sequential, No Parallel)
Guardian gates execute 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.  
No parallel evaluation. No early bailout (all gates must issue verdict).

### All-or-Nothing Verdict Logic
- **Guardian:** ALL 8 gates must PASS for DecisionCartridge.final_verdict = PASS
- **Batch:** APPROVED IFF all 8 Guardian gates PASS + compliance_passed + tax_verified + archive_verified
- **No conditional escalation, no partial approval, no majority rule.**

### Immutability Enforcement (Database Level)
- Evidence immutable (INSERT-only, no UPDATE)
- GateVerdict immutable (INSERT-only, no UPDATE)
- Batch data immutable after closed_at (UPDATE rejected)
- Archive write-once (INSERT-only, no UPDATE/DELETE)
- Compliance bundle locked after certified_at

### HP Integration Points (Non-Negotiable)
- Guardian Gate 4 requires fresh heartbeat (< 60s)
- Guardian Gate 4 requires clock sync (NTP offset < 5s)
- Guardian Gate 4 requires valid fencing token (not expired, signature verified)
- Guardian Gate 4 detects restart/cold-start/recovery
- Batch archive write must receive HP DurableReceiptTuple before status = VERIFIED

### UI Constraints (Non-Negotiable)
- Authority=ZERO must display on all screens, all form factors
- UI is read-only (no authority grants, verdict overrides, gate changes)
- Truth bar displays age_seconds (> 300s = red stale warning)
- Admin/public toggle filters sensitive data (read-only both)
- No way to escalate authority from UI

---

## What Is NOT Locked (TBD During M02–M04)

### Technology Stack
- Database choice (SQL vs NoSQL) — locked at team kickoff (M02)
- ORM framework — locked at team kickoff (M02)
- API framework — locked at team kickoff (M02)
- Containerization strategy — locked at team kickoff (M02)

### Code Architecture
- Namespace organization
- Class hierarchies (as long as immutability constraints enforced)
- Error handling patterns
- Logging implementation
- Deployment topology

### Testing Strategy
- Test framework choice
- Test coverage targets
- Integration test approach
- Smoke test sequence

### Performance Tuning
- Query optimization (as long as correctness first)
- Caching strategy (as long as immutability respected)
- Connection pooling
- Rate limiting

---

## Parallel Workstream Kickoff (Sep 8)

### M02: HP 24/7 Infrastructure (Sep 8–11)

**Start:** Sep 8, 09:00 ET  
**Owner:** HP Lead  
**Deliverables:**
- MachineRole entity + 8 related entities (MachineHealth, FencingToken, DurableStorage, etc.)
- Heartbeat mechanism (< 60s, sequence tracking)
- Clock sync detection (NTP offset < 5s)
- Fencing token validation (expiry + signature)
- Restart detection (cold/warm start recovery)
- Durable storage write-once enforcement
- Receipt generation + verification (DurableReceiptTuple)
- 6 fail-closed constraints (HP01–HP06) enforced

**Dependencies:**
- [ ] Database schema approved (M02 start)
- [ ] ORM framework chosen (M02 start)
- [ ] Guardian heartbeat/clock expectations documented
- [ ] Batch archive write expectations documented

**Exit Criteria:**
- [x] All entities implemented
- [x] All tuples validated
- [x] Heartbeat working (< 60s)
- [x] Clock sync working (< 5s offset)
- [x] Fencing token validation working
- [x] Restart detection working
- [x] Durable storage write-once + receipt working
- [x] Integration tests with Guardian Gate 4
- [x] Integration tests with Batch archive write
- [x] Code review signed-off

**Skill Sequence (Recommended):**
1. `to-spec` — Translate frozen domain into implementation spec
2. `to-tickets` — Break down into developer tickets
3. `tdd` — Red-green-refactor for heartbeat, clock, fencing
4. `implement` — Build HP infrastructure
5. `code-review` — Full code review (immutability + receipt verified)

**Risks (M02-Specific):**
- R04: Restart/sleep/clock jump detection — validate against Guardian Gate 4 expectations
- R06: Archive data corruption — write-once + receipt + immutable hash

---

### M03: Guardian Enforcement (Sep 8–12)

**Start:** Sep 8, 09:00 ET  
**Owner:** Guardian Lead  
**Deliverables:**
- 7 core entities (ReleaseGate, GateVerdict, EvidenceRecord, AuthorityPolicy, DecisionCartridge, CanaryRun, DeploymentCandidate)
- 8 sequential gates (SCHEMA_AND_IDENTITY → HASH_INTEGRITY → AUTHORITY_POLICY_COMPLIANCE → MACHINE_HEALTH_AND_READINESS → CANARY_EXECUTION → EVIDENCE_CONSISTENCY → FRESHNESS_AND_STALENESS → FINAL_ARBITER)
- 4 frozen tuples (AuthorityTuple, StrategyIdentityTuple, GateDecisionTuple, DeploymentCandidateTuple)
- 8 fail-closed constraints (FC01–FC08) enforced
- Gate verdicts (PASS|BLOCKED|NOT_PROVEN) for all gates

**Dependencies:**
- [ ] Database schema approved (M02 start)
- [ ] ORM framework chosen (M02 start)
- [ ] Canary execution expectations documented (with product team)
- [ ] HP heartbeat/clock/fencing expectations locked (M02 complete)
- [ ] Batch verdict aggregation expectations documented

**Exit Criteria:**
- [x] 8/8 gates implemented
- [x] 4 frozen tuples validated
- [x] All 3 verdict types (PASS|BLOCKED|NOT_PROVEN) tested
- [x] Negative authority tests (authority≠ZERO → BLOCKED)
- [x] Negative evidence tests (stale/missing/contradicted → BLOCKED)
- [x] Gate ordering enforced (sequential 1→8)
- [x] All-or-nothing verdict logic (all 8 must PASS)
- [x] Integration with HP (Gate 4 receives heartbeat/clock/fencing)
- [x] Integration with Batch (GateDecisionTuple array → BatchVerdictTuple)
- [x] Integration with UI (GuardianStateSnapshot)
- [x] Code review signed-off (authority invariant verified in code)
- [x] QA verification (100+ gate test cases)

**Skill Sequence (Recommended):**
1. `to-spec` — Translate frozen domain into implementation spec (per-gate)
2. `to-tickets` — Break down into 8 developer tickets (1 per gate)
3. `tdd` — Red-green-refactor for each gate (copy test cases from spec)
4. `implement` — Build gates 1–8 in sequence
5. `code-review` — Full code review (authority invariant, gate ordering, immutability verified)

**Risks (M03-Specific):**
- R01: Canary PASS lacks closure evidence — Gate 5 must produce timestamped, non-contradicted evidence
- R02: BUY/SELL hash mismatch — Gate 2 must verify before M05 integration
- R03: UI mistaken for authority — Authority=ZERO hardcoding + read-only UI

---

### M04: NinjaTrader Batch (Sep 8–14)

**Start:** Sep 8, 09:00 ET  
**Owner:** Batch Lead  
**Deliverables:**
- 7 core entities (BatchRun, BatchVerdict, DayReport, AlertRecord, ComplianceBundle, TaxDataArchive, ArchiveRecord)
- Batch lifecycle (PENDING → PROCESSING → CLOSED → ARCHIVED)
- Guardian verdict aggregation (all 8 GateDecisionTuple received + processed)
- BatchVerdictTuple logic (APPROVED IFF all 8 gates PASS + compliance + tax + archive verified)
- Compliance bundle certification (locks tax data immutable)
- Archive write coordination (ArchiveRecord → HP durable storage → DurableReceiptTuple)
- 6 frozen tuples validated (BatchRunTuple, DayReportTuple, AlertRecordTuple, ComplianceBundleTuple, ArchiveRecordTuple, BatchVerdictTuple)
- 8 fail-closed constraints (CG01–CG08) enforced

**Dependencies:**
- [ ] Guardian gates locked + integrated (M03 complete)
- [ ] HP archive expectations + receipt format (M02 complete)
- [ ] Database schema approved (M02 start)
- [ ] UI batch status display expectations documented

**Exit Criteria:**
- [x] Batch lifecycle state machine working (PENDING → PROCESSING → CLOSED → ARCHIVED)
- [x] Guardian verdict aggregation (all 8 gates required, APPROVED logic)
- [x] Compliance bundle certification (locks tax data)
- [x] Archive write coordination (HP durable storage + receipt)
- [x] Alert generation + escalation
- [x] Report finalization + export
- [x] All constraint gates (CG01-CG08) enforced
- [x] Authority=ZERO locked throughout (no escalation possible)
- [x] Data immutable after batch close (closed_at enforcement)
- [x] Integration tests with Guardian (all 8 gates)
- [x] Integration tests with HP (archive write + receipt verification)
- [x] Code review signed-off (immutability + verdict logic verified)

**Skill Sequence (Recommended):**
1. `to-spec` — Translate frozen domain into implementation spec
2. `to-tickets` — Break down into developer tickets (lifecycle, verdict, compliance, archive)
3. `tdd` — Red-green-refactor for state machine + verdict aggregation
4. `implement` — Build Batch engine
5. `code-review` — Full code review (authority invariant, immutability, verdict logic verified)

**Risks (M04-Specific):**
- R01: Guardian verdict incomplete (timeout to BLOCKED)
- R02: Batch executes without APPROVED (authority=ZERO hardcoded)
- R05: Compliance data loss (HP durable storage + receipt)

---

### M04: UI Design (Sep 8–14)

**Start:** Sep 8, 09:00 ET  
**Owner:** UI Lead  
**Deliverables:**
- Phone cockpit (320–480px, critical alerts, Authority=ZERO lock)
- Tablet workspace (600–1024px, summary + chart, full gate status)
- Desktop command center (1200px+, full drill-down, evidence tree)
- GuardianStateDisplay (gates[], verdicts[], final_verdict, authority_lock)
- TruthBar (age_seconds, is_fresh, stale_warning > 300s = red)
- BatchStatusDisplay (verdict, alerts, report summary)
- MachineHealthDisplay (heartbeat, clock, fencing token status)
- CanaryDisplay (execution_status, error_rate, latency)
- 10 frozen tuples validated (GuardianStateSnapshotTuple, TruthBarTuple, PhoneCockpitTuple, etc.)
- 7 fail-closed constraints (UI01–UI07) enforced (read-only, authority display, truth bar, etc.)

**Dependencies:**
- [ ] Guardian state snapshot format locked (M03)
- [ ] Batch status snapshot format locked (M04)
- [ ] HP machine health snapshot format locked (M02)
- [ ] Design system assets available (colors, typography, icons)

**Exit Criteria:**
- [x] Phone cockpit working (320–480px)
- [x] Tablet workspace working (600–1024px)
- [x] Desktop command center working (1200px+)
- [x] Truth bar on all form factors (age, stale warning > 300s)
- [x] Guardian state display (all 8 gates + verdicts + authority lock)
- [x] Batch status display (verdict, alerts, report)
- [x] HP machine health display (heartbeat, clock, fencing)
- [x] Authority=ZERO lock visible and emphasized
- [x] Admin/public toggle filtering tested (read-only both)
- [x] Read-only enforcement (no authority grants, verdict overrides)
- [x] Integration tests with Guardian (state snapshots)
- [x] Integration tests with Batch (status snapshots)
- [x] Integration tests with HP (machine health)
- [x] Code review signed-off (read-only + authority lock verified)

**Skill Sequence (Recommended):**
1. `to-spec` — Translate frozen domain into UI spec (per form factor)
2. `prototype` — Build HTML/CSS prototypes (phone, tablet, desktop)
3. `tdd` — Component tests for truth bar, authority display, read-only enforcement
4. `implement` — Build UI components + state wiring
5. `code-review` — Full code review (read-only enforced, authority display verified)

**Risks (M04-Specific):**
- R03: UI mistaken for authority (Authority=ZERO display + read-only emphasized)
- R08: Stale evidence treated as fresh (Truth bar > 300s = red warning)

---

## Integration Checkpoints (M05: Sep 15–16)

**All four workstreams converge. Integration tests required.**

### Checkpoint 1: Guardian ↔ HP (Sep 15)
- [ ] Guardian Gate 4 receives MachineRoleTuple (heartbeat, clock, fencing)
- [ ] Heartbeat < 60s passes Gate 4
- [ ] Heartbeat > 60s fails Gate 4 (BLOCKED)
- [ ] Clock offset < 5s passes Gate 4
- [ ] Clock offset > 5s fails Gate 4 (BLOCKED)
- [ ] Fencing token valid passes Gate 4
- [ ] Fencing token expired fails Gate 4 (BLOCKED)
- [ ] Restart detected by HP → Gate 4 blocks

### Checkpoint 2: Guardian ↔ Batch (Sep 15)
- [ ] All 8 GateDecisionTuple received by Batch
- [ ] All 8 gates PASS → BatchVerdictTuple = APPROVED
- [ ] Any gate BLOCKED → BatchVerdictTuple = BLOCKED
- [ ] Any gate NOT_PROVEN → BatchVerdictTuple = NOT_PROVEN
- [ ] Timeout missing gates → BLOCKED after 5 minutes

### Checkpoint 3: Guardian ↔ UI (Sep 15–16)
- [ ] GuardianStateSnapshot flows to UI
- [ ] All 8 gates + verdicts displayed
- [ ] Authority=ZERO displayed on all form factors
- [ ] Truth age displayed (> 300s = red stale warning)
- [ ] UI read-only (no verdict overrides possible)

### Checkpoint 4: Batch ↔ HP (Sep 16)
- [ ] ComplianceBundle certified (tax data locked)
- [ ] ArchiveRecord created (storage_path immutable)
- [ ] Write request sent to HP durable storage
- [ ] DurableReceiptTuple received (receipt_id, confirmation_hash)
- [ ] ArchiveRecord.archive_status = VERIFIED
- [ ] Batch.closed_at set (data immutable)

### Checkpoint 5: Batch ↔ UI (Sep 15–16)
- [ ] BatchStatusSnapshot flows to UI
- [ ] Batch verdict (APPROVED|BLOCKED) displayed
- [ ] Alert array displayed (sorted by severity)
- [ ] Report summary (trade count, P&L) displayed
- [ ] UI read-only (no batch verdict overrides possible)

### Checkpoint 6: HP ↔ UI (Sep 16)
- [ ] MachineHealthSnapshot flows to UI
- [ ] Machine status (healthy/degraded) displayed
- [ ] Heartbeat displayed (< 60s = green, > 60s = red)
- [ ] Clock offset displayed (< 5s = green, > 5s = red)
- [ ] Fencing token status displayed
- [ ] UI read-only (no health overrides possible)

---

## Skill Recommendations per Workstream

### Guardian Enforcement (M03)
**Recommended Matt Skill Sequence:**
1. `domain-modeling` — Freeze entities + gate logic (if needed for clarification)
2. `to-spec` — Detailed per-gate specification
3. `to-tickets` — Developer tickets (1 per gate)
4. `tdd` — Red-green-refactor (copy test cases from spec verbatim)
5. `implement` — Build gates 1–8
6. `code-review` — Full depth (authority invariant, gate ordering, immutability)

**Estimated Effort:** 40 engineer-hours (5 days × 8 hours)

**Skills per Gate:**
- Gates 1–2: Core data validation (schema, hash)
- Gates 3–4: Authority + infrastructure checks (hardest gates, 2 days)
- Gates 5–6: Execution + logic (canary, consistency)
- Gates 7–8: Freshness + final arbiter (temporal logic)

---

### HP 24/7 Infrastructure (M02)
**Recommended Matt Skill Sequence:**
1. `to-spec` — Detailed infrastructure spec
2. `to-tickets` — Developer tickets (heartbeat, clock, fencing, storage)
3. `tdd` — Red-green-refactor (heartbeat timing, clock sync, receipt verification)
4. `implement` — Build HP entities + mechanisms
5. `code-review` — Full depth (immutability, write-once, receipt verified)

**Estimated Effort:** 24 engineer-hours (3 days × 8 hours)

**Components per Sprint:**
- Day 1: MachineRole + heartbeat (< 60s)
- Day 2: Clock sync + fencing token
- Day 3: Durable storage + receipt + integration tests

---

### NinjaTrader Batch (M04)
**Recommended Matt Skill Sequence:**
1. `to-spec` — Detailed batch + verdict aggregation spec
2. `to-tickets` — Developer tickets (lifecycle, verdict, compliance, archive)
3. `tdd` — Red-green-refactor (state machine, verdict logic, immutability)
4. `implement` — Build Batch engine
5. `code-review` — Full depth (verdict all-or-nothing, immutability enforced)

**Estimated Effort:** 48 engineer-hours (6 days × 8 hours)

**Components per Sprint:**
- Days 1–2: Batch lifecycle (PENDING → PROCESSING → CLOSED → ARCHIVED)
- Days 3–4: Guardian verdict aggregation + compliance certification
- Days 5–6: Archive write coordination + HP integration

---

### UI Design (M04)
**Recommended Matt Skill Sequence:**
1. `to-spec` — Per-form-factor UI spec (phone, tablet, desktop)
2. `prototype` — HTML/CSS prototypes (responsive design, truth bar)
3. `tdd` — Component tests (truth age display, read-only enforcement, authority lock)
4. `implement` — Build UI components + state binding
5. `code-review` — Full depth (read-only enforced, authority display, immutability logic)

**Estimated Effort:** 40 engineer-hours (5 days × 8 hours)

**Components per Sprint:**
- Days 1–2: Phone cockpit + truth bar (responsive)
- Days 3–4: Tablet workspace + desktop command center
- Day 5: Integration tests + authority lock verification

---

### Cross-Workstream (M05)
**Recommended Matt Skill Sequence (Parallel Teams):**
1. `grilling` — Stress-test integration assumptions (Guardian ↔ HP, Guardian ↔ Batch, etc.)
2. `resolving-merge-conflicts` — Consolidate integration branches
3. `code-review` — Full-depth review of merged code

**Estimated Effort:** 32 engineer-hours (4 days × 8 hours, all teams)

---

### M06 Certification
**Recommended Matt Skill Sequence:**
1. `code-review` — Ultra deep code review (authority invariant verified in all code paths)
2. `security-review` — Verify no escalation, no override paths

**Estimated Effort:** 24 engineer-hours (3 days × 8 hours, technical reviewer + architect)

---

### M07 Owner Review
**Recommended Matt Skill Sequence:**
1. `handoff` — Evidence package (all gates PASS, authority ZERO, fail-closed verified)

**Estimated Effort:** 8 engineer-hours (1 day × 8 hours, owner + architect)

---

## Evidence Register (Current State)

**All items must reach PASS or ASSERTED status before M06 certification.**

| Item | Current State | Target | M02 | M03 | M04 | M05 | M06 | M07 |
|------|---|---|---|---|---|---|---|---|
| Phase 2 architecture contract | PASS | LOCKED | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Guardian domain (7 entities, 4 tuples, 8 gates) | PASS | LOCKED | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| HP 24/7 domain (8 entities, 5 tuples, fencing, storage) | PASS | LOCKED | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| NinjaTrader Batch domain (7 entities, 6 tuples, lifecycle) | PASS | LOCKED | — | — | ✓ | ✓ | ✓ | ✓ |
| UI Design domain (12 entities, 10 tuples, 3 form factors) | PASS | LOCKED | — | — | ✓ | ✓ | ✓ | ✓ |
| Tuple freeze (31 total) | PASS | LOCKED | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Constraint freeze (25+) | PASS | LOCKED | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BUY hash (strategy identity) | ASSERTED | VERIFIED | — | TBD | TBD | TBD | ✓ | ✓ |
| SELL hash (strategy identity) | ASSERTED | VERIFIED | — | TBD | TBD | TBD | ✓ | ✓ |
| CONTROL passport | ASSERTED | VERIFIED | — | TBD | TBD | TBD | ✓ | ✓ |
| R5 Canary (evidence closure) | NOT_PROVEN | PROVEN | — | TBD | TBD | TBD | ✓ | ✓ |
| Deployment readiness | BLOCKED | READY | — | — | — | TBD | TBD | ✓ |
| LIVE authority | CLOSED/OFF | CLOSED/OFF | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Authority=ZERO lock (code) | NOT_VERIFIED | VERIFIED | TBD | TBD | TBD | TBD | ✓ | ✓ |
| Fail-closed enforcement (all gates) | NOT_VERIFIED | VERIFIED | TBD | TBD | TBD | TBD | ✓ | ✓ |
| Immutability enforcement (database) | NOT_VERIFIED | VERIFIED | TBD | TBD | TBD | TBD | ✓ | ✓ |

---

## Next Session Checklist

### For All Teams (Sep 8 Morning)
- [ ] Read FLIPFLOP_HQ_PHASE2_M01_ARCHITECTURE_CONTRACT_FINAL.md (this session's prep)
- [ ] Read PHASE2_M01_TO_M02_HANDOFF.md (this document)
- [ ] Read PHASE2_SKILL_ROADMAP.md (skill recommendations)
- [ ] Open M01_REGISTER_FROZEN.json (current evidence state)
- [ ] Database schema approval meeting (tech lead + team leads)
- [ ] ORM/API framework selection meeting (tech lead + team leads)
- [ ] Git repository setup + branch strategy (M02/M03/M04 parallel branches)

### For Guardian Team (M03)
- [ ] Kickoff: Read GUARDIAN_DOMAIN_SPEC_FROZEN_V1.md + GUARDIAN_DOMAIN_MODEL_FROZEN_V1.json
- [ ] Launch Matt `domain-modeling` skill (if clarification needed on gate logic)
- [ ] Launch Matt `to-spec` skill (per-gate detailed specifications)
- [ ] Launch Matt `to-tickets` skill (8 developer tickets, 1 per gate)
- [ ] Sprint planning: Gates 1–2 (schema + hash) in first sprint
- [ ] Database schema review + ORM implementation (M03 day 1)

### For HP Team (M02)
- [ ] Kickoff: Review HP 24/7 section of M01 architecture contract
- [ ] Database schema approval (MachineRole, MachineHealth, FencingToken, DurableStorage, etc.)
- [ ] ORM framework setup
- [ ] Sprint planning: Heartbeat mechanism (day 1), clock sync (day 2), fencing + storage (day 3)
- [ ] Guardian integration expectations documented (Gate 4 requirements)
- [ ] Batch integration expectations documented (archive write + receipt)

### For Batch Team (M04)
- [ ] Kickoff: Read NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md + NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json
- [ ] Database schema approval (BatchRun, BatchVerdict, ComplianceBundle, ArchiveRecord, etc.)
- [ ] ORM framework setup
- [ ] Sprint planning: Batch lifecycle (days 1–2), verdict aggregation (days 3–4), archive write (days 5–6)
- [ ] Guardian integration expectations locked (all 8 GateDecisionTuple format)
- [ ] HP integration expectations locked (DurableReceiptTuple format, write-once requirement)

### For UI Team (M04)
- [ ] Kickoff: Read UI Design section of M01 architecture contract
- [ ] Design system / component library setup (colors, typography, icons)
- [ ] Responsive design validation (phone 320–480px, tablet 600–1024px, desktop 1200px+)
- [ ] Sprint planning: Phone cockpit + truth bar (days 1–2), tablet + desktop (days 3–4), integration (day 5)
- [ ] Guardian state snapshot format locked
- [ ] Batch status snapshot format locked
- [ ] HP machine health snapshot format locked

### For Tech Lead
- [ ] Database schema review + approval (all 4 workstreams)
- [ ] Dependency lock (all third-party libraries pinned during M02–M06)
- [ ] Git strategy (master + M02/M03/M04 parallel branches, M05 merge)
- [ ] CI/CD setup (tests required before merge, code review gate)
- [ ] Monitoring setup (deployment candidate verification, gate verdicts logging)

### For Architect
- [ ] Verify all workstreams have frozen specs + skill sequences ready
- [ ] Prepare code review checklist (authority invariant, immutability, fail-closed)
- [ ] Schedule M05 integration checkpoints (all 6 checkpoints)
- [ ] Schedule M06 certification code review (full depth)
- [ ] Prepare M07 handoff evidence package template

---

## Document Control

**Classification:** Implementation Handoff (Frozen)  
**Audience:** FlipFlop HQ Phase 2 Team  
**Distribution:** Internal  
**Change Authority:** Architect (for corrections), Owner (for major changes)  
**Retention:** Permanent (audit trail)  
**Handoff Date:** 2026-09-07  
**Implementation Start:** 2026-09-08  
**Status:** READY FOR TEAM DISTRIBUTION  

---

**Phase 2 M01 → M02/M03/M04 Handoff: LOCKED AND READY**

Authority Invariant: ZERO (hard-locked, non-negotiable)  
Parallel Workstreams: HP (M02), Guardian (M03), Batch + UI (M04)  
Integration Checkpoint: M05 (Sep 15–16)  
Certification: M06 (Sep 17–18)  
Owner Review: M07 (Sep 19)  

**Status: READY FOR IMPLEMENTATION (Sep 8 09:00 ET)**

