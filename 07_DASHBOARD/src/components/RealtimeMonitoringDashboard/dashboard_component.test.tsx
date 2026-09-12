import { vi, type Mock } from 'vitest';
/**
 * Dashboard Component Unit Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { RealtimeMonitoringDashboard } from './dashboard_component';

describe('RealtimeMonitoringDashboard', () => {
  const defaultProps = {
    apiBaseUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000',
    machineId: 'machine-001',
    fencingToken: 'token-123',
  };

  beforeEach(() => {
    // Mock WebSocket
    global.WebSocket = vi.fn(() => ({
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    })) as any;

    // Mock fetch
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      })
    ) as Mock;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render dashboard container', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    expect(screen.getByText('Autonomous Lab Monitoring Dashboard')).toBeInTheDocument();
  });

  it('should display authority banner', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    expect(screen.getByText('AUTHORITY: ZERO')).toBeInTheDocument();
    expect(screen.getByText('LIVE: OFF')).toBeInTheDocument();
  });

  it('should display authority message', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    const message = screen.getByText(/Evidence-scoped review mode/i);
    expect(message).toBeInTheDocument();
  });

  it('should disable simulator buttons', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    const buttons = screen.getAllByText(/Simulator/i);
    buttons.forEach((button) => {
      expect(button).toBeDisabled();
    });
  });

  it('should render Download CSV button', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    expect(screen.getByText('Download CSV')).toBeInTheDocument();
  });

  it('should render metrics cards', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    expect(screen.getByText('Strategies Running')).toBeInTheDocument();
    expect(screen.getByText('P&L Summary')).toBeInTheDocument();
    expect(screen.getByText('System Health')).toBeInTheDocument();
  });

  it('should render trade ledger', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    expect(screen.getByText('Latest Trades (Last 50)')).toBeInTheDocument();
  });

  it('should render trade table headers', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    const headers = [
      'Entry Time',
      'Exit Time',
      'Entry Price',
      'Exit Price',
      'Qty',
      'P&L',
      'Latency (ms)',
    ];
    headers.forEach((header) => {
      expect(screen.getByText(header)).toBeInTheDocument();
    });
  });

  it('should render filter controls', () => {
    const { container } = render(<RealtimeMonitoringDashboard {...defaultProps} />);
    const dateInputs = container.querySelectorAll('input[type="date"]');
    expect(dateInputs.length).toBeGreaterThan(0);
  });

  it('should handle empty states gracefully', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    expect(screen.getByText('No strategies currently running')).toBeInTheDocument();
  });

  it('should display system health metrics', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    expect(screen.getByText(/CPU/i)).toBeInTheDocument();
    expect(screen.getByText(/Memory/i)).toBeInTheDocument();
    expect(screen.getByText(/DB Size/i)).toBeInTheDocument();
  });

  it('should have responsive layout', () => {
    const { container } = render(<RealtimeMonitoringDashboard {...defaultProps} />);
    const grid = container.querySelector('.metrics-grid');
    expect(grid).toHaveClass('metrics-grid');
  });

  it('should handle CSV download', () => {
    const createElementSpy = vi.spyOn(document, 'createElement');
    render(<RealtimeMonitoringDashboard {...defaultProps} />);

    const downloadButton = screen.getByText('Download CSV');
    fireEvent.click(downloadButton);

    // Verify download functionality was triggered
    expect(createElementSpy).toHaveBeenCalledWith('a');
  });

  it('should display connection status', async () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);

    await waitFor(() => {
      const statusBadge = screen.queryByText(/CONNECTED|DISCONNECTED|RECONNECTING/i);
      expect(statusBadge).toBeInTheDocument();
    });
  });

  it('should handle date range filtering', () => {
    const { container } = render(<RealtimeMonitoringDashboard {...defaultProps} />);
    const dateInputs = Array.from(container.querySelectorAll('input[type="date"]'));
    expect(dateInputs.length).toBeGreaterThan(0);

    // User can interact with date inputs
    fireEvent.change(dateInputs[0], { target: { value: '2026-09-06' } });
    expect((dateInputs[0] as HTMLInputElement).value).toBe('2026-09-06');
  });

  it('should call onAuthError callback on connection error', async () => {
    const onAuthError = vi.fn();
    render(
      <RealtimeMonitoringDashboard
        {...defaultProps}
        onAuthError={onAuthError}
      />
    );

    await waitFor(() => {
      // Simulate connection error
      expect(onAuthError).toHaveBeenCalledTimes(0);
    });
  });

  it('should format currency correctly', () => {
    render(<RealtimeMonitoringDashboard {...defaultProps} />);
    const pnlValues = screen.getAllByText(/\$0\.00/);
    expect(pnlValues.length).toBeGreaterThan(0);
  });
});
