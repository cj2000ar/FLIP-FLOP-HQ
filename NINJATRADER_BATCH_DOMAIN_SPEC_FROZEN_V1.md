# NinjaTrader Batch Domain Model — Phase 2 Frozen Specification

**Status:** PHASE_2_FROZEN_M01  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**Live Status:** OFF (LOCKED IMMUTABLE)  
**Date:** 2026-09-07  
**Owner:** Domain Architect  

---

## Executive Summary

This specification freezes the NinjaTrader Batch domain model for Phase 2 implementation. Seven core entities, six frozen tuples, eight constraint gates, and three Guardian integration points define an end-of-day batch execution system with Authority=ZERO hard-locked throughout.

**Key invariant:** Batch cannot execute real trades (Authority=ZERO, LIVE=OFF). All data immutable after market close. Guardian 8-gate verdicts required before batch approval. HP 24/7 Infrastructure durable storage required for archive finality.

**Workflow:** market close → NinjaTrader export → alerts → summary → compliance → archive → CLOSED

---

## Authority Invariant (Hard Locked)

```
AUTHORITY = ZERO (no escalation ever)
LIVE = OFF (paper-only, no real orders)
BROKER_ORDERS = NONE (no broker execution)
CONTROL_MUTATION = NONE (batch data immutable after close)
FAILURE_POLICY = FAIL_CLOSED (stale/missing/contradictory blocks)
```

**Status:** CANNOT CHANGE. Every implementation must verify this invariant at batch initialization, verdict issuance, and archive finalization.

---

## Domain Entities (7 Core)

### 1. BatchRun

**Purpose:** End-of-day batch execution session. Spans market close → NinjaTrader export → alerts → summary → archive.

**Immutable Fields:**
- `batch_id` (UUID): Unique identifier
- `run_date` (date): Batch execution date (YYYY-MM-DD)
- `market_open_time` (timestamp): Market open (UTC)
- `market_close_time` (timestamp): Market close (UTC)
- `mode` (enum: PAPER|SHADOW|ANALYSIS): Execution mode
  - **PAPER:** Paper-only execution (no real orders)
  - **SHADOW:** Shadow-mode (monitoring only, no execution)
  - **ANALYSIS:** Post-analysis of historical data
- `correlation_id` (UUID): Links batch to deployment candidate + Guardian verdicts

**Mutable Fields:**
- `batch_status` (enum: PENDING|PROCESSING|CLOSED|ARCHIVED)

**Constraints:**
- `batch_id` globally unique
- `run_date` must be trading day (no weekends/holidays)
- `market_open_time < market_close_time`
- `mode` immutable after creation
- `correlation_id` must match a Guardian deployment candidate
- `batch_status` state machine: PENDING → PROCESSING → CLOSED → ARCHIVED
- `closed_at` marks data immutability: no further modifications allowed
- **Authority invariant:** mode must be PAPER/SHADOW/ANALYSIS (never LIVE)

**Lifecycle:**
```
PENDING (created) → PROCESSING (market open/close) 
  → CLOSED (export + summary + compliance complete) 
  → ARCHIVED (archive finalized)
```

---

### 2. BatchVerdict

**Purpose:** Final authorization verdict for batch execution. Aggregates Guardian 8-gate verdicts + compliance + tax + archive checks. **Batch cannot execute without APPROVED verdict.**

**Immutable Fields:**
- `verdict_id` (UUID): Unique verdict identifier
- `batch_id` (UUID): Foreign key to BatchRun
- `guardian_gate_results` (array of GateDecisionTuple): All 8 Guardian gate verdicts
  - Must contain exactly 8 entries (gates 1-8)
  - Each entry: (gate_id, verdict, evidence_id, event_time, knowledge_time)
- `compliance_passed` (boolean): Compliance verification result
- `tax_verified` (boolean): Tax data accuracy verified
- `archive_verified` (boolean): Archive integrity verified
- `batch_status` (enum: APPROVED|BLOCKED|NOT_PROVEN): Final verdict
- `event_time` (timestamp): When verdict was issued
- `knowledge_time` (timestamp): When all evidence was known
- `authority_used` (enum: ZERO): Authority level at verdict

**Mutable Fields:**
- `verdict_reasoning` (string): Human-readable explanation
- `policy_hash` (SHA256): Hash of applied policy

**Verdict Logic:**
- **APPROVED:** All 8 Guardian gates = PASS AND compliance_passed=true AND tax_verified=true AND archive_verified=true
- **BLOCKED:** ANY gate = BLOCKED OR compliance/tax/archive verification = false
- **NOT_PROVEN:** ANY gate = NOT_PROVEN (waiting for evidence resolution)

**Constraints:**
- `verdict_id` globally unique
- `batch_id` foreign key must exist
- `guardian_gate_results` array must contain exactly 8 GateDecisionTuple entries
- `batch_status = APPROVED` IFF all conditions met (all-or-nothing)
- `batch_status = BLOCKED` if ANY gate BLOCKED or verification failed
- `batch_status = NOT_PROVEN` if ANY gate NOT_PROVEN
- Verdict immutable after creation (audit-only append)
- `authority_used` must be ZERO (hard-locked)
- `event_time <= knowledge_time`
- Guardian gate results immutable (copy-on-write)

---

