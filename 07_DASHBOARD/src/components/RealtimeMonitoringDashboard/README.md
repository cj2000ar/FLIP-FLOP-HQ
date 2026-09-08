# Real-time Monitoring Dashboard

Complete 24/7 autonomous lab monitoring system with live metrics, WebSocket updates, and Guardian-approved read-only interface.

## Components

### 1. `dashboard_component.tsx` (285 lines)
Main React component displaying real-time metrics for autonomous trading lab.

**Features:**
- Authority-ZERO locked display
- Live strategy status (running/idle/error)
- P&L chart and summary metrics
- Win rate, profit factor, max drawdown
- Latest 50 trades (entry/exit, P&L, latency)
- System health: CPU, memory, DB size, uptime
- Trade filtering by date range and strategy
- CSV export functionality
- Read-only Guardian-approved interface
- Responsive design (mobile/tablet/desktop)

**Props:**
```typescript
interface DashboardProps {
  apiBaseUrl: string;        // Backend API base URL
  wsUrl: string;             // WebSocket server URL
  machineId: string;         // Machine identifier
  fencingToken: string;      // Fencing token for auth
  onAuthError?: (error: string) => void;  // Error callback
}
```

**Usage:**
```tsx
<RealtimeMonitoringDashboard
  apiBaseUrl="http://localhost:8000"
  wsUrl="ws://localhost:8000"
  machineId="machine-001"
  fencingToken="token-123"
  onAuthError={(error) => console.error(error)}
/>
```

### 2. `websocket_client.ts` (168 lines)
WebSocket client with auto-reconnect, bitemporal data handling, and machine_id+fencing_token auth.

**Features:**
- Auto-reconnect with exponential backoff
- Message queuing while disconnected
- Heartbeat keep-alive
- Channel subscription/unsubscription
- Graceful disconnect
- Error handling and status callbacks

**Class:**
```typescript
class WebSocketClient {
  connect(): Promise<void>
  send(data: Record<string, unknown>): void
  subscribe(channel: string): void
  unsubscribe(channel: string): void
  disconnect(): void
  isConnected(): boolean
}
```

**Usage:**
```typescript
const client = new WebSocketClient({
  url: 'ws://localhost:8000',
  machineId: 'machine-001',
  fencingToken: 'token-123',
  reconnectAttempts: 5,
  reconnectDelayMs: 1000,
  onUpdate: (update) => console.log(update),
  onError: (error) => console.error(error),
  onStatusChange: (status) => console.log(status),
});

await client.connect();
client.subscribe('metrics');
```

### 3. `metrics_updater.ts` (229 lines)
State management for real-time metrics with React hooks.

**Features:**
- Metrics state reducer (strategies, trades, health, P&L)
- `useMetricsState()` hook for state management
- `useMetricsFetch()` hook for API calls
- `useMetricsPolling()` hook for periodic updates
- `calculateTradeMetrics()` utility (win rate, profit factor, max drawdown, latency)
- Immutable update patterns

**Hooks:**
```typescript
// State management
const {
  state,
  updateStrategy,
  addTrade,
  updateTrades,
  updateSystemHealth,
  updatePnlHistory,
  reset,
} = useMetricsState();

// API fetching
const fetchMetrics = useMetricsFetch(apiBaseUrl, machineId, fencingToken);

// Polling
useMetricsPolling(fetchMetrics, onUpdate, 1000);
```

### 4. `dashboard.css` (293 lines)
Comprehensive styles with theme support, responsive design, and dark mode.

**Features:**
- CSS variables for theming
- Dark mode support
- Responsive grid layout
- Smooth animations and transitions
- Mobile-first design
- Accessibility features

## Data Types

### StrategyMetrics
```typescript
interface StrategyMetrics {
  id: string;
  name: string;
  version: string;
  state: 'running' | 'idle' | 'error' | 'completed';
  startTime: number;
  trades: TradeRecord[];
  pnlCurrent: number;
  pnlMax: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
}
```

