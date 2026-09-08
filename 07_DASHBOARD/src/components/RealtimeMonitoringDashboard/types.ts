/**
 * Shared Type Definitions for Real-time Monitoring Dashboard
 * Ensures type safety across WebSocket, metrics, and components
 */

/**
 * Strategy Execution State
 */
export type StrategyState = 'running' | 'idle' | 'error' | 'completed';

/**
 * Trade Direction
 */
export type TradeType = 'LONG' | 'SHORT' | 'HEDGE';

/**
 * Connection Status
 */
export type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting';

/**
 * Alert Severity Levels
 */
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

/**
 * Current Strategy Metrics
 * Aggregated performance for a single strategy
 */
export interface StrategyMetrics {
  id: string;
  name: string;
  version: string;
  state: StrategyState;
  startTime: number; // Unix timestamp
  trades: TradeRecord[];
  pnlCurrent: number;
  pnlMax: number;
  winRate: number;
  profitFactor: number;
  maxDrawdown: number;
}

/**
 * Individual Trade Record
 * Immutable record of a single trade execution
 */
export interface TradeRecord {
  id: string;
  strategyId: string;
  entryTime: number; // Unix timestamp
  exitTime?: number; // Unix timestamp
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  pnl: number;
  latencyMs: number; // Execution latency
  type: TradeType;
}

/**
 * System Health Metrics
 * Real-time system resource and database status
 */
export interface SystemHealth {
  cpuPercent: number; // 0-100
  memoryPercent: number; // 0-100
  dbSizeBytes: number;
  lastEodDownload: number; // Unix timestamp
  uptime: number; // Milliseconds
  isHealthy: boolean;
}

/**
 * P&L History Point
 * Single data point for P&L charting
 */
export interface PnlHistoryPoint {
  timestamp: number; // Unix timestamp
  value: number; // Cumulative P&L
}

/**
 * Metrics State
 * Root state for all metrics in dashboard
 */
export interface MetricsState {
  strategies: StrategyMetrics[];
  trades: TradeRecord[];
  systemHealth: SystemHealth;
  pnlHistory: PnlHistoryPoint[];
  lastUpdate: number; // Unix timestamp
  liveEnabled: boolean;
  authorityLevel: string; // 'ZERO', etc.
}

/**
 * Calculated Trade Metrics
 * Derived statistics from trade records
 */
export interface CalculatedMetrics {
  winRate: number; // Percentage (0-100)
  profitFactor: number; // Gross wins / Gross losses
  maxDrawdown: number; // Peak to trough decline
  avgLatency: number; // Average execution latency (ms)
}

/**
 * WebSocket Metrics Update Message
 * Messages received from server
 */
export interface MetricsUpdate {
  type: 'heartbeat' | 'gates' | 'batch' | 'trades' | 'health' | 'error';
  timestamp: number; // Unix timestamp
  data?: Record<string, unknown>;
  error?: string;
}

/**
 * API Response - Batch Summary
 * From GET /batch/{batch_id}
 */
export interface BatchSummaryResponse {
  batch_id: string;
  verdict_status: string;
  alert_array: AlertRecord[];
  pnl_summary: {
    gross_pnl: number;
    net_pnl: number;
    currency: string;
  };
  risk_metrics: {
    max_drawdown_pct: number;
    sharpe_ratio: number;
    win_rate_pct: number;
  };
}

/**
 * API Response - Guardian Gates
 * From GET /gates
 */
export interface GateVerdictResponse {
  gate_id: number;
  gate_name: string;
  verdict: 'PASS' | 'BLOCKED' | 'NOT_PROVEN';
  evidence_id: string;
  event_time: number;
  knowledge_time: number;
  truth_age_seconds: number;
}

/**
 * API Response - System Heartbeat
 * From GET /heartbeat/{machine_id}/freshness
 */
export interface HeartbeatResponse {
  age_seconds: number;
  is_fresh: boolean;
  warning_level: 'fresh' | 'warning' | 'stale';
  stale_since?: number;
  last_update: number;
}

/**
 * Alert Record
 * Single alert or notification
 */
export interface AlertRecord {
  alert_id: string;
  batch_id: string;
  severity: AlertSeverity;
  alert_type: string;
  message: string;
  timestamp: number;
  escalation_flag: boolean;
  resolution_status: 'open' | 'resolved' | 'dismissed';
}

/**
 * Date Range Filter
 * For filtering trades by time
 */
export interface DateRange {
  start: Date;
  end: Date;
}

/**
 * Trade Metrics Response
 * Derived metrics calculation result
 */
export interface TradeMetricsResponse {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  totalWins: number;
  totalLosses: number;
  profitFactor: number;
  maxDrawdown: number;
  avgLatency: number;
  cumulative: {
    pnl: number;
    trades: number;
  };
}

/**
 * Dashboard Props
 * Main component configuration
 */
export interface DashboardProps {
  apiBaseUrl: string;
  wsUrl: string;
  machineId: string;
  fencingToken: string;
  onAuthError?: (error: string) => void;
}

/**
 * WebSocket Client Config
 * Configuration for WebSocket connection
 */
export interface WebSocketClientConfig {
  url: string;
  machineId: string;
  fencingToken: string;
  reconnectAttempts: number;
  reconnectDelayMs: number;
  onUpdate: (update: MetricsUpdate) => void;
  onError: (error: string) => void;
  onStatusChange: (status: ConnectionStatus) => void;
}

/**
 * Metrics Action
 * Redux-style actions for state management
 */
export type MetricsAction =
  | { type: 'UPDATE_STRATEGY'; payload: Partial<StrategyMetrics> & { id: string } }
  | { type: 'ADD_TRADE'; payload: TradeRecord }
  | { type: 'UPDATE_TRADES'; payload: TradeRecord[] }
  | { type: 'UPDATE_SYSTEM_HEALTH'; payload: Partial<SystemHealth> }
  | { type: 'UPDATE_PNL_HISTORY'; payload: PnlHistoryPoint[] }
  | { type: 'RESET'; payload?: Partial<MetricsState> };