### 3. DayReport

**Purpose:** End-of-day summary report. Aggregates trading activity, P&L, risk metrics, and alert counts. **Final snapshot of batch performance.**

**Immutable Fields:**
- `report_id` (UUID): Unique identifier
- `batch_id` (UUID): Foreign key to BatchRun
- `report_date` (date): Report date = batch.run_date
- `trade_count` (int, default 0): Total trades processed
- `pnl_summary` (JSON): P&L breakdown
  - Required fields: `gross_pnl`, `net_pnl`, `currency`, `timestamp`
  - Example: `{gross_pnl: 1500.00, net_pnl: 1350.00, currency: USD, timestamp: 2026-09-07T20:15:00Z}`
- `risk_metrics` (JSON): Risk data
  - Required fields: `max_drawdown`, `var_95`, `sharpe_ratio`, `win_rate`, `avg_win`, `avg_loss`
  - Example: `{max_drawdown: 0.05, var_95: 2000, sharpe_ratio: 1.2, win_rate: 0.65, avg_win: 250, avg_loss: 100}`
- `alert_count` (int, default 0): Number of alerts generated
- `alert_summary` (JSON): Count by severity
  - Required fields: `critical`, `high`, `medium`, `low`
  - Example: `{critical: 0, high: 1, medium: 2, low: 0}`
- `export_time` (timestamp): When NinjaTrader export completed

**Mutable Fields:**
- `report_status` (enum: DRAFT|FINALIZED|ARCHIVED)

**Constraints:**
- `report_id` globally unique
- `batch_id` foreign key must exist
- `report_date = batch.run_date` (must match)
- `trade_count >= 0`
- `pnl_summary` must contain all required fields
- `risk_metrics` must contain all required fields
- `alert_count = sum(alert_summary.critical + alert_summary.high + alert_summary.medium + alert_summary.low)`
- `export_time` must be after `batch.market_close_time`
- `report_status` state machine: DRAFT → FINALIZED → ARCHIVED
- `finalized_at` marks immutability: no further modifications
- Report immutable after FINALIZED

---

### 4. AlertRecord

**Purpose:** Trade alert or anomaly detection. Generated during batch processing; sources: risk monitors, compliance checks, anomaly detection. **Read-only on UI dashboard.**

**Immutable Fields:**
- `alert_id` (UUID): Unique identifier
- `batch_id` (UUID): Foreign key to BatchRun
- `report_id` (UUID, optional): Foreign key to DayReport
- `severity` (enum: CRITICAL|HIGH|MEDIUM|LOW): Alert severity level
- `alert_type` (string): Category
  - Examples: `RISK_LIMIT_BREACH`, `DRAWDOWN_WARNING`, `ANOMALY`, `COMPLIANCE_FLAG`, `TAX_DISCREPANCY`
- `message` (string): Human-readable alert text
- `context` (JSON): Alert-specific context
  - Example: `{symbol: ES, quantity: 10, price: 5500.00, threshold: 0.05, actual_value: 0.07}`
- `timestamp` (timestamp): When alert was generated

**Mutable Fields:**
- `escalation_flag` (boolean, default false): If true, alert requires manual review
- `escalated_to` (string): User/role alert was escalated to
- `resolved` (boolean, default false): If true, alert acknowledged/resolved
- `resolved_at` (timestamp): When alert was resolved

**Constraints:**
- `alert_id` globally unique
- `batch_id` foreign key must exist
- `severity` immutable after creation
- `alert_type` immutable after creation
- `timestamp` must be within [batch.initiated_at, batch.closed_at]
- `escalation_flag = true` requires `escalated_to` to be set
- `resolved = true` requires `resolved_at` to be set
- `resolved_at >= timestamp`
- Alert counts in DayReport.alert_summary must match alert records

---

### 5. ComplianceBundle

**Purpose:** Immutable compliance package. Locks tax summary, receipt hashes, and audit trail at batch close. **Certification marks immutability.**

**Immutable Fields:**
- `bundle_id` (UUID): Unique identifier
- `batch_id` (UUID): Foreign key to BatchRun
- `tax_summary` (JSON): Tax data (immutable after certification)
  - Required fields: `gains`, `losses`, `wash_sales`, `adjustments`, `total_taxable_income`
  - Example: `{gains: 5000, losses: 2000, wash_sales: 500, adjustments: 0, total_taxable_income: 2500}`
- `receipt_hashes` (array of SHA256 strings): Hashes of all receipts/executions
  - Must not be empty
  - Immutable (array is copy-on-write)
- `audit_trail` (array of JSON): Chronological log of compliance checks
  - Immutable (append-only)
  - Each entry: `{check: string, result: PASS|FAIL|WARNING, timestamp: timestamp, details: json}`
- `certification_time` (timestamp): When bundle was certified/locked
- `certifying_authority` (string): System/role that certified bundle
- `bundle_hash` (SHA256): Hash of entire bundle (immutability seal)

**Mutable Fields:**
- `bundle_status` (enum: DRAFT|CERTIFIED|ARCHIVED)

