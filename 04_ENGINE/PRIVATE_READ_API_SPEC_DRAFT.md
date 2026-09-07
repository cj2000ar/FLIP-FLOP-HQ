# Private Read API Spec — Lab & Dashboard

## Overview

Read-only API (port 8000, same host as Guardian/HP) for dashboard UI state. Bitemporal queries: each response carries `event_time` (when thing happened) + `knowledge_time` (when HQ learned it). No mutations, no orders, no LIVE authority.

**Auth:** `Machine-ID` + `Fencing-Token` headers. Token from `/acquire_fencing_token`, verified via `/validate_fencing_token` on HP infra.

**Version:** Draft v0.1 (schema subject to change).

---

## Endpoint Mapping

### Overview Tab

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| TruthBar.heartbeat | `/heartbeat/{machine_id}/freshness` | `{age_seconds, is_fresh, warning_level, stale_since, last_update}` | age < 10s = fresh, 10-30s = warning, > 30s = stale |
| TruthBar.authority | `/health` | `{authority: "ZERO", live: false, broker_orders: "NONE"}` | Frozen, immutable |
| Guardian.8gates | `/gates` | `[{gate_id, verdict, evidence_id, event_time, knowledge_time, truth_age_seconds}]` | event_time ≤ knowledge_time |
| Batch.summary | `/batch/{batch_id}` | `{batch_id, verdict_status, alert_array, pnl_summary, risk_metrics}` | Immutable after close |

### Lab.Vault

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| VaultItems | `/vault/items?family={fam}` | `[{id, kind, title, source, extraction, evidence, family, dna, data_needs}]` | Filter by family tag |
| StrategyFamilies | `/vault/families` | `[{id, name, lineage, dna}]` | Frozen 5 families |

### Lab.Arena

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| StrategyCards | `/arena/strategies` | `[{id, name, state, version, metrics, summary, note}]` | CONTROL immutable; shadow/rejected deletable? No. |

### Lab.ExperimentLedger

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| Experiments | `/experiments` | `[{id, name, hypothesis, parameters, dataset_role, runs, status, result, rejection_reason, next_gate, created_at, completed_at}]` | PRE_REGISTERED A–G, FAILED holdouts, no edits |

### Lab.Queue

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| QueueByState | `/queue?state={state}` | `[{id, title, state, why}]` | 10 states, PROMOTION_REVIEW empty |

### Lab.Agenda

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| EventSlots | `/agenda/events` | `[{code, name, importance, datetime, actual, forecast, previous, nq_response, signals_emitted, control_result}]` | NOT_CONNECTED until feed live |

### Lab.Guardian

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| Cartridge.history | `/cartridge?start_date={iso}, end_date={iso}` | `[{correlation_id, bars, signal_state, clock, verdict, config, version, session, event_time, knowledge_time}]` | Immutable, upcasted schema |
| Wounds | `/guardian/wounds` | `[{id, title, detail, status, tone}]` | Permanent registry |
| Override.ledger | `/guardian/overrides` | `[{id, who, reason, before_state, after_state, outcome, timestamp}]` | Empty until manual intervention |

### Lab.Promotion

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| Gates.checklist | `/promotion/gates?candidate={id}` | `[{id, name, requirement, status, evidence}]` | 16 gates per candidate |
| Gates.verdict | `/promotion/verdict?candidate={id}` | `{pass_count, blocking_gates, final_verdict}` | BLOCKED if NOT_PROVEN gate exist |

### Lab.Quantum

| UI component | GET endpoint | schema | notes |
|---|---|---|---|
| Lanes | `/quantum/lanes` | `[{id, name, definition, status, tone}]` | Real / Sim / Inspired / Classical |

---

## Bitemporal Query Model

Every response carries two timestamps:
- `event_time` (number, Unix seconds): when trade/gate/event happened in market time
- `knowledge_time` (ISO 8601): when HQ recorded/confirmed it

Rule: `event_time ≤ knowledge_time` enforced server-side. Late data = both timestamps recorded, past never rewritten.

UI: `truth_age_seconds = now - knowledge_time`. Stale detection runs client-side.

---

## Error Codes

| code | meaning | recovery |
|---|---|---|
| 200 | OK | use data |
| 401 | Machine-ID or Fencing-Token invalid | refresh token, retry |
| 403 | Fencing-Token expired | re-acquire token |
| 404 | batch_id / cartridge_id not found | verify ID |
| 500 | DB error | retry, escalate if persist |

---

## Implementation Gaps

**Must add:**
1. Experiment Ledger: `/experiments` — query materialized `experiments` table (if not live-queried from schema)
2. Queue: `/queue` — query `queue_items` state machine table
3. Calibration: `/guardian/calibration` — query `calibration_ledger` (predictions + scores)
4. Vault: `/vault/items`, `/vault/families` — new queries, data from `labData.ts` (hardcoded for now)

**Optional:** `/news/agenda` wired to live feed (currently `NOT_CONNECTED`).

**Schema versioning:** Each endpoint response includes `schema_version` (int). Upcaster on client if schema change.

---

## Next Steps

1. Add missing endpoints to `guardian_api.py` or new `private_read_api.py`
2. Wire dashboard Lab components to endpoints (replace hardcoded labData with fetch)
3. Test bitemporal query: inject late data, verify both timestamps recorded
4. Implement Fencing-Token validation in request middleware
