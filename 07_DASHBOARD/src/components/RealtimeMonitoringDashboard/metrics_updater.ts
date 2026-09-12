/**
 * Metrics Updater Hook - State management for real-time metrics
 * Handles P&L charts, trade ledger, system health, strategy state
 */

import React, { useCallback, useReducer } from 'react';

export interface StrategyMetrics {
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

export interface TradeRecord {
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

export interface SystemHealth {
  cpuPercent: number;
  memoryPercent: number;
  dbSizeBytes: number;
  lastEodDownload: number;
  uptime: number;
  isHealthy: boolean;
}

export interface MetricsState {
  strategies: StrategyMetrics[];
  trades: TradeRecord[];
  systemHealth: SystemHealth;
  pnlHistory: { timestamp: number; value: number }[];
  lastUpdate: number;
  liveEnabled: boolean;
  authorityLevel: string;
}

export type MetricsAction =
  | { type: 'UPDATE_STRATEGY'; payload: Partial<StrategyMetrics> & { id: string } }
  | { type: 'ADD_TRADE'; payload: TradeRecord }
  | { type: 'UPDATE_TRADES'; payload: TradeRecord[] }
  | { type: 'UPDATE_SYSTEM_HEALTH'; payload: Partial<SystemHealth> }
  | { type: 'UPDATE_PNL_HISTORY'; payload: { timestamp: number; value: number }[] }
  | { type: 'RESET'; payload?: Partial<MetricsState> };

const initialState: MetricsState = {
  strategies: [],
  trades: [],
  systemHealth: {
    cpuPercent: 0,
    memoryPercent: 0,
    dbSizeBytes: 0,
    lastEodDownload: 0,
    uptime: 0,
    isHealthy: true,
  },
  pnlHistory: [],
  lastUpdate: Date.now(),
  liveEnabled: false,
  authorityLevel: 'ZERO',
};

function metricsReducer(state: MetricsState, action: MetricsAction): MetricsState {
  switch (action.type) {
    case 'UPDATE_STRATEGY': {
      const { id, ...updates } = action.payload;
      return {
        ...state,
        strategies: state.strategies.map((s) => (s.id === id ? { ...s, ...updates } : s)),
        lastUpdate: Date.now(),
      };
    }

    case 'ADD_TRADE': {
      const newTrades = [action.payload, ...state.trades].slice(0, 50); // Keep last 50
      return {
        ...state,
        trades: newTrades,
        lastUpdate: Date.now(),
      };
    }

    case 'UPDATE_TRADES': {
      return {
        ...state,
        trades: action.payload.slice(0, 50),
        lastUpdate: Date.now(),
      };
    }

    case 'UPDATE_SYSTEM_HEALTH': {
      return {
        ...state,
        systemHealth: { ...state.systemHealth, ...action.payload },
        lastUpdate: Date.now(),
      };
    }

    case 'UPDATE_PNL_HISTORY': {
      return {
        ...state,
        pnlHistory: action.payload.slice(-100), // Keep last 100 points
        lastUpdate: Date.now(),
      };
    }

    case 'RESET': {
      return { ...initialState, ...action.payload };
    }

    default:
      return state;
  }
}

/**
 * Hook for managing metrics state
 */
export function useMetricsState() {
  const [state, dispatch] = useReducer(metricsReducer, initialState);

  const updateStrategy = useCallback((id: string, updates: Partial<StrategyMetrics>) => {
    dispatch({ type: 'UPDATE_STRATEGY', payload: { id, ...updates } });
  }, []);

  const addTrade = useCallback((trade: TradeRecord) => {
    dispatch({ type: 'ADD_TRADE', payload: trade });
  }, []);

  const updateTrades = useCallback((trades: TradeRecord[]) => {
    dispatch({ type: 'UPDATE_TRADES', payload: trades });
  }, []);

  const updateSystemHealth = useCallback((health: Partial<SystemHealth>) => {
    dispatch({ type: 'UPDATE_SYSTEM_HEALTH', payload: health });
  }, []);

  const updatePnlHistory = useCallback((history: { timestamp: number; value: number }[]) => {
    dispatch({ type: 'UPDATE_PNL_HISTORY', payload: history });
  }, []);

  const reset = useCallback((partial?: Partial<MetricsState>) => {
    dispatch({ type: 'RESET', payload: partial });
  }, []);

  return {
    state,
    updateStrategy,
    addTrade,
    updateTrades,
    updateSystemHealth,
    updatePnlHistory,
    reset,
  };
}

/**
 * Hook for fetching metrics from API
 */
export function useMetricsFetch(apiBaseUrl: string, machineId: string, fencingToken: string) {
  return useCallback(async () => {
    try {
      const headers = {
        'Machine-ID': machineId,
        'Fencing-Token': fencingToken,
        'Content-Type': 'application/json',
      };

      const [batchRes, gatesRes, healthRes] = await Promise.all([
        fetch(`${apiBaseUrl}/batch/latest`, { headers }),
        fetch(`${apiBaseUrl}/gates`, { headers }),
        fetch(`${apiBaseUrl}/heartbeat/${machineId}/freshness`, { headers }),
      ]);

      if (!batchRes.ok || !gatesRes.ok || !healthRes.ok) {
        throw new Error('Failed to fetch metrics');
      }

      const [batch, gates, health] = await Promise.all([
        batchRes.json(),
        gatesRes.json(),
        healthRes.json(),
      ]);

      return { batch, gates, health };
    } catch (error) {
      console.error('Metrics fetch error:', error);
      throw error;
    }
  }, [apiBaseUrl, machineId, fencingToken]);
}

/**
 * Hook for polling metrics periodically
 */
export function useMetricsPolling(
  fetchFn: () => Promise<unknown>,
  onUpdate: (data: unknown) => void,
  intervalMs: number = 1000
) {
  React.useEffect(() => {
    const tick = () => {
      fetchFn()
        .then(onUpdate)
        .catch((error) => console.error('Polling error:', error));
    };
    tick();
    const interval = setInterval(tick, intervalMs);

    return () => clearInterval(interval);
  }, [fetchFn, onUpdate, intervalMs]);
}

/**
 * Calculate derived metrics from trades
 */
export function calculateTradeMetrics(trades: TradeRecord[]) {
  if (trades.length === 0) {
    return { winRate: 0, profitFactor: 1, maxDrawdown: 0, avgLatency: 0 };
  }

  const winningTrades = trades.filter((t) => t.pnl > 0);
  const losingTrades = trades.filter((t) => t.pnl < 0);

  const winRate = (winningTrades.length / trades.length) * 100;
  const totalWins = winningTrades.reduce((sum, t) => sum + t.pnl, 0);
  const totalLosses = Math.abs(losingTrades.reduce((sum, t) => sum + t.pnl, 0));
  const profitFactor = totalLosses > 0 ? totalWins / totalLosses : totalWins > 0 ? Infinity : 1;

  let cumulativePnl = 0;
  let maxDrawdown = 0;
  let peak = 0;

  for (const trade of trades) {
    cumulativePnl += trade.pnl;
    if (cumulativePnl > peak) peak = cumulativePnl;
    const drawdown = peak - cumulativePnl;
    if (drawdown > maxDrawdown) maxDrawdown = drawdown;
  }

  const avgLatency = trades.reduce((sum, t) => sum + t.latencyMs, 0) / trades.length;

  return { winRate, profitFactor, maxDrawdown, avgLatency };
}