**Constraints:**
- `bundle_id` globally unique
- `batch_id` foreign key must exist
- `tax_summary` must contain all required fields
- `receipt_hashes` array must not be empty
- `receipt_hashes` immutable (array is copy-on-write, cannot modify after certification)
- `audit_trail` immutable (append-only log, cannot modify entries)
- `certification_time` marks immutability: no further modifications
- `bundle_hash` must match cryptographic hash of tax_summary + receipt_hashes + audit_trail
- `bundle_status` state machine: DRAFT → CERTIFIED → ARCHIVED
- `certified_at = certification_time`
- Bundle immutable after CERTIFIED

---

### 6. TaxDataArchive

**Purpose:** Write-once, append-only tax data archive. Sourced from ComplianceBundle. Retained per regulatory requirements. **Long-term regulatory compliance.**

**Immutable Fields:**
- `archive_id` (UUID): Unique identifier
- `batch_id` (UUID): Foreign key to BatchRun
- `bundle_id` (UUID): Foreign key to ComplianceBundle
- `archive_date` (date): Archive creation date = batch.run_date
- `tax_year` (int): Fiscal year for tax data
- `taxable_events` (array of JSON): List of taxable events
  - Immutable (write-once)
  - Each entry: `{type: string, date: date, quantity: int, basis: decimal, proceeds: decimal, gain_loss: decimal}`
- `total_gain_loss` (decimal): Sum of all gains/losses
- `retention_years` (int, default 7): Years to retain (regulatory minimum)
- `retention_until` (date): Date after which archive can be purged
  - Calculated as: `archive_date + retention_years years`

**Mutable Fields:**
- `archive_status` (enum: ACTIVE|ARCHIVED|PURGED)

**Constraints:**
- `archive_id` globally unique
- `batch_id` foreign key must exist
- `bundle_id` foreign key must exist
- `archive_date = batch.run_date`
- `tax_year` immutable after creation
- `taxable_events` immutable (write-once)
- `retention_years >= 7` (regulatory minimum)
- `retention_until = archive_date + retention_years`
- `archive_status` state machine: ACTIVE → ARCHIVED → PURGED
- **No purge allowed before `retention_until` date**
- Archive immutable after creation

---

### 7. ArchiveRecord

**Purpose:** Immutable archive entry in HP durable storage. Sourced from ComplianceBundle + DayReport. Read-only retrieval only. **Final audit trail entry.**

**Immutable Fields:**
- `archive_record_id` (UUID): Unique identifier
- `batch_id` (UUID): Foreign key to BatchRun
- `report_id` (UUID, optional): Foreign key to DayReport
- `bundle_id` (UUID, optional): Foreign key to ComplianceBundle
- `storage_path` (string): Path in HP durable storage (immutable)
  - Example: `/durable/2026-09-07/batch-uuid-001.tar.gz`
- `storage_tier` (enum: HOT|WARM|COLD, default WARM): Storage access tier
- `retention_years` (int, default 7): Regulatory retention requirement
- `immutable_hash` (SHA256): SHA256 of archived data (immutability seal)
- `retrieval_metadata` (JSON): Metadata for retrieval
  - Required fields: `format`, `size_bytes`, `created_date`, `archived_date`
  - Example: `{format: tarball, size_bytes: 5242880, created_date: 2026-09-07, archived_date: 2026-09-07}`
- `hp_receipt` (JSON): HP storage receipt (set when verified)
  - Required fields (when set): `receipt_id`, `timestamp`, `confirmation_hash`

**Mutable Fields:**
- `archive_status` (enum: WRITTEN|VERIFIED|RETRIEVED|PURGED)

**Constraints:**
- `archive_record_id` globally unique
- `batch_id` foreign key must exist
- `storage_path` immutable after creation
- `immutable_hash` immutable (write-once integrity seal)
- `archive_status` state machine: WRITTEN → VERIFIED → RETRIEVED → PURGED
- `verified_at` set only when `archive_status = VERIFIED`
- **No updates allowed after creation (INSERT only)**
- `retrieval_metadata` must contain all required fields
- `hp_receipt` must be populated before `archive_status = VERIFIED`
- Write-once to HP durable storage (no overwrites)

---

## Frozen Tuples (6 Core)

### 1. BatchRunTuple

**Schema:** `(batch_id, run_date, market_open_time, market_close_time, mode, correlation_id)`

**Description:** Immutable snapshot of batch identity + timing.

**Example:**
```
(
  uuid-batch-001,
  2026-09-07,
  2026-09-07T13:30:00Z,
  2026-09-07T20:00:00Z,
  PAPER,
  uuid-corr-001
)
```

**Constraints:**
- All fields immutable
- Hashable for audit trail
- Used as primary key for batch identity

---

### 2. DayReportTuple

**Schema:** `(report_id, batch_id, trade_count, pnl_summary, risk_metrics, alert_count, export_time)`

**Description:** Immutable snapshot of end-of-day summary.

**Example:**
```
(
  uuid-report-001,
  uuid-batch-001,
  42,
  {gross_pnl: 1500.00, net_pnl: 1350.00, currency: USD, timestamp: 2026-09-07T20:15:00Z},
  {max_drawdown: 0.05, var_95: 2000, sharpe_ratio: 1.2, win_rate: 0.65, avg_win: 250, avg_loss: 100},
  3,
  2026-09-07T20:15:00Z
)
```

**Constraints:**
- All fields immutable after FINALIZED
- Hashable for audit trail
- Used for dashboard display and historical record

---