### TradeRecord
```typescript
interface TradeRecord {
  id: string;
  strategyId: string;
  entryTime: number;
  exitTime?: number;
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  pnl: number;
  latencyMs: number;
  type: 'LONG' | 'SHORT' | 'HEDGE';
}
```

### SystemHealth
```typescript
interface SystemHealth {
  cpuPercent: number;
  memoryPercent: number;
  dbSizeBytes: number;
  lastEodDownload: number;
  uptime: number;
  isHealthy: boolean;
}
```

## API Integration

Dashboard expects API endpoints (from PRIVATE_READ_API_SPEC_DRAFT.md):

```
GET /batch/{batch_id}           - Batch summary (P&L, alerts)
GET /gates                      - Guardian gate verdicts
GET /heartbeat/{machine_id}/freshness - System health/freshness
```

**Auth Headers:**
```
Machine-ID: {machineId}
Fencing-Token: {fencingToken}
```

## WebSocket Messages

Subscribe to `metrics` channel for live updates:

```typescript
// Updates received:
{
  type: 'heartbeat',
  timestamp: 1234567890,
  data: { uptime: 3600 }
}

{
  type: 'batch',
  timestamp: 1234567890,
  data: {
    trades: [...],
    pnl_history: [{ timestamp, value }, ...]
  }
}

{
  type: 'health',
  timestamp: 1234567890,
  data: {
    cpuPercent: 45,
    memoryPercent: 60,
    dbSizeBytes: 1048576
  }
}
```

## Authority and Security

**Authority Display:**
- `AUTHORITY: ZERO` (locked, immutable)
- `LIVE: OFF` (paper-only, no real orders)
- Read-only interface (no trade execution)
- Guardian-approved buttons only
- Disabled simulator controls

**Fencing Token:**
- Validated on every API call
- Auto-acquired via `/acquire_fencing_token`
- Expires after usage (refresh required)

## Testing

Unit tests included (Jest + React Testing Library):

```bash
npm test

# Run specific test file
npm test websocket_client.test.ts
npm test metrics_updater.test.ts
npm test dashboard_component.test.tsx
```

### Test Coverage
- **websocket_client.test.ts**: Connection, reconnect, subscribe/unsubscribe, auth
- **metrics_updater.test.ts**: Trade metrics calculation, state updates
- **dashboard_component.test.tsx**: Rendering, user interactions, data display

## Responsive Design

- **Desktop (>1024px)**: 3-column grid, full table
- **Tablet (768-1024px)**: 2-column grid, condensed table
- **Mobile (<768px)**: 1-column grid, card-based trade display

## Performance

- Updates every 1 second (configurable)
- Last 50 trades in memory
- Last 100 P&L points in history
- Auto-reconnect with exponential backoff
- Message queue for offline periods
- Minimal re-renders (React hooks)

## Files Structure

```
RealtimeMonitoringDashboard/
├── dashboard_component.tsx      (285 lines)
├── websocket_client.ts          (168 lines)
├── metrics_updater.ts           (229 lines)
├── dashboard.css                (293 lines)
├── dashboard_component.test.tsx (170 lines)
├── metrics_updater.test.ts      (160 lines)
├── websocket_client.test.ts     (90 lines)
└── README.md                    (this file)
```

## Configuration

Environment variables:
```
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_MACHINE_ID=machine-001
REACT_APP_FENCING_TOKEN=token-123
```

## Error Handling

- Connection errors logged to console
- Graceful fallback to last known state
- Retry mechanism for failed API calls
- User-friendly error messages
- No data loss on disconnect

## Future Enhancements

- P&L chart with canvas/d3.js
- Trade detail modal
- Strategy performance comparison
- Alert notifications (push)
- Export to other formats (JSON, Excel)
- Real-time strategy parameters view
- Historical backtesting results
