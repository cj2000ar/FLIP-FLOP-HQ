# FlipFlop HQ Phase 2 UI - Quick Start Guide

## 30-Second Setup

```bash
cd C:\FLIP_FLOP_HQ\07_DASHBOARD
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## What You'll See

- **TruthBar** (fixed top): Authority=ZERO, Live=OFF, data freshness, broker/control status
- **GuardianSeal**: 8 gates with PASS/BLOCKED/NOT_PROVEN verdicts, 8/8 status
- **HealthIndicator**: Machine heartbeat, clock offset, fencing token, restart flag
- **BatchSummary**: P&L ($12,500 net), 42 trades, 62% win rate, 1.8 Sharpe
- **AlertWidget**: 1 info alert (completion)
- **ArchiveViewer**: 1 archived cartridge (7-year retention)

## Key Features

- **3 Form Factors**: Mobile cockpit (375px), tablet workspace (768px), desktop command center (1440px+)
- **Truth-Age State Machine**: Green (fresh <10s) → Yellow (warning 10-30s) → Red (stale >30s)
- **Modal Overlay**: Blocks interaction when data is stale (>30 seconds old)
- **Read-Only**: No mutations, no authority grants, no verdict overrides
- **Authority Lock**: ZERO hard-coded throughout (no escalation possible)

## Testing

```bash
npm test              # Run all 40+ tests
npm test:ui          # Interactive test runner
npm run type-check   # TypeScript verification
```

## Type Safety

Full TypeScript strict mode with:
- No implicit any
- Strict null checks
- Immutable types
- Enum-like verdicts

## Accessibility

- WCAG 2.1 AA compliant
- 4.5:1 color contrast
- Keyboard navigation (Tab, Arrow, Enter)
- Screen reader support (ARIA labels)
- Reduced motion support

## Keyboard Shortcuts

- **Ctrl+Shift+A** - Toggle admin mode (development info)
- **Ctrl+R** - Refresh data (resets truth-age)

## Component Structure

```
ScreenComponent (responsive container)
├── TruthBar (fixed top, authority lock)
├── StaleWarning (modal overlay for >30s)
└── FormFactorLayout (phone/tablet/desktop)
    ├── GuardianSeal (8 gates)
    │   └── GateDetailView (per-gate details)
    ├── HealthIndicator (machine metrics)
    ├── BatchSummary (P&L, trades, alerts)
    ├── AlertWidget (ranked alerts)
    └── ArchiveViewer (immutable cartridges)
```

## Mock Data

App comes with realistic mock data:
- Guardian: All 8 gates PASS
- Machine: Healthy (5s heartbeat, 2ms clock, valid token)
- Batch: APPROVED with $12,500 net P&L
- Alerts: 1 completion info alert
- Archives: 1 cartridge with 7-year retention

Replace with real API calls in `App.tsx`:

```typescript
// Instead of mock data
const state = createMockGuardianState();

// Fetch from API
const response = await fetch('/api/guardian/state');
const state = await response.json();
```

## API Integration

**Subscribe to updates (recommended):**

```typescript
// Truth-age (refresh every 5s)
setInterval(() => {
  fetch('/api/truth-age')
    .then(r => r.json())
    .then(setTruthBar);
}, 5000);

// Stale check (every 2s)
setInterval(() => {
  if (truthBar.age_seconds > 30) {
    // Modal blocks interaction
  }
}, 2000);

// Guardian state
fetch('/api/guardian/state')
  .then(r => r.json())
  .then(setGuardianState);

// Machine health
fetch('/api/health')
  .then(r => r.json())
  .then(setHealthIndicator);

// Batch status
fetch('/api/batch/status')
  .then(r => r.json())
  .then(setBatchStatus);
```

## Build for Production

```bash
npm run build    # Creates dist/ directory
npm run preview  # Test production build locally
```

Deploy `dist/` directory to your web server.

## Dark Mode

Automatically respects system preference:
- Light: `@media (prefers-color-scheme: light)`
- Dark: `@media (prefers-color-scheme: dark)`

Or force via browser dev tools:
- Inspector > ⋮ > Rendering > Emulate CSS media feature prefers-color-scheme

## Authority Invariant Verification

**Hard-coded throughout (no way to change):**
- Authority: ZERO
- Live: OFF
- Broker Orders: NONE
- Control Mutations: NONE

**Verified by:**
- TypeScript types (immutable)
- Component rendering (always displays ZERO)
- Tests (40 test cases)

## Fail-Closed Constraints

1. **Stale Evidence (>300s):** Modal overlay blocks all interaction
2. **Missing Evidence:** Gates show NOT_PROVEN verdict
3. **Contradicted Evidence:** Gates show BLOCKED verdict
4. **Promotion:** Requires all 8 gates PASS + compliance + tax + archive

## Performance

- Lightweight: ~3KB gzipped (CSS + JS)
- Fast: Vite dev server with HMR
- Optimized: Tree-shaking in production build
- Accessible: No performance impact from a11y features

## Troubleshooting

**Port 5173 already in use?**
```bash
npm run dev -- --port 3000
```

**TypeScript errors?**
```bash
npm run type-check
```

**Tests failing?**
```bash
npm test -- --reporter=verbose
```

**Build errors?**
```bash
rm node_modules package-lock.json
npm install
npm run build
```

## Support

See `README.md` for complete documentation.

---

**Authority: ZERO | Live: OFF | Paper-Only | RED_DRAGON Ready**