### 3. AlertRecordTuple

**Schema:** `(alert_id, batch_id, severity, alert_type, message, timestamp, escalation_flag)`

**Description:** Immutable snapshot of alert + context.

**Example:**
```
(
  uuid-alert-001,
  uuid-batch-001,
  HIGH,
  RISK_LIMIT_BREACH,
  'Drawdown exceeded 5%',
  2026-09-07T16:45:00Z,
  true
)
```

**Constraints:**
- All fields immutable
- Hashable for audit trail
- Used for alert feeds and escalation workflows

---

### 4. ComplianceBundleTuple

**Schema:** `(bundle_id, batch_id, tax_summary, receipt_hashes, audit_trail, certification_time)`

**Description:** Immutable snapshot of compliance data at certification.

**Example:**
```
(
  uuid-bundle-001,
  uuid-batch-001,
  {gains: 5000, losses: 2000, wash_sales: 500, adjustments: 0, total_taxable_income: 2500},
  [sha256-hash-1, sha256-hash-2, sha256-hash-3, ...],
  [
    {check: WASH_SALE, result: PASS, timestamp: 2026-09-07T20:20:00Z, details: {}},
    {check: RECEIPT_INTEGRITY, result: PASS, timestamp: 2026-09-07T20:21:00Z, details: {}},
    {check: TAX_CALCULATION, result: PASS, timestamp: 2026-09-07T20:22:00Z, details: {}}
  ],
  2026-09-07T20:30:00Z
)
```

**Constraints:**
- All fields immutable after CERTIFIED
- Hashable for regulatory audit
- Used for tax filing and compliance verification

---

### 5. ArchiveRecordTuple

**Schema:** `(archive_record_id, batch_id, storage_path, retention_years, immutable_hash, retrieval_metadata)`

**Description:** Immutable snapshot of archived data in HP storage.

**Example:**
```
(
  uuid-arch-001,
  uuid-batch-001,
  /durable/2026-09-07/batch-001.tar.gz,
  7,
  sha256-hash-immutable-seal-here,
  {format: tarball, size_bytes: 5242880, created_date: 2026-09-07, archived_date: 2026-09-07}
)
```

**Constraints:**
- All fields immutable
- Write-once to HP durable storage
- Hashable for archive integrity verification

---

### 6. BatchVerdictTuple

**Schema:** `(verdict_id, batch_id, guardian_gate_results, compliance_passed, tax_verified, archive_verified, batch_status)`

**Description:** Immutable snapshot of batch authorization verdict.

**Example:**
```
(
  uuid-verdict-001,
  uuid-batch-001,
  [
    GateDecisionTuple(gate_id: 1, verdict: PASS, ...),
    GateDecisionTuple(gate_id: 2, verdict: PASS, ...),
    GateDecisionTuple(gate_id: 3, verdict: PASS, ...),
    GateDecisionTuple(gate_id: 4, verdict: PASS, ...),
    GateDecisionTuple(gate_id: 5, verdict: PASS, ...),
    GateDecisionTuple(gate_id: 6, verdict: PASS, ...),
    GateDecisionTuple(gate_id: 7, verdict: PASS, ...),
    GateDecisionTuple(gate_id: 8, verdict: PASS, ...)
  ],
  true,
  true,
  true,
  APPROVED
)
```

**Constraints:**
- All fields immutable after creation
- `guardian_gate_results` must contain exactly 8 GateDecisionTuple entries
- `batch_status = APPROVED` IFF all gates PASS AND compliance_passed AND tax_verified AND archive_verified
- Hashable for audit trail
- Authority=ZERO must be verified across all gate results

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ GUARDIAN ENFORCEMENT DOMAIN                                         │
│ GateDecisionTuple (8 verdicts from gates 1-8)                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────┐
        │ BatchRun Created (PENDING)       │
        │ - batch_id, run_date, mode      │
        │ - correlation_id → Guardian     │
        └──────────────────┬───────────────┘
                           │
                           ▼
        ┌──────────────────────────────────┐
        │ Market Close Triggered           │
        │ BatchRun status: PROCESSING      │
        └──────────────────┬───────────────┘
                           │
        ┌──────────────────┼──────────────────────┐
        │                  │                      │
        ▼                  ▼                      ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
    │ NinjaTrader │  │ Risk Monitors│  │ Compliance   │
    │ Export      │  │ Alert Gen    │  │ Checks       │
    └──────┬──────┘  └──────┬───────┘  └──────┬───────┘
           │                │                  │
           ▼                ▼                  ▼
    ┌─────────────────────────────────────────────────┐
    │ DayReport       AlertRecord (N)  ComplianceBundle
    │ - pnl_summary   - severity       - tax_summary
    │ - risk_metrics  - alert_type     - receipt_hashes
    │ - trade_count   - message        - audit_trail
    │ - alert_count   - timestamp      - certification
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
        ┌──────────────────────────────────┐
        │ Guardian Verdict Aggregation     │
        │ - All 8 gates results            │
        │ - Compliance + Tax + Archive     │
        │ - BatchVerdictTuple created      │
        └──────────────────┬───────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼ (if ALL checks pass)                ▼ (if ANY check fails)
    ┌──────────────┐                    ┌──────────────┐
    │ APPROVED     │                    │ BLOCKED or   │
    │ Proceed      │                    │ NOT_PROVEN   │
    │ to Archive   │                    │ Halt batch   │
    └──────┬───────┘                    └──────────────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │ Archive Write (HP Durable)       │
    │ - ArchiveRecord created          │
    │ - storage_path immutable         │
    │ - immutable_hash set             │
    │ - HP receipt required            │
    └──────────────────┬───────────────┘
           │
           ▼ (when HP confirms write)
    ┌──────────────────────────────────┐
    │ BatchRun Closed (CLOSED)         │
    │ - closed_at timestamp set        │
    │ - All data now immutable         │
    └──────────────────┬───────────────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │ Archive Finalized (ARCHIVED)     │
    │ - ArchiveRecord status VERIFIED  │
    │ - Retention lifecycle active     │
    │ - Read-only from here on         │
    └──────────────────────────────────┘
