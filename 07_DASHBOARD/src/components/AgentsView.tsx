import React, { useState } from 'react';

interface Agent {
  id: string;
  name: string;
  status: 'running' | 'idle' | 'error';
  uptime: string;
  trades_today: number;
  avg_pnl: number;
  last_activity: string;
}

const mockAgents: Agent[] = [
  {
    id: 'A001',
    name: 'RR500/V03 Baseline',
    status: 'running',
    uptime: '14h 32m',
    trades_today: 12,
    avg_pnl: 85.75,
    last_activity: '2 min ago',
  },
  {
    id: 'A002',
    name: 'Momentum+RSI Variant',
    status: 'running',
    uptime: '8h 15m',
    trades_today: 7,
    avg_pnl: 62.50,
    last_activity: '5 min ago',
  },
  {
    id: 'A003',
    name: 'Mean Reversion Strategy',
    status: 'idle',
    uptime: '2h 44m',
    trades_today: 2,
    avg_pnl: 35.00,
    last_activity: '45 min ago',
  },
  {
    id: 'A004',
    name: 'Trend Following V2',
    status: 'error',
    uptime: '0h 0m',
    trades_today: 0,
    avg_pnl: 0,
    last_activity: '1h 20m ago',
  },
];

const AgentsView: React.FC = () => {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  const stats = {
    total: mockAgents.length,
    running: mockAgents.filter((a) => a.status === 'running').length,
    idle: mockAgents.filter((a) => a.status === 'idle').length,
    error: mockAgents.filter((a) => a.status === 'error').length,
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'var(--color-pass-green)';
      case 'idle':
        return 'var(--color-warning-yellow)';
      case 'error':
        return 'var(--color-fail-red)';
      default:
        return 'var(--color-text-secondary)';
    }
  };

  return (
    <div style={{ padding: 'var(--spacing-6)' }}>
      {/* Stats */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: 'var(--spacing-4)',
          marginBottom: 'var(--spacing-6)',
        }}
      >
        <StatCard label="Total Agents" value={stats.total} color="blue" />
        <StatCard label="Running" value={stats.running} color="green" />
        <StatCard label="Idle" value={stats.idle} color="yellow" />
        <StatCard label="Error" value={stats.error} color="red" />
      </div>

      {/* Agents Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: 'var(--spacing-4)',
        }}
      >
        {mockAgents.map((agent) => (
          <div
            key={agent.id}
            onClick={() => setSelectedAgent(agent.id)}
            style={{
              padding: 'var(--spacing-6)',
              background: 'var(--hq-panel-bg)',
              borderRadius: '12px',
              border: selectedAgent === agent.id ? '2px solid var(--color-low-blue)' : '1px solid var(--color-border)',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {/* Agent Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-4)' }}>
              <div>
                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: '4px' }}>{agent.name}</h3>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>ID: {agent.id}</p>
              </div>
              <div
                style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: getStatusColor(agent.status),
                  flexShrink: 0,
                }}
              />
            </div>

            {/* Metrics */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-3)' }}>
              <div>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                  Status
                </p>
                <p style={{ fontSize: 'var(--font-size-sm)', fontWeight: '600', color: getStatusColor(agent.status) }}>
                  {agent.status.toUpperCase()}
                </p>
              </div>

              <div>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                  Uptime
                </p>
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>{agent.uptime}</p>
              </div>

              <div>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                  Trades Today
                </p>
                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>{agent.trades_today}</p>
              </div>

              <div>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                  Avg P&L
                </p>
                <p
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: '600',
                    color: agent.avg_pnl > 0 ? 'var(--color-pass-green)' : 'var(--color-fail-red)',
                  }}
                >
                  ${agent.avg_pnl.toFixed(2)}
                </p>
              </div>

              <div style={{ paddingTop: 'var(--spacing-3)', borderTop: '1px solid var(--color-border)' }}>
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
                  Last activity: {agent.last_activity}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Agent Details */}
      {selectedAgent && (
        <div
          style={{
            marginTop: 'var(--spacing-6)',
            padding: 'var(--spacing-6)',
            background: 'var(--hq-panel-bg)',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
          }}
        >
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
            Agent Details
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--spacing-4)' }}>
            <div>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                CPU Usage
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div
                  style={{
                    flex: 1,
                    height: '6px',
                    background: 'rgba(51, 65, 85, 0.3)',
                    borderRadius: '3px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: '45%',
                      background: 'var(--color-low-blue)',
                    }}
                  />
                </div>
                <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>45%</span>
              </div>
            </div>

            <div>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                Memory Usage
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div
                  style={{
                    flex: 1,
                    height: '6px',
                    background: 'rgba(51, 65, 85, 0.3)',
                    borderRadius: '3px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: '28%',
                      background: 'var(--color-pass-green)',
                    }}
                  />
                </div>
                <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>256 MB</span>
              </div>
            </div>

            <div>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                Network I/O
              </p>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>1.2 MB/s</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const StatCard: React.FC<{ label: string; value: number; color: 'blue' | 'green' | 'yellow' | 'red' }> = ({ label, value, color }) => {
  const colorMap = {
    blue: 'var(--color-low-blue)',
    green: 'var(--color-pass-green)',
    yellow: 'var(--color-warning-yellow)',
    red: 'var(--color-fail-red)',
  };

  return (
    <div
      style={{
        padding: 'var(--spacing-4)',
        background: 'var(--hq-panel-bg)',
        borderRadius: '12px',
        border: '1px solid var(--color-border)',
      }}
    >
      <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '8px' }}>
        {label}
      </p>
      <p style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'bold', color: colorMap[color] }}>{value}</p>
    </div>
  );
};

export default AgentsView;
