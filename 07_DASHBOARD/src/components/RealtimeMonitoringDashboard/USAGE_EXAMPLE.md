# Real-time Monitoring Dashboard - Usage Examples

## Installation

```bash
npm install react react-dom typescript @testing-library/react @testing-library/jest-dom
```

## Basic Usage

### 1. Render Dashboard in App

```tsx
import React from 'react';
import { RealtimeMonitoringDashboard } from './components/RealtimeMonitoringDashboard';

export function App() {
  return (
    <RealtimeMonitoringDashboard
      apiBaseUrl={process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'}
      wsUrl={process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}
      machineId={process.env.REACT_APP_MACHINE_ID || 'machine-001'}
      fencingToken={process.env.REACT_APP_FENCING_TOKEN || 'token-123'}
      onAuthError={(error) => {
        console.error('Dashboard auth error:', error);
        // Could trigger alert or redirect
      }}
    />
  );
}
```

### 2. Environment Variables (.env)

```
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_MACHINE_ID=machine-001
REACT_APP_FENCING_TOKEN=token-123
```

## Advanced Usage

### 1. Custom Metrics Hook

```tsx
import { useMetricsState, calculateTradeMetrics } from './metrics_updater';

function MyCustomMetricsDisplay() {
  const {
    state,
    updateStrategy,
    addTrade,
    updateSystemHealth,
  } = useMetricsState();

  // Add a new trade
  const handleNewTrade = (trade) => {
    addTrade(trade);
    const metrics = calculateTradeMetrics(state.trades);
    console.log('Win Rate:', metrics.winRate);
  };

  return (
    <div>
      <h2>Win Rate: {calculateTradeMetrics(state.trades).winRate}%</h2>
      <button onClick={() => handleNewTrade(newTrade)}>
        Add Trade
      </button>
    </div>
  );
}
```

### 2. WebSocket Client Standalone

```tsx
import { WebSocketClient } from './websocket_client';

async function setupWebSocket() {
  const client = new WebSocketClient({
    url: 'ws://localhost:8000',
    machineId: 'machine-001',
    fencingToken: 'token-123',
    reconnectAttempts: 5,
    reconnectDelayMs: 1000,
    onUpdate: (update) => {
      console.log('Received update:', update);
      if (update.type === 'batch') {
        handleBatchUpdate(update.data);
      }
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    },
    onStatusChange: (status) => {
      console.log('Connection status:', status);
    },
  });

  await client.connect();
  client.subscribe('metrics');

  // Use client...
  client.send({ type: 'custom', data: {} });

  // Cleanup
  // client.disconnect();
}
```

### 3. API Fetching with Polling

```tsx
import { useMetricsFetch, useMetricsPolling } from './metrics_updater';

function MetricsPoller() {
  const fetchMetrics = useMetricsFetch(
    'http://localhost:8000',
    'machine-001',
    'token-123'
  );

  useMetricsPolling(
    fetchMetrics,
    (data) => {
      console.log('New metrics:', data);
      // Update your state here
    },
    1000 // Poll every 1 second
  );

  return <div>Polling for metrics...</div>;
}
```

### 4. Trade Metrics Calculation

```tsx
import { calculateTradeMetrics, TradeRecord } from './metrics_updater';

const trades: TradeRecord[] = [
  {
    id: '1',
    strategyId: 's1',
    entryTime: 1609459200000,
    exitTime: 1609459260000,
    entryPrice: 100.00,
    exitPrice: 105.00,
    quantity: 10,
    pnl: 500,
    latencyMs: 45,
    type: 'LONG',
  },
  {
    id: '2',
    strategyId: 's1',
    entryTime: 1609459320000,
    entryPrice: 105.00,
    quantity: 10,
    pnl: -100,
    latencyMs: 52,
    type: 'SHORT',
  },
];

const metrics = calculateTradeMetrics(trades);
console.log('Metrics:', metrics);
// Output:
// {
//   winRate: 50,
//   profitFactor: 5,
//   maxDrawdown: 100,
//   avgLatency: 48.5
// }
```

## Integration with Existing Dashboard

### 1. As a Tab in Larger Dashboard

```tsx
import { useState } from 'react';
import { RealtimeMonitoringDashboard } from './components/RealtimeMonitoringDashboard';

function MasterDashboard() {
  const [activeTab, setActiveTab] = useState('monitoring');

  return (
    <div>
      <nav>
        <button onClick={() => setActiveTab('monitoring')}>Monitoring</button>
        <button onClick={() => setActiveTab('settings')}>Settings</button>
      </nav>

      {activeTab === 'monitoring' && (
        <RealtimeMonitoringDashboard
          apiBaseUrl="http://localhost:8000"
          wsUrl="ws://localhost:8000"
          machineId="machine-001"
          fencingToken="token-123"
        />
      )}

      {activeTab === 'settings' && <SettingsPanel />}
    </div>
  );
}
```

### 2. With Custom Error Boundary