```

---

## Constraint Gates (8 Fail-Closed)

| ID | Constraint | Enforcement | Test Case |
|----|------------|-------------|-----------|
| **CG01** | NO_AUTHORITY_ESCALATION | BatchRun.mode and BatchVerdict.authority_used must be ZERO | If any guardian_gate_results contain authority≠ZERO, batch_status = BLOCKED |
| **CG02** | BATCH_DATA_IMMUTABLE_AFTER_CLOSE | After BatchRun.closed_at is set, no updates allowed | Any update after closed_at throws immutability_violation |
| **CG03** | VERDICT_REQUIRES_ALL_GATES_PASS | BatchVerdict.batch_status = APPROVED only if ALL conditions met | If any guardian gate = BLOCKED/NOT_PROVEN, batch_status must be BLOCKED/NOT_PROVEN |
| **CG04** | GUARDIAN_GATES_MUST_COMPLETE | BatchRun cannot close without BatchVerdict with all 8 gates | Attempting to close without complete verdict throws required_verdict_missing |
| **CG05** | COMPLIANCE_LOCK | After ComplianceBundle.certified_at, no updates allowed | Any update to tax_summary after certified_at throws immutability_violation |
| **CG06** | ARCHIVE_WRITE_ONCE | ArchiveRecord INSERT only, never UPDATE/DELETE | Attempting to UPDATE/DELETE ArchiveRecord throws write_once_violation |
| **CG07** | HP_DURABLE_RECEIPT | ArchiveRecord.hp_receipt required before VERIFIED | Attempting to verify without hp_receipt throws missing_receipt |
| **CG08** | RETENTION_ENFORCED | TaxDataArchive cannot purge before retention_until | Attempting to purge before date throws retention_not_met |

---

## Integration Points

### 1. Guardian Enforcement Domain

**Receives:**
- `GateDecisionTuple` (8 verdicts from Guardian gates 1-8)
  - Each tuple contains: gate_id, verdict (PASS|BLOCKED|NOT_PROVEN), evidence_id, event_time, knowledge_time
  - All 8 must be received before batch can issue verdict

**Sends:**
- `BatchVerdictTuple` (final verdict for batch approval)
  - Contains aggregated guardian_gate_results array
  - Batch cannot execute without APPROVED verdict

**Constraint:**
- Batch cannot execute if ANY gate = BLOCKED or NOT_PROVEN
- Authority=ZERO must be verified across all gate results
- No conditional escalation paths

**Integration Example:**
```json
{
  "batch_id": "uuid-batch-001",
  "guardian_gate_results": [
    {"gate_id": 1, "verdict": "PASS", "event_time": "2026-09-07T20:01:00Z"},
    {"gate_id": 2, "verdict": "PASS", "event_time": "2026-09-07T20:02:00Z"},
    {"gate_id": 3, "verdict": "PASS", "event_time": "2026-09-07T20:03:00Z"},
    {"gate_id": 4, "verdict": "PASS", "event_time": "2026-09-07T20:04:00Z"},
    {"gate_id": 5, "verdict": "PASS", "event_time": "2026-09-07T20:05:00Z"},
    {"gate_id": 6, "verdict": "PASS", "event_time": "2026-09-07T20:06:00Z"},
    {"gate_id": 7, "verdict": "PASS", "event_time": "2026-09-07T20:07:00Z"},
    {"gate_id": 8, "verdict": "PASS", "event_time": "2026-09-07T20:08:00Z"}
  ],
  "batch_status": "APPROVED"
}
```

---

### 2. HP 24/7 Infrastructure Domain

**Receives:**
- `MachineRoleTuple` (health, heartbeat, truth_age from HP machines)
  - Used by Guardian Gate 4 (Machine Health and Readiness)
- `DurableReceiptTuple` (storage confirmation from HP durable storage)
  - Used to verify ArchiveRecord write completion

**Sends:**
- `ArchiveRecordTuple` (immutable storage path + hash)
  - Storage path: `/durable/{run_date}/batch-{batch_id}.tar.gz`
  - Immutable hash confirms integrity
  - HP receipt marks finality

**Constraints:**
- Archive must be accepted by HP durable storage before batch closes
- HP receipt required before ArchiveRecord.archive_status = VERIFIED
- No modification/deletion allowed after write
- Storage path immutable (write-once)

**Integration Example:**
```json
{
  "archive_record_id": "uuid-arch-001",
  "batch_id": "uuid-batch-001",
  "storage_path": "/durable/2026-09-07/batch-uuid-batch-001.tar.gz",
  "immutable_hash": "sha256:abc123def456...",
  "retrieval_metadata": {
    "format": "tarball",
    "size_bytes": 5242880,
    "created_date": "2026-09-07",
    "archived_date": "2026-09-07"
  },
  "hp_receipt": {
    "receipt_id": "uuid-receipt-001",
    "timestamp": "2026-09-07T20:45:00Z",
    "confirmation_hash": "sha256:xyz789..."
  }
}
```

---

### 3. UI Control Center Domain

**Receives:**
- `BatchStatusSnapshot` (batch status, alerts, report summary)
  - Batch ID, verdict status (APPROVED|BLOCKED|NOT_PROVEN)
  - Alert array with severity breakdown
  - Report summary: trade count, P&L, risk metrics

**Sends:**
- `AlertRecordTuple` → dashboard display (read-only)
- `DayReportTuple` → summary view (read-only)
- Guardian verdict status (read-only)

**Constraints:**
- Authority=ZERO must be visible on all screens
- UI display read-only (no authority grants, no verdict overrides)
- Alerts are escalation-only (no state changes on UI)
- Stale truth detection required (> 300s = red warning)

**UI Display Rules:**
- Show Authority=ZERO prominently
- Display batch status with explanation
- Alert feed sorted by severity (CRITICAL → HIGH → MEDIUM → LOW)
- Report summary: trade count, gross P&L, net P&L, risk metrics
- Guardian gate results: all 8 gates + final verdict
- Truth bar: age in seconds, stale warning if > 300s

---

## Key Invariants (Must Be Verified in Code)

### Authority Lock (Non-Negotiable)

```python
# Hardcoded check at batch creation
if batch.mode != PAPER and batch.mode != SHADOW and batch.mode != ANALYSIS:
    raise InvalidBatchMode("mode must be PAPER, SHADOW, or ANALYSIS")
    
