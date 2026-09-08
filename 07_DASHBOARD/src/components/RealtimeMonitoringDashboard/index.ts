/**
 * Real-time Monitoring Dashboard - Public API
 * Exports all components and utilities for external use
 */

export { RealtimeMonitoringDashboard, type DashboardProps } from './dashboard_component';

export {
  WebSocketClient,
  useWebSocketClient,
  type MetricsUpdate,
  type WebSocketClientConfig,
} from './websocket_client';

export {
  useMetricsState,
  useMetricsFetch,
  useMetricsPolling,
  calculateTradeMetrics,
  type StrategyMetrics,
  type TradeRecord,
  type SystemHealth,
  type MetricsState,
  type MetricsAction,
} from './metrics_updater';
