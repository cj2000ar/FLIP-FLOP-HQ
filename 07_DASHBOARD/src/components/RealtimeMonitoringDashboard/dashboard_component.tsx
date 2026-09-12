/**
 * Real-time Monitoring Dashboard for 24/7 Autonomous Lab
 * Authority-ZERO locked, live_enabled=false (read-only, paper-only)
 */

import React, { useEffect, useState } from 'react';
import {
  useMetricsState,
  useMetricsFetch,
  useMetricsPolling,
  calculateTradeMetrics,
  TradeRecord,
  SystemHealth,
} from './metrics_updater';
import { WebSocketClient, MetricsUpdate } from './websocket_client';
import './dashboard.css';

export interface DashboardProps {
  apiBaseUrl: string;
  wsUrl: string;
  machineId: string;
  fencingToken: string;
  onAuthError?: (error: string) => void;
}

export const RealtimeMonitoringDashboard: React.FC<DashboardProps> = ({
  apiBaseUrl,
  wsUrl,
  machineId,
  fencingToken,
  onAuthError,
}) => {
  const { state, updateTrades, updateSystemHealth, updatePnlHistory } =
    useMetricsState();

  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'reconnecting'>(
    'disconnected'
  );
  const [dateRange, setDateRange] = useState<{ start: Date; end: Date }>({
    start: new Date(Date.now() - 24 * 60 * 60 * 1000),
    end: new Date(),
  });
  const [filterStrategy, setFilterStrategy] = useState<string>('all');

  // Fetch metrics from API
  const fetchMetrics = useMetricsFetch(apiBaseUrl, machineId, fencingToken);

  // WebSocket connection for live updates
  useEffect(() => {
    const wsClient = new WebSocketClient({
      url: wsUrl,
      machineId,
      fencingToken,
      reconnectAttempts: 5,
      reconnectDelayMs: 1000,
      onUpdate: handleWebSocketUpdate,
      onError: (error) => onAuthError?.(error),
      onStatusChange: setConnectionStatus,
    });

    wsClient.connect().catch((error) => {
      onAuthError?.(`WebSocket connection failed: ${error}`);
    });

    wsClient.subscribe('metrics');

    return () => {
      wsClient.unsubscribe('metrics');
      wsClient.disconnect();
    };
  }, [machineId, fencingToken, wsUrl]);

  // Poll metrics every second
  useMetricsPolling(
    fetchMetrics,
    (_data: unknown) => {
      // Update state from API response
    },
    1000
  );

  const handleWebSocketUpdate = (update: MetricsUpdate) => {
    switch (update.type) {
      case 'heartbeat':
        updateSystemHealth({
          uptime: update.data?.uptime as number,
          isHealthy: true,
        });
        break;
      case 'batch':
        if (update.data?.trades) {
          updateTrades(update.data.trades as TradeRecord[]);
        }
        if (update.data?.pnl_history) {
          updatePnlHistory(update.data.pnl_history as { timestamp: number; value: number }[]);
        }
        break;
      case 'health':
        updateSystemHealth(update.data as Partial<SystemHealth>);
        break;
    }
  };

  const handleDownloadCSV = () => {
    const csv = generateTradesCsv(state.trades);
    downloadFile(csv, `trades_${Date.now()}.csv`, 'text/csv');
  };

  const filteredTrades = state.trades.filter((trade) => {
    const inRange =
      trade.entryTime >= dateRange.start.getTime() &&
      trade.entryTime <= dateRange.end.getTime();
    const matchesStrategy = filterStrategy === 'all' || state.strategies.some((s) => s.id === filterStrategy);
    return inRange && matchesStrategy;
  });

  const metrics = calculateTradeMetrics(filteredTrades);

  return (
    <div className="dashboard-container">
      {/* Authority Display */}
      <div className="authority-banner">
        <div className="authority-status">
          <span className="status-badge locked">AUTHORITY: ZERO</span>
          <span className="status-badge readonly">LIVE: OFF</span>
          <span className={`status-badge ${connectionStatus}`}>
            {connectionStatus.toUpperCase()}
          </span>
        </div>
        <p className="authority-message">
          Evidence-scoped review mode (no live trading, read-only interface)
        </p>
      </div>

      {/* Header with Controls */}
      <div className="dashboard-header">
        <h1>Autonomous Lab Monitoring Dashboard</h1>
        <div className="header-controls">
          <button disabled className="btn btn-disabled" title="Guardian-approved only">
            Start Simulator
          </button>
          <button disabled className="btn btn-disabled" title="Guardian-approved only">
            Stop Simulator
          </button>
          <button onClick={handleDownloadCSV} className="btn btn-primary">
            Download CSV
          </button>
        </div>
      </div>

      {/* Metrics Display Grid */}
      <div className="metrics-grid">
        {/* Strategies Running */}
        <div className="metric-card">
          <h3>Strategies Running</h3>
          <div className="strategies-list">
            {state.strategies.length === 0 ? (
              <p className="empty-state">No strategies currently running</p>
            ) : (
              state.strategies.map((strategy) => (
                <div key={strategy.id} className="strategy-item">
                  <div className="strategy-header">
                    <span className="strategy-name">{strategy.name}</span>
                    <span className={`state-badge ${strategy.state}`}>{strategy.state}</span>
                  </div>
                  <div className="strategy-details">
                    <span>v{strategy.version}</span>
                    <span>{formatUptime(Date.now() - strategy.startTime)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* P&L Summary */}
        <div className="metric-card">
          <h3>P&L Summary</h3>
          <div className="pnl-display">
            <div className="pnl-value">${state.trades.reduce((sum, t) => sum + t.pnl, 0).toFixed(2)}</div>
            <div className="pnl-metrics">
              <div>Win Rate: {metrics.winRate.toFixed(1)}%</div>
              <div>Profit Factor: {metrics.profitFactor.toFixed(2)}</div>
              <div>Max Drawdown: ${metrics.maxDrawdown.toFixed(2)}</div>
            </div>
          </div>
        </div>

        {/* System Health */}
        <div className="metric-card">
          <h3>System Health</h3>
          <div className="health-metrics">
            <div className="health-item">
              <span>CPU</span>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${state.systemHealth.cpuPercent}%` }}
                />
              </div>
              <span className="value">{state.systemHealth.cpuPercent.toFixed(1)}%</span>
            </div>
            <div className="health-item">
              <span>Memory</span>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${state.systemHealth.memoryPercent}%` }}
                />
              </div>
              <span className="value">{state.systemHealth.memoryPercent.toFixed(1)}%</span>
            </div>
            <div className="health-item">
              <span>DB Size</span>
              <span className="value">{formatBytes(state.systemHealth.dbSizeBytes)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Trade Ledger */}
      <div className="trade-ledger">
        <div className="ledger-header">
          <h2>Latest Trades (Last 50)</h2>
          <div className="filters">
            <input
              type="date"
              value={dateRange.start.toISOString().split('T')[0]}
              onChange={(e) =>
                setDateRange((prev) => ({
                  ...prev,
                  start: new Date(e.target.value),
                }))
              }
              className="filter-input"
            />
            <input
              type="date"
              value={dateRange.end.toISOString().split('T')[0]}
              onChange={(e) =>
                setDateRange((prev) => ({
                  ...prev,
                  end: new Date(e.target.value),
                }))
              }
              className="filter-input"
            />
            <select
              value={filterStrategy}
              onChange={(e) => setFilterStrategy(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Strategies</option>
              {state.strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="trade-table">
          <div className="table-header">
            <div>Entry Time</div>
            <div>Exit Time</div>
            <div>Entry Price</div>
            <div>Exit Price</div>
            <div>Qty</div>
            <div>P&L</div>
            <div>Latency (ms)</div>
          </div>
          <div className="table-body">
            {filteredTrades.length === 0 ? (
              <div className="empty-state">No trades in selected range</div>
            ) : (
              filteredTrades.map((trade) => (
                <div key={trade.id} className="table-row">
                  <div>{formatTimestamp(trade.entryTime)}</div>
                  <div>{trade.exitTime ? formatTimestamp(trade.exitTime) : '-'}</div>
                  <div>${trade.entryPrice.toFixed(2)}</div>
                  <div>{trade.exitPrice ? `$${trade.exitPrice.toFixed(2)}` : '-'}</div>
                  <div>{trade.quantity}</div>
                  <div className={`pnl-cell ${trade.pnl > 0 ? 'positive' : 'negative'}`}>
                    ${trade.pnl.toFixed(2)}
                  </div>
                  <div>{trade.latencyMs}ms</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Utility Functions
function formatUptime(ms: number): string {
  const hours = Math.floor(ms / 3600000);
  const minutes = Math.floor((ms % 3600000) / 60000);
  return `${hours}h ${minutes}m`;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
}

function formatTimestamp(ts: number): string {
  return new Date(ts).toLocaleTimeString();
}

function generateTradesCsv(trades: TradeRecord[]): string {
  const headers = ['Entry Time', 'Exit Time', 'Entry Price', 'Exit Price', 'Qty', 'P&L', 'Latency (ms)'];
  const rows = trades.map((t) => [
    new Date(t.entryTime).toISOString(),
    t.exitTime ? new Date(t.exitTime).toISOString() : '',
    t.entryPrice,
    t.exitPrice || '',
    t.quantity,
    t.pnl,
    t.latencyMs,
  ]);

  const csv = [headers, ...rows.map((r) => r.map((v) => `"${v}"`).join(','))].join('\n');
  return csv;
}

function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default RealtimeMonitoringDashboard;