# Hardcoded check at verdict issuance
if verdict.authority_used != ZERO:
    verdict.batch_status = BLOCKED
    raise AuthorityEscalationDetected("authority must be ZERO")
```

**No conditionals. No fallback. No escalation path.**

### Evidence Immutability

```python
# All evidence inserted, never updated
class BatchRunTuple:
    batch_id: UUID  # immutable
    run_date: date  # immutable
    market_open_time: timestamp  # immutable
    market_close_time: timestamp  # immutable
    mode: enum  # immutable
    correlation_id: UUID  # immutable
    # No UPDATE path exists
```

### Verdict Immutability

```python
# Verdicts append-only
class BatchVerdictTuple:
    verdict_id: UUID  # immutable
    batch_status: enum  # immutable
    guardian_gate_results: array  # immutable
    compliance_passed: bool  # immutable
    tax_verified: bool  # immutable
    archive_verified: bool  # immutable
    # No UPDATE path exists
```

### Batch Closure Marks Immutability

```python
# After closed_at is set, no mutations allowed
if batch.closed_at is not None:
    raise ImmutabilityViolation("batch data locked after close")
```

### Guardian Gate Aggregation

```python
# All 8 gates must PASS for batch APPROVED
if verdict.batch_status == APPROVED:
    assert len(verdict.guardian_gate_results) == 8
    assert all(gate.verdict == PASS for gate in verdict.guardian_gate_results)
    assert verdict.compliance_passed == true
    assert verdict.tax_verified == true
    assert verdict.archive_verified == true
```

---

## Archive Retention Lifecycle

```
Archive Created (ACTIVE)
  ↓ (archive_date + retention_years)
Retention Period Active
  ↓ (on retention_until date)
Available for Purge (status = PURGED only after this date)
  ↓
Archive Purged (compliance met, data destroyed)
```

**Key Rules:**
- No purge before `retention_until` date
- Retention minimum 7 years (regulatory)
- Archive status immutable until PURGED
- After PURGED, record archived but data gone

---

## Database Schema Constraints (Pseudo-SQL)

```sql
-- BatchRun table
CREATE TABLE batch_runs (
    batch_id UUID PRIMARY KEY NOT NULL,
    run_date DATE NOT NULL,
    market_open_time TIMESTAMP NOT NULL,
    market_close_time TIMESTAMP NOT NULL,
    mode ENUM('PAPER', 'SHADOW', 'ANALYSIS') NOT NULL,
    correlation_id UUID NOT NULL REFERENCES deployment_candidates(candidate_id),
    batch_status ENUM('PENDING', 'PROCESSING', 'CLOSED', 'ARCHIVED') NOT NULL DEFAULT 'PENDING',
    initiated_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    modified_at TIMESTAMP NOT NULL,
    CONSTRAINT market_open_before_close CHECK (market_open_time < market_close_time),
    CONSTRAINT mode_immutable GENERATED ALWAYS AS (mode) STORED,
    CONSTRAINT closed_at_immutability CHECK (closed_at IS NOT NULL OR batch_status != 'CLOSED')
);

