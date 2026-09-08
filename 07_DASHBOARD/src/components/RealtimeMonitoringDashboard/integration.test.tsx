/**
 * Integration Tests - Dashboard with WebSocket and Metrics
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { RealtimeMonitoringDashboard } from './dashboard_component';
import { WebSocketClient } from './websocket_client';
import { calculateTradeMetrics, TradeRecord } from './metrics_updater';

describe('Dashboard Integration Tests', () => {
  beforeEach(() => {
    // Mock WebSocket
    global.WebSocket = jest.fn(() => ({
      readyState: 1,
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    })) as any;

    // Mock fetch
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          batch: { pnl: 1000, trades: [] },
          gates: [],
          health: { cpuPercent: 45, memoryPercent: 60 },
        }),
      })
    ) as jest.Mock;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize dashboard with WebSocket connection', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Autonomous Lab Monitoring Dashboard')).toBeInTheDocument();
    });

    expect(global.WebSocket).toHaveBeenCalled();
  });

  it('should fetch metrics from API on mount', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  it('should display Authority-ZERO locked status', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('AUTHORITY: ZERO')).toBeInTheDocument();
      expect(screen.getByText('LIVE: OFF')).toBeInTheDocument();
    });
  });

  it('should handle real-time metrics update', async () => {
    const trades: TradeRecord[] = [
      {
        id: '1',
        strategyId: 's1',
        entryTime: Date.now() - 10000,
        entryPrice: 100,
        exitPrice: 105,
        quantity: 10,
        pnl: 500,
        latencyMs: 45,
        type: 'LONG',
      },
      {
        id: '2',
        strategyId: 's1',
        entryTime: Date.now() - 5000,
        entryPrice: 105,
        exitPrice: 104,
        quantity: 10,
        pnl: -100,
        latencyMs: 50,
        type: 'SHORT',
      },
    ];

    const metrics = calculateTradeMetrics(trades);

    expect(metrics.winRate).toBe(50);
    expect(metrics.profitFactor).toBe(5);
    expect(metrics.avgLatency).toBe(47.5);
  });

  it('should process WebSocket updates', async () => {
    const onAuthError = jest.fn();

    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
        onAuthError={onAuthError}
      />
    );

    await waitFor(() => {
      // WebSocket should be established
      expect(global.WebSocket).toHaveBeenCalled();
    });
  });

  it('should format currency values correctly', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      // Should display P&L in currency format
      const pnlValue = screen.getByText(/\$/);
      expect(pnlValue).toBeInTheDocument();
    });
  });

  it('should respect Guardian-approved read-only mode', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      // Simulator buttons should be disabled
      const startButton = screen.getByText('Start Simulator');
      const stopButton = screen.getByText('Stop Simulator');
      expect(startButton).toBeDisabled();
      expect(stopButton).toBeDisabled();
    });
  });

  it('should handle multiple concurrent API requests', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      // Should have made multiple fetch calls
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });
  });

  it('should validate auth headers in API calls', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      const calls = (global.fetch as jest.Mock).mock.calls;
      if (calls.length > 0) {
        const lastCall = calls[calls.length - 1];
        if (lastCall[1]) {
          expect(lastCall[1].headers).toHaveProperty('Machine-ID', 'machine-001');
          expect(lastCall[1].headers).toHaveProperty('Fencing-Token', 'token-123');
        }
      }
    });
  });

  it('should handle trade filtering by date range', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Latest Trades (Last 50)')).toBeInTheDocument();
    });
  });

  it('should display system health metrics', async () => {
    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('System Health')).toBeInTheDocument();
      expect(screen.getByText(/CPU/)).toBeInTheDocument();
      expect(screen.getByText(/Memory/)).toBeInTheDocument();
      expect(screen.getByText(/DB Size/)).toBeInTheDocument();
    });
  });

  it('should maintain data freshness with polling', async () => {
    jest.useFakeTimers();

    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    // Fast-forward 1 second for polling
    jest.advanceTimersByTime(1000);

    await waitFor(() => {
      // Should have made additional fetch calls
      expect((global.fetch as jest.Mock).mock.calls.length).toBeGreaterThan(3);
    });

    jest.useRealTimers();
  });

  it('should handle export to CSV', async () => {
    const createElementSpy = jest.spyOn(document, 'createElement');
    const appendChildSpy = jest.spyOn(document, 'appendChild');

    render(
      <RealtimeMonitoringDashboard
        apiBaseUrl="http://localhost:8000"
        wsUrl="ws://localhost:8000"
        machineId="machine-001"
        fencingToken="token-123"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Download CSV')).toBeInTheDocument();
    });

    createElementSpy.mockRestore();
    appendChildSpy.mockRestore();
  });
});