```tsx
import React, { ErrorInfo } from 'react';
import { RealtimeMonitoringDashboard } from './components/RealtimeMonitoringDashboard';

class DashboardErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Dashboard error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-state">
          <h2>Dashboard Error</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false })}>
            Retry
          </button>
        </div>
      );
    }

    return (
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
        onAuthError={(error) => {
          this.setState({ hasError: true, error: new Error(error) });
        }}
      />
    );
  }
}
```

## Testing

### 1. Unit Tests

```bash
npm test websocket_client.test.ts
npm test metrics_updater.test.ts
npm test dashboard_component.test.tsx
```

### 2. Integration Tests

```bash
npm test integration.test.tsx
```

### 3. Coverage Report

```bash
npm test -- --coverage

# Output coverage metrics for:
# - Lines: 70%+
# - Branches: 70%+
# - Functions: 70%+
# - Statements: 70%+
```

### 4. Custom Test Case

```tsx
import { render, screen } from '@testing-library/react';
import { RealtimeMonitoringDashboard } from './dashboard_component';

test('displays Authority-ZERO status', async () => {
  render(
    <RealtimeMonitoringDashboard
      apiBaseUrl="http://localhost:8000"
      wsUrl="ws://localhost:8000"
      machineId="machine-001"
      fencingToken="token-123"
    />
  );

  expect(screen.getByText('AUTHORITY: ZERO')).toBeInTheDocument();
  expect(screen.getByText('LIVE: OFF')).toBeInTheDocument();
});
```

## Performance Optimization

### 1. Lazy Loading

```tsx
import { lazy, Suspense } from 'react';

const Dashboard = lazy(
  () => import('./components/RealtimeMonitoringDashboard')
);

function App() {
  return (
    <Suspense fallback={<div>Loading Dashboard...</div>}>
      <Dashboard {...props} />
    </Suspense>
  );
}
```

### 2. Memoization

```tsx
import { memo } from 'react';

const MemoizedDashboard = memo(RealtimeMonitoringDashboard);

// Props won't cause re-render if they don't change
<MemoizedDashboard {...props} />
```

### 3. Reduce Polling Frequency

```tsx
// Poll every 5 seconds instead of 1 second
useMetricsPolling(fetchMetrics, onUpdate, 5000);
```

## Troubleshooting

### WebSocket Connection Issues

```tsx
onAuthError={(error) => {
  if (error.includes('401')) {
    // Machine-ID or token invalid
    refreshFencingToken();
  } else if (error.includes('403')) {
    // Token expired
    reacquireToken();
  }
}}
```

### Data Staleness

Monitor `truth_age_seconds` from API responses:

```tsx
const freshness = response.truth_age_seconds;
if (freshness > 30) {
  console.warn('Data is stale, consider refreshing');
}
```

### Performance Degradation

- Reduce polling frequency
- Limit trade history (currently 50 trades)
- Use WebSocket instead of HTTP polling
- Enable browser DevTools Performance tab

## Production Deployment

### 1. Environment Configuration

```env
# Production
REACT_APP_API_BASE_URL=https://api.flipflop-hq.com
REACT_APP_WS_URL=wss://api.flipflop-hq.com
REACT_APP_MACHINE_ID=prod-machine-001
REACT_APP_FENCING_TOKEN=<secured-token>
```

### 2. Build Optimization

```bash
npm run build

# Output: build/
# - Main bundle size: ~45KB (gzipped)
# - CSS bundle: ~8KB (gzipped)
# - No external dependencies needed
```

### 3. Security Headers

```
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
```

## API Contract

Ensure your backend implements these endpoints:

### Batch Summary
```
GET /batch/{batch_id}
Headers: Machine-ID, Fencing-Token
Response:
{
  "batch_id": "batch-001",
  "verdict_status": "APPROVED",
  "alert_array": [...],
  "pnl_summary": {
    "gross_pnl": 15000,
    "net_pnl": 12500,
    "currency": "USD"
  },
  "risk_metrics": {
    "max_drawdown_pct": 2.5,
    "sharpe_ratio": 1.8,
    "win_rate_pct": 62
  }
}
```

### Guardian Gates
```
GET /gates
Headers: Machine-ID, Fencing-Token
Response:
[
  {
    "gate_id": 1,
    "gate_name": "SCHEMA_AND_IDENTITY",
    "verdict": "PASS",
    "evidence_id": "evidence-1",
    "event_time": 1609459200,
    "knowledge_time": 1609459210,
    "truth_age_seconds": 5
  },
  ...
]
```

### System Heartbeat
```
GET /heartbeat/{machine_id}/freshness
Headers: Machine-ID, Fencing-Token
Response:
{
  "age_seconds": 5,
  "is_fresh": true,
  "warning_level": "fresh",
  "last_update": 1609459210
}
```

## Support

For issues or questions:
1. Check README.md for component documentation
2. Review test files for usage examples
3. Check console for error messages
4. Verify API responses match expected schema