-- BatchVerdict table
CREATE TABLE batch_verdicts (
    verdict_id UUID PRIMARY KEY NOT NULL,
    batch_id UUID NOT NULL REFERENCES batch_runs(batch_id),
    guardian_gate_results JSONB NOT NULL,
    compliance_passed BOOLEAN NOT NULL,
    tax_verified BOOLEAN NOT NULL,
    archive_verified BOOLEAN NOT NULL,
    batch_status ENUM('APPROVED', 'BLOCKED', 'NOT_PROVEN') NOT NULL,
    verdict_reasoning TEXT,
    authority_used ENUM('ZERO') NOT NULL DEFAULT 'ZERO',
    event_time TIMESTAMP NOT NULL,
    knowledge_time TIMESTAMP NOT NULL,
    policy_hash VARCHAR(64),
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT verdict_immutable PRIMARY KEY (verdict_id),
    CONSTRAINT authority_locked CHECK (authority_used = 'ZERO'),
    CONSTRAINT event_before_knowledge CHECK (event_time <= knowledge_time),
    CONSTRAINT guardian_gates_count CHECK (jsonb_array_length(guardian_gate_results) = 8),
    CONSTRAINT batch_status_logic CHECK (
        (batch_status = 'APPROVED' AND compliance_passed AND tax_verified AND archive_verified) OR
        (batch_status != 'APPROVED')
    )
);

-- DayReport table
CREATE TABLE day_reports (
    report_id UUID PRIMARY KEY NOT NULL,
    batch_id UUID NOT NULL REFERENCES batch_runs(batch_id),
    report_date DATE NOT NULL,
    trade_count INT NOT NULL DEFAULT 0 CHECK (trade_count >= 0),
    pnl_summary JSONB NOT NULL,
    risk_metrics JSONB NOT NULL,
    alert_count INT NOT NULL DEFAULT 0 CHECK (alert_count >= 0),
    alert_summary JSONB,
    export_time TIMESTAMP NOT NULL,
    report_status ENUM('DRAFT', 'FINALIZED', 'ARCHIVED') NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL,
    finalized_at TIMESTAMP,
    CONSTRAINT report_immutable_after_finalized TRIGGER (
        IF NEW.report_status = 'FINALIZED' AND OLD.report_status != 'FINALIZED'
        THEN SET finalized_at = NOW()
    )
);

-- ComplianceBundle table
CREATE TABLE compliance_bundles (
    bundle_id UUID PRIMARY KEY NOT NULL,
    batch_id UUID NOT NULL REFERENCES batch_runs(batch_id),
    tax_summary JSONB NOT NULL,
    receipt_hashes TEXT[] NOT NULL,
    audit_trail JSONB[] NOT NULL,
    certification_time TIMESTAMP NOT NULL,
    certifying_authority VARCHAR(255) NOT NULL,
    bundle_hash VARCHAR(64) NOT NULL,
    bundle_status ENUM('DRAFT', 'CERTIFIED', 'ARCHIVED') NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL,
    certified_at TIMESTAMP,
    CONSTRAINT bundle_immutable_after_certified TRIGGER (
        IF NEW.bundle_status = 'CERTIFIED' THEN THROW immutability_violation
    )
);

-- ArchiveRecord table (write-once, append-only)
CREATE TABLE archive_records (
    archive_record_id UUID PRIMARY KEY NOT NULL,
    batch_id UUID NOT NULL REFERENCES batch_runs(batch_id),
    report_id UUID REFERENCES day_reports(report_id),
    bundle_id UUID REFERENCES compliance_bundles(bundle_id),
    storage_path VARCHAR(1024) NOT NULL UNIQUE,
    storage_tier ENUM('HOT', 'WARM', 'COLD') NOT NULL DEFAULT 'WARM',
    retention_years INT NOT NULL DEFAULT 7 CHECK (retention_years >= 7),
    immutable_hash VARCHAR(64) NOT NULL,
    retrieval_metadata JSONB NOT NULL,
    hp_receipt JSONB,
    archive_status ENUM('WRITTEN', 'VERIFIED', 'RETRIEVED', 'PURGED') NOT NULL DEFAULT 'WRITTEN',
    created_at TIMESTAMP NOT NULL,
    verified_at TIMESTAMP,
    CONSTRAINT write_once PRIMARY KEY (archive_record_id),
    CONSTRAINT no_updates TRIGGER (IF UPDATE THEN THROW write_once_violation),
    CONSTRAINT no_deletes TRIGGER (IF DELETE THEN THROW write_once_violation)
);
```

---

## Workflow State Transitions

### BatchRun Lifecycle

```
PENDING
  │ (market_close_time reached)
  ↓
PROCESSING
  │ (export + summary + compliance complete)
  ↓
CLOSED
  │ (archive write verified + hp_receipt received)
  ↓
ARCHIVED
```

### BatchVerdict Lifecycle

```
Created (immutable upon creation)
  │ (verdict_id, batch_id, guardian_gate_results, compliance_passed, tax_verified, archive_verified set)
  ↓
Immutable (audit-only append, no updates)
  │
  └─→ Status = APPROVED (all conditions met)
  │   └─→ Batch proceeds to archive
  │
  └─→ Status = BLOCKED (any gate BLOCKED or verification failed)
  │   └─→ Batch halted, no archive
  │
  └─→ Status = NOT_PROVEN (any gate NOT_PROVEN)
      └─→ Batch waits for evidence resolution
```

### ComplianceBundle Lifecycle

```
DRAFT
  │ (tax_summary, receipt_hashes, audit_trail populated)
  ↓
