# FLIPFLOP HQ STATE TABLE — COMMIT 85e7b44

**Date**: 2026-09-08  
**Root**: C:\FLIP_FLOP_HQ  
**Branch**: master  
**Authority**: ZERO (immutable)  
**Live Trading**: OFF  

---

## COMPONENT STATUS

| Component | Status | Details |
|-----------|--------|---------|
| **CORE ENGINE** | IMPLEMENTED | scheduler_service.py (24/7 loop, 60s tick), job_orchestrator, market_downloader, audit_engine, guardian_enforcement |
| **GUARDIAN** | IMPLEMENTED | 8 gates (1-3: FIXED; 4-7: TUNABLE; 8: Authority-ZERO locked). All passing. Thresholds documented in GUARDIAN_THRESHOLDS.md |
| **BACKEND API** | IMPLEMENTED | Flask port 8000. 10+ endpoints. Tier-based auth (control/external_read). /health, /metrics, /vault, /experiments, /queue, /arena, /guardian, /scripts/submit |
| **DASHBOARD UI** | IMPLEMENTED | React 19, 07_DASHBOARD/src. 8 sections: Overview, Trades, Performance, Calendar, Agents, Lab, Shadow, Guardian. HTTP polling + WebSocket-ready |
| **Database** | IMPLEMENTED | SQLite (audit trail, jobs, market data). Backup/restore daily, 30-day retention. Deterministic replay engine. |
| **Script Sandbox** | IMPLEMENTED | SafeScriptExecutor: AST validation, 512MB RAM, 300s timeout. Banned modules: os/sys/subprocess/socket/requests. Endpoint: /scripts/submit |
| **Deployment** | IMPLEMENTED | Windows Scheduled Task (auto-restart <30s). Linux systemd. Bootstrap scripts. Health checks every 5 minutes. |
| **Testing** | PASS 6/6 | Chaos tests all passing. 40+ integration tests passing. Scheduler restart verified. Audit chain verified. |
| **Setup Guides** | COMPLETE | ALPACA_SETUP_GUIDE.md, GUARDIAN_THRESHOLDS.md, strategy_loader.py (custom strategies), EXTERNAL_USERS_SETUP.md |
| **Documentation** | COMPLETE | 40+ markdown files. Production deployment, chaos tests, completion report. |

---

## OPEN GATES / NOT_PROVEN

| Item | Status | Reason |
|------|--------|--------|
| E: vs C: alignment | OPEN | Constitution says E:\FF_FAST\FF_HQ primary; current work on C:\FLIP_FLOP_HQ. Not critical but note discrepancy. |
| Real market connectivity | NOT_PROVEN | Alpaca guide exists; credentials not configured. System runs on synthetic data. |
| NinjaTrader bridge | HISTORICAL | NinjaTrader integration mentioned but not currently active. RR500/V03 strategy status needs assessment. |
| CONTROL/SHADOW runtime enforcement | DESIGNED_NOT_ENFORCED | Concept documented; not yet active in scheduler loop. |
| Bitemporal event store | PARTIAL | Audit trail exists; full event_time/knowledge_time separation incomplete. |
| Calibration ledger | NOT_IMPLEMENTED | Readiness/predictions logging (Brier-style) designed but not built. |
| Override ledger | NOT_IMPLEMENTED | Manual intervention tracking designed but not built. |
| Wound registry | NOT_IMPLEMENTED | Incident regression database not yet built. |
| Phone/Tablet responsive UI | NOT_IMPLEMENTED | Desktop works; mobile-first versions not started. |
| Admin Center | NOT_IMPLEMENTED | User/device/role management designed but not built. |
| Security Bunker | NOT_IMPLEMENTED | Zero-trust device registry not built. |
| SaaS auth/billing | NOT_IMPLEMENTED | OAuth/role-based architecture designed but not built. |

---

## NEXT HIGHEST VALUE QUEUE

1. **Canonical root alignment** — Decide E: vs C:; establish single source of truth
2. **Bitemporal event ledger** — event_time / knowledge_time separation; schema versioning
3. **Calibration + Override + Wound ledgers** — Permanent institutional memory for decisions and incidents
4. **Phone-first responsive redesign** — Mobile surfaces for Overview, Trades, Calendar, Agents
5. **SaaS auth foundation** — User roles (ROOT_OWNER, ADMIN, USER, VIEWER), device trust, MFA prep
6. **NinjaTrader integration** — If NQ/MNQ execution planned; currently NOT_PROVEN

---

## READY TO USE NOW

**Backend API + Dashboard**:
```bash
python 04_ENGINE/scheduler_service.py
# Runs 24/7 in Authority-ZERO mode
# All safety gates enforced
# External users readable via token
# Health checks every 5 min
```

System operational. Authority-ZERO locked. LIVE=OFF. All tests passing.

---

## RECENT COMMITS

- 85e7b44 Add complete setup guides (Alpaca, Guardian, strategy, external users)
- d24003b Complete autonomous system build: PRODUCTION READY
- 22121f2 Add tier-based access control
- 8f49654 Add scheduler_service.py: 24/7 autonomous loop
- 65b5518 Complete dashboard UI (8 sections)
- 39da94d Add backend API server (port 8000)
- ecf8c14 Chaos test execution: 6/6 passed

---

## NOTES FOR NEXT SESSION

**Constitution loaded**: All 52 points from FLIPFLOP HQ PRIMARY BUILDER TRANSFER document. Claude is primary builder. CJ is Root Owner. ChatGPT supports research/architecture.

**Style**: Caveman mode active (full). Drop articles, fluff, fragments OK. Direct language preferred. "bro operativo" tone fine.

**Stop points**: Only pause for owner-only PC action, credentials, irreversible changes, LIVE authority, broker mutations, real-money exposure, unverifiable evidence.

**Working style**: Don't ask "continue?" — pick next highest-value step and proceed.

---

**State snapshot captured. Ready for handoff to new session.**
