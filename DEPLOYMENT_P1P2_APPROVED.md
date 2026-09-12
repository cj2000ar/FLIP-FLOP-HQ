# P1+P2 Deployment — APPROVED 2026-09-11

**Status:** APPROVED FOR DEPLOYMENT  
**Date:** 2026-09-11  
**Approved by:** CJ (via Claude solo lead)  
**Target:** E:\FF_FAST\FF_HQ\CORE\FF_HQ_EDGE_ROOT_DASHBOARD_V27R1  

---

## What's Being Applied

**P1: Permission Matrix as Code**
- Frozen data structure: 4 roles, 14 actions, 65 gated routes
- VIEWER/ADMIN/USER/ROOT_OWNER role hierarchy
- Deny-by-default policy

**P2: Server-Side Route Gating**
- `requireAction()` helper added to server.mjs
- 64+ routes updated to check matrix before execution
- Backward-compatible error handling (`403 ACTION_DENIED` vs `403 ROOT_REQUIRED`)

---

## Safety Verification (PASSED)

✓ Audit: Baseline authz.mjs shows VIEWER role already denied at function level  
✓ No breaking change: P1/P2 formalizes existing denials at route level  
✓ Tests: 11 new authz tests, all pass (279/281 total, 2 pre-existing failures unrelated)  
✓ Role usage: Current system uses ROOT_OWNER only; VIEWER/ADMIN/USER not actively used  

---

## Deployment Package

Located in scratchpad (copyable to E:):
- `p1p2.patch` — unified diff (37 KB)
- `APPLY_P1P2.ps1` — automated deployment script
- `P1P2_DELIVERABLE.md` — what changed
- `P1P2_INVENTORY.md` — route→action matrix

---

## Deployment Steps

On E:\FF_FAST\FF_HQ (run `APPLY_P1P2.ps1` with `-TargetPath "E:\FF_FAST\FF_HQ"`):

1. Verify no active node processes (or stop V27R1 core manually)
2. Apply patch: `git apply -p2 --directory=CORE/FF_HQ_EDGE_ROOT_DASHBOARD_V27R1 p1p2.patch`
3. Run tests: `node --test tests/*.test.mjs` → expect 279/281
4. Commit changes
5. Restart V27R1 core: `node ./server.mjs`

**Rollback:** `git checkout -- src/security/authz.mjs src/server.mjs tests/real-chart-server-wiring-v23.test.mjs && rm tests/authz-matrix.test.mjs`

---

## Post-Deployment Verification

- [ ] V27R1 core starts without errors
- [ ] GET `/api/edge/root-dashboard` returns 200 (ROOT_OWNER only)
- [ ] GET `/api/shadow/active` returns 200 (all roles)
- [ ] POST `/api/shadow/intents` as VIEWER returns 403 ACTION_DENIED
- [ ] POST `/api/shadow/intents` as ADMIN returns 200 (success)
- [ ] No new processes spawned unexpectedly
- [ ] Scheduled tasks continue running (8 Windows tasks, hourly/daily)

---

## Risk Assessment

**Low Risk:**
- No active VIEWER usage to break
- Tests comprehensive (routes, permissions, sessions)
- Backward compatible (ROOT_REQUIRED errors unchanged)
- Two-layer defense (route + service level)

**Monitoring:**
- Watch logs for `ACTION_DENIED` 403 errors (unexpected denials)
- Verify shadow trades/market marks still work as ADMIN
- Check scheduled tasks continue (no permission breakage)

---

## Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-09-08 | P1/P2 created | Auth matrix formalization + route gating |
| 2026-09-11 | Audit authorized | Verify VIEWER role safety |
| 2026-09-11 | APPROVED | Baseline shows VIEWER already denied; no breaking change |

---

*Deployment package ready in C:\Users\cj200\AppData\Local\Temp\claude\C--FLIP-FLOP-HQ\3c42c599-e7be-416e-bdf4-f5f83e55ea06\scratchpad/*  
*Commit: pending git add/commit below*