CERTIFIED
  │ (certification_time set, bundle immutable)
  ↓
ARCHIVED
  │ (ready for long-term retention)
```

---

## Phase 2 Implementation Timeline

| Milestone | Dates | Owner | Status |
|-----------|-------|-------|--------|
| **M01 — Freeze** | Sep 8, 09–18 ET | Domain Architect | READY |
| **M02 — HP Infra** | Sep 8–11 ET | HP 24/7 | PARALLEL |
| **M03 — Guardian** | Sep 8–12 ET | Guardian Enforcement | PARALLEL |
| **M04 — NinjaTrader Batch** | Sep 8–14 ET | Batch Engine Team | STARTING |
| **M05 — Integration** | Sep 15–16 ET | All lanes | WAITING |
| **M06 — Cert** | Sep 17–18 ET | Architect + Guardian | WAITING |
| **M07 — Owner Review** | Sep 19 ET | Owner | WAITING |

---

## Onboarding Sequence (M04 Start)

**For NinjaTrader Batch Engine Developers:**

1. Read: NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md (Executive Summary → Authority Invariant)
2. Review: NINJATRADER_BATCH_DOMAIN_MODEL_FROZEN_V1.json (entities, tuples, relationships)
3. Study: This specification (data flow, constraint gates, integrations)
4. Understand: Guardian integration (8-gate verdict aggregation)
5. Understand: HP integration (durable storage + archive)
6. Implement: Batch lifecycle, verdict aggregation, archive writes
7. Verify: All 8 constraint gates enforced
8. Test: Authority=ZERO locked, data immutable after close

**For QA/Testers:**

1. Read: NINJATRADER_BATCH_DOMAIN_SPEC_FROZEN_V1.md (Verdict Types + Constraints)
2. Implement: Test cases for all 8 constraint gates
3. Implement: Guardian integration tests (all 8 gates PASS → APPROVED)
4. Implement: Compliance bundle certification tests
5. Implement: Archive write-once tests (HP integration)
6. Document: Pass/fail for each test case
7. Sign-Off: QA lead confirms all tests passed

---

## Risk Mitigation

### Critical Risks (Phase 2)

| Risk | Mitigation |
|------|-----------|
| R01: Guardian verdict incomplete | Batch verdict requires all 8 gates. Timeout to BLOCKED if missing. |
| R02: Batch executes without APPROVED | Authority=ZERO hardcoded. APPROVED requires ALL conditions. No bypass. |
| R03: Archive data corrupted | Write-once to HP durable storage. Immutable hash seals integrity. |
| R04: Batch data mutable after close | closed_at timestamp marks immutability. UPDATE triggers violation. |
| R05: Compliance data loss | ComplianceBundle certified and locked. Archived to HP with receipt. |

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

## Sign-Off

| Role | Responsibility | Status |
|------|---|---|
| **Domain Architect** | Froze domain model, verified Authority invariant | ✓ COMPLETE |
| **Guardian Lead** | Integration review (GateDecisionTuple aggregation) | TBD |
| **HP Lead** | Integration review (ArchiveRecord + durable storage) | TBD |
| **Batch Team Lead** | Implementation plan + development start | TBD |
| **Technical Reviewer** | Code adherence to frozen model | TBD |
| **QA Lead** | Test plan + verification checklist | TBD |

---

## Document Control

**Classification:** Technical Specification (Frozen)  
**Audience:** Batch Engine Team, Guardian Integration, HP Integration, QA, Architects  
**Distribution:** Internal (FlipFlop HQ project directory)  
**Change Authority:** Domain Architect (for corrections), Owner (for major changes)  
**Retention:** Permanent (audit trail)  

---

## Appendix: Quick Integration Checklist

**Before Batch Can Claim APPROVED Status:**

- [ ] All 8 Guardian gates received and verified
- [ ] ALL 8 guardian_gate_results = PASS
- [ ] compliance_passed = true (compliance checks passed)
- [ ] tax_verified = true (tax data accuracy verified)
- [ ] archive_verified = true (archive write confirmed)
- [ ] Authority=ZERO verified across all fields
- [ ] BatchVerdictTuple created with batch_status = APPROVED

**Before Batch Can Close:**

- [ ] DayReport finalized with all required fields
- [ ] AlertRecord array complete and timestamped
- [ ] ComplianceBundle certified with bundle_hash immutability seal
- [ ] ArchiveRecord written to HP durable storage
- [ ] HP receipt received and populated
- [ ] ArchiveRecord.archive_status = VERIFIED
- [ ] BatchRun.closed_at timestamp set

**Before Archive Completes:**

- [ ] All batch data locked (immutable after closed_at)
- [ ] TaxDataArchive created with retention_until date
- [ ] Retention lifecycle enforced (no purge before date)
- [ ] ArchiveRecord status = ARCHIVED
- [ ] All data read-only from UI (no further mutations)

---

**NinjaTrader Batch Domain Model: FROZEN AND LOCKED**

Authority Invariant: ZERO (immutable)  
Failure Policy: FAIL_CLOSED  
Integration: Guardian Enforcement + HP 24/7 Infrastructure  
Implementation Start: 2026-09-08  

**Status: READY FOR IMPLEMENTATION**
