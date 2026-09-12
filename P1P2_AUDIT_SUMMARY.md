# P1+P2 Authorization Patch — Ready for Review

**Status:** Isolated, tested, ready for approval  
**Date:** 2026-09-08  
**Target:** `E:\FF_FAST\FF_HQ\CORE\FF_HQ_EDGE_ROOT_DASHBOARD_V27R1`  
**Test result:** 279/281 ✓ (2 failures pre-existing, unrelated to this change)

---

## What P1+P2 Does

**P1: Permission Matrix as Code**  
Frozen data structure defining which roles can perform which actions:
- 14 actions (e.g., `read.edge.rootDashboard`, `admin.security`, `write.shadow`)
- 4 roles: ROOT_OWNER, ADMIN, USER, VIEWER
- 65 gated routes (e.g., `/api/admin/users`, `/api/shadow/intents`, `/api/charts/realtime`)
- 14 routes pre-session or public (bootstrap, login, ingest, health checks)

**P2: Route-Level Gating**  
Server now checks matrix on every request:
- New `requireAction(req, res, action)` helper replaces bare `requireSession`
- 64+ route call sites updated to name their required action
- Deny by default: unknown action/role → `403 ACTION_DENIED`
- ROOT_REQUIRED errors unchanged for backward compatibility

---

## Changes (4 files, +291 / −70)

| File | Change |
|---|---|
| `src/security/authz.mjs` | +59 lines: ACTIONS array, PERMISSIONS per role, `can()`, `permissionMatrix()`. Frozen (immutable). |
| `src/server.mjs` | `requireAction()` helper added. 64 route sites updated. 2 inline ROOT_OWNER checks removed (now expressed in matrix). |
| `tests/authz-matrix.test.mjs` | **NEW** — 11 comprehensive tests: matrix structure, deny-by-default, role isolation, immutability, session binding, route coverage. All pass. |
| `tests/real-chart-server-wiring-v23.test.mjs` | 1 assertion: now checks matrix gate on `/api/charts/realtime` route itself. |

**Unchanged:** Authentication, credentials, scrypt, session signing, cookies, device binding, account scopes, database, evidence store, CSP, package.json.

---

## Permission Changes

| Role | Before | After |
|---|---|---|
| VIEWER | could write shadow trades, ack alerts, run preview | **denied all** (still has full read); `403 ACTION_DENIED` |
| USER | could post market marks, read platform config | **denied both**; read/preview unchanged |
| ADMIN | identical to USER | now has `read.platform.config`, `write.shadow.marketMark`, `admin.ops`; security/root still denied |
| ROOT_OWNER | — | unchanged |

---

## Test Results

### Before & After
| | Baseline | After Patch | Change |
|---|---|---|---|
| Total | 270 | 281 | +11 new tests |
| Pass | 268 | 279 | +11 |
| Fail | 2 | 2 | 0 (pre-existing) |

### 2 Failures (Pre-existing, Not Related to P1/P2)
1. `Root Boss is a real browser application surface` — expects string "Boss Console" not found in `web/root-boss.html`
2. `Boss dashboard is responsive desktop and phone` — expects `@media(max-width:860px)` not in CSS

Both failures existed before patch. Separate design/HTML decision required.

### 11 New Tests (authz-matrix.test.mjs) — All Pass
1. Matrix structure matches approved table exactly (56 assertions)
2. Deny by default (unknown action, unknown role, missing session)
3. VIEWER is strictly read-only (no product state writes)
4. USER has no admin, no market-mark; ADMIN has ops only, never security
5. Only ROOT_OWNER holds security admin + root dashboard
6. No action can mutate LIVE/broker/CONTROL/routing/order authority; matrix immutable
7. Permissions on real `AuthService` sessions (temp DB + live authenticate)
8. Server routes: `requireSession` only inside `requireAction`
9. Server routes: each gated route names a known action (≥60 sites)
10. Inventory pins route→action for 15 sensitive routes
11. No inline `ROOT_OWNER` checks remain on matrix-covered routes

---

## Deliverables in Scratchpad

- `p1p2.patch` — unified diff (37 KB, 4 files, 24 hunks)
- `inventory.md` — route→action→role table (auto-generated, not hand-typed)
- `apply_p2.py` / `apply_p2_tests.py` — exact transforms with assertions
- `baseline_test_output.txt` / `work_test_output.txt` — before/after full test output

---

## To Apply (After CJ Approval)

1. Stop V27R1 core if running (`29 node.exe` processes noted Sep 7–8; which serve V27R1 NOT_PROVEN)
2. `git apply p1p2.patch` from V27R1 directory (or `git apply -p2 --directory=CORE/FF_HQ_EDGE_ROOT_DASHBOARD_V27R1` from E: repo root)
3. `node --test tests/*.test.mjs` → expect 281 / 279 / 2
4. Restart core

**Rollback:** `git checkout -- src/security/authz.mjs src/server.mjs tests/real-chart-server-wiring-v23.test.mjs && rm tests/authz-matrix.test.mjs`

---

## Security Properties

✓ No LIVE/broker/CONTROL/routing authority can be granted via this matrix  
✓ Frozen arrays prevent runtime mutation  
✓ Deny by default (unknown actions/roles rejected)  
✓ Service-level checks (AuthService, AccountService) still run after route gate (defense in depth)  
✓ Root-only actions keep `ROOT_REQUIRED` error (backward compatible)  
✓ Every other denial returns `ACTION_DENIED` with role info

---

## Decision Points

**Open:** Two pre-existing test failures (Boss Console HTML/CSS). Separate from P1/P2.  
- Delete tests?  
- Leave as drift?  
- Fix HTML/CSS?  
→ Decision: CJ only

**Ready to apply?** Yes, after CJ approval. No blockers.

---

*Generated 2026-09-11. Patch ready in scratchpad at `v27r1_p1p2/`.*
