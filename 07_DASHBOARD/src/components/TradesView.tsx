import React, { useState } from 'react';

interface Trade {
  id: string;
  symbol: string;
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number;
  status: 'closed' | 'open';
  direction: 'long' | 'short';
}

const mockTrades: Trade[] = [
  {
    id: 'T001',
    symbol: 'NQ',
    entry_time: '09:30:15',
    exit_time: '10:45:22',
    entry_price: 20150.50,
    exit_price: 20285.25,
    quantity: 2,
    pnl: 269.50,
    status: 'closed',
    direction: 'long',
  },
  {
    id: 'T002',
    symbol: 'ES',
    entry_time: '10:15:08',
    exit_time: '11:22:30',
    entry_price: 5425.75,
    exit_price: 5438.50,
    quantity: 5,
    pnl: 63.75,
    status: 'closed',
    direction: 'long',
  },
  {
    id: 'T003',
    symbol: 'MNQ',
    entry_time: '11:45:40',
    exit_time: null,
    entry_price: 20175.00,
    exit_price: 20225.50,
    quantity: 1,
    pnl: 50.50,
    status: 'open',
    direction: 'long',
  },
  {
    id: 'T004',
    symbol: 'ES',
    entry_time: '13:20:15',
    exit_time: '14:05:45',
    entry_price: 5440.25,
    exit_price: 5408.75,
    quantity: 3,
    pnl: -93.50,
    status: 'closed',
    direction: 'short',
  },
  {
    id: 'T005',
    symbol: 'NQ',
    entry_time: '14:30:00',
    exit_time: '15:15:20',
    entry_price: 20300.00,
    exit_price: 20380.50,
    quantity: 1,
    pnl: 80.50,
    status: 'closed',
    direction: 'long',
  },
];

const TradesView: React.FC = () => {
  const [sortBy, setSortBy] = useState<'time' | 'pnl' | 'symbol'>('time');
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all');

  const filteredTrades = mockTrades.filter((t) => {
    if (filter === 'open') return t.status === 'open';
    if (filter === 'closed') return t.status === 'closed';
    return true;
  });

  const sortedTrades = [...filteredTrades].sort((a, b) => {
    if (sortBy === 'pnl') return b.pnl - a.pnl;
    if (sortBy === 'symbol') return a.symbol.localeCompare(b.symbol);
    return b.entry_time.localeCompare(a.entry_time);
  });

  const stats = {
    total: filteredTrades.length,
    wins: filteredTrades.filter((t) => t.pnl > 0).length,
    losses: filteredTrades.filter((t) => t.pnl < 0).length,
    totalPnl: filteredTrades.reduce((sum, t) => sum + t.pnl, 0),
  };

  return (
    <div
      style={{
        padding: 'var(--spacing-6)',
        background: 'var(--hq-panel-bg)',
        borderRadius: '12px',
        border: '1px solid var(--color-border)',
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 'var(--spacing-6)' }}>
        <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-4)' }}>
          Trade Execution Log
        </h2>

        {/* Stats */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: 'var(--spacing-4)',
            marginBottom: 'var(--spacing-4)',
          }}
        >
          <div style={{ padding: 'var(--spacing-3)', background: 'rgba(51, 65, 85, 0.3)', borderRadius: '8px' }}>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
              Total Trades
            </p>
            <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-text-primary)' }}>
              {stats.total}
            </p>
          </div>

          <div style={{ padding: 'var(--spacing-3)', background: 'rgba(51, 65, 85, 0.3)', borderRadius: '8px' }}>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
              Wins
            </p>
            <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-pass-green)' }}>
              {stats.wins}
            </p>
          </div>

          <div style={{ padding: 'var(--spacing-3)', background: 'rgba(51, 65, 85, 0.3)', borderRadius: '8px' }}>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
              Losses
            </p>
            <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-fail-red)' }}>
              {stats.losses}
            </p>
          </div>

          <div style={{ padding: 'var(--spacing-3)', background: 'rgba(51, 65, 85, 0.3)', borderRadius: '8px' }}>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
              Total P&L
            </p>
            <p
              style={{
                fontSize: 'var(--font-size-2xl)',
                fontWeight: 'bold',
                color: stats.totalPnl > 0 ? 'var(--color-pass-green)' : 'var(--color-fail-red)',
              }}
            >
              ${stats.totalPnl.toFixed(2)}
            </p>
          </div>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', gap: 'var(--spacing-3)', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginRight: '8px' }}>
              Filter:
            </label>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              style={{
                padding: '6px 12px',
                background: 'rgba(51, 65, 85, 0.5)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                color: 'var(--color-text-primary)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              <option value="all">All Trades</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginRight: '8px' }}>
              Sort:
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              style={{
                padding: '6px 12px',
                background: 'rgba(51, 65, 85, 0.5)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                color: 'var(--color-text-primary)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              <option value="time">By Time</option>
              <option value="pnl">By P&L</option>
              <option value="symbol">By Symbol</option>
            </select>
          </div>
        </div>
      </div>

      {/* Trade Table */}
      <div
        style={{
          overflowX: 'auto',
          borderRadius: '8px',
          border: '1px solid var(--color-border)',
        }}
      >
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          <thead>
            <tr style={{ background: 'rgba(51, 65, 85, 0.3)', borderBottom: '1px solid var(--color-border)' }}>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                Time
              </th>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                Symbol
              </th>
              <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                Direction
              </th>
              <th style={{ padding: '12px', textAlign: 'right', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                Entry
              </th>
              <th style={{ padding: '12px', textAlign: 'right', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                Exit
              </th>
              <th style={{ padding: '12px', textAlign: 'right', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                Qty
              </th>
              <th style={{ padding: '12px', textAlign: 'right', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                P&L
              </th>
              <th style={{ padding: '12px', textAlign: 'center', fontWeight: '600', color: 'var(--color-text-secondary)' }}>
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedTrades.map((trade) => (
              <tr key={trade.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={{ padding: '12px', color: 'var(--color-text-primary)' }}>{trade.entry_time}</td>
                <td style={{ padding: '12px', color: 'var(--color-text-primary)', fontWeight: '600' }}>{trade.symbol}</td>
                <td style={{ padding: '12px', color: trade.direction === 'long' ? 'var(--color-low-blue)' : 'var(--color-fail-red)' }}>
                  {trade.direction.toUpperCase()}
                </td>
                <td style={{ padding: '12px', textAlign: 'right', color: 'var(--color-text-primary)' }}>
                  ${trade.entry_price.toFixed(2)}
                </td>
                <td style={{ padding: '12px', textAlign: 'right', color: 'var(--color-text-primary)' }}>
                  {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '—'}
                </td>
                <td style={{ padding: '12px', textAlign: 'right', color: 'var(--color-text-primary)' }}>{trade.quantity}</td>
                <td
                  style={{
                    padding: '12px',
                    textAlign: 'right',
                    color: trade.pnl > 0 ? 'var(--color-pass-green)' : 'var(--color-fail-red)',
                    fontWeight: '600',
                  }}
                >
                  ${trade.pnl > 0 ? '+' : ''}
                  {trade.pnl.toFixed(2)}
                </td>
                <td style={{ padding: '12px', textAlign: 'center' }}>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: 'var(--font-size-xs)',
                      fontWeight: '600',
                      background: trade.status === 'closed' ? 'rgba(74, 144, 226, 0.2)' : 'rgba(251, 191, 36, 0.2)',
                      color: trade.status === 'closed' ? 'var(--color-low-blue)' : 'var(--color-warning-yellow)',
                    }}
                  >
                    {trade.status === 'closed' ? 'CLOSED' : 'OPEN'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TradesView;
