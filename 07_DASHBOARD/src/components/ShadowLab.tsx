import React, { useState, useEffect } from 'react';
import './ShadowLab.css';

interface Strategy {
  name: string;
  description: string;
  baseline_winrate: number;
  baseline_pnl: number;
  baseline_trades: number;
}

interface TradeMetrics {
  session_id: string;
  strategy_name: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  gross_pnl_dollars: number;
  net_pnl_dollars: number;
  max_drawdown_dollars: number;
  avg_pnl_per_trade: number;
  profit_factor: number;
  trade_count: number;
}

interface Trade {
  event_id: string;
  strategy: string;
  instrument: string;
  side: string;
  entry_time: string;
  entry_price: number;
  quantity: number;
  stop: number;
  target: number;
  exit_time?: string;
  exit_price?: number;
  status: string;
  pnl_ticks?: number;
  pnl_dollars?: number;
  cost: number;
  slippage: number;
}

interface Comparison {
  session_metrics: TradeMetrics;
  baseline: {
    win_rate: number;
    pnl_dollars: number;
    pnl_per_trade: number;
    trades: number;
  };
  comparison: {
    vs_baseline_winrate: number;
    vs_baseline_pnl: number;
    performance: string;
  };
}

export const ShadowLab: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState('RR500');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [marketDate, setMarketDate] = useState(
    new Date().toISOString().split('T')[0].replace(/-/g, '')
  );
  const [metrics, setMetrics] = useState<TradeMetrics | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8002';

  // Load strategies
  useEffect(() => {
    const loadStrategies = async () => {
      try {
        const response = await fetch(`${apiUrl}/shadow/strategies`);
        if (response.ok) {
          const data = await response.json();
          setStrategies(data);
        }
      } catch (err) {
        console.error('Failed to load strategies:', err);
      }
    };

    loadStrategies();
  }, [apiUrl]);

  const handleCreateSession = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/shadow/session/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_name: selectedStrategy,
          instrument: 'NQ',
          market_date: marketDate,
          replay_speed: 1,
          start_time: '09:30',
          end_time: '16:00',
        }),
      });

      if (response.ok) {
        const session = await response.json();
        setSessionId(session.session_id);
      } else {
        setError('Failed to create session');
      }
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMetrics = async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const [metricsRes, tradesRes, comparisonRes] = await Promise.all([
        fetch(`${apiUrl}/shadow/session/${sessionId}/metrics`),
        fetch(`${apiUrl}/shadow/session/${sessionId}/trades`),
        fetch(`${apiUrl}/shadow/session/${sessionId}/vs-baseline`),
      ]);

      if (metricsRes.ok) {
        const m = await metricsRes.json();
        setMetrics(m);
      }

      if (tradesRes.ok) {
        const t = await tradesRes.json();
        setTrades(t.trades);
      }

      if (comparisonRes.ok) {
        const c = await comparisonRes.json();
        setComparison(c);
      }
    } catch (err) {
      setError(`Error loading metrics: ${err instanceof Error ? err.message : 'Unknown'}`);
    } finally {
      setLoading(false);
    }
  };

  const pnlColor = (pnl: number) =>
    pnl > 0 ? '#10b981' : pnl < 0 ? '#ef4444' : '#6b7280';
  const winrateColor = (wr: number, baseline: number) =>
    wr >= baseline ? '#10b981' : '#f59e0b';

  return (
    <div className="shadow-lab">
      <div className="lab-header">
        <h1>Shadow Lab</h1>
        <p>Market Replay Testing - Authority=ZERO, Live=OFF</p>
      </div>

      <div className="lab-controls">
        <div className="control-group">
          <label>Strategy:</label>
          <select
            value={selectedStrategy}
            onChange={(e) => setSelectedStrategy(e.target.value)}
            disabled={!!sessionId}
          >
            {strategies.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name} - {s.description}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>Market Date:</label>
          <input
            type="date"
            value={marketDate.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
            onChange={(e) => setMarketDate(e.target.value.replace(/-/g, ''))}
            disabled={!!sessionId}
          />
        </div>

        {!sessionId ? (
          <button
            onClick={handleCreateSession}
            disabled={loading}
            className="btn-primary"
          >
            {loading ? 'Creating...' : 'Create Session'}
          </button>
        ) : (
          <div className="session-active">
            <span className="badge">Session Active</span>
            <code className="session-id">{sessionId?.substring(0, 8)}...</code>
            <button
              onClick={() => {
                setSessionId(null);
                setMetrics(null);
                setTrades([]);
                setComparison(null);
              }}
              className="btn-secondary"
            >
              New Session
            </button>
          </div>
        )}
      </div>

      {sessionId && !metrics && (
        <div className="load-section">
          <button onClick={handleLoadMetrics} disabled={loading} className="btn-primary">
            {loading ? 'Loading...' : 'Load Replay Data'}
          </button>
        </div>
      )}

      {error && <div className="error-box">{error}</div>}

      {metrics && (
        <div className="metrics-container">
          {/* P&L Ticker */}
          <div className="pnl-ticker">
            <div className="ticker-item">
              <span className="label">Net P&L</span>
              <span
                className="value"
                style={{ color: pnlColor(metrics.net_pnl_dollars) }}
              >
                ${metrics.net_pnl_dollars.toFixed(2)}
              </span>
            </div>

            <div className="ticker-item">
              <span className="label">Trades</span>
              <span className="value">{metrics.total_trades}</span>
            </div>

            <div className="ticker-item">
              <span className="label">Win Rate</span>
              <span
                className="value"
                style={{
                  color: winrateColor(
                    metrics.win_rate,
                    comparison?.baseline.win_rate || 0.833
                  ),
                }}
              >
                {(metrics.win_rate * 100).toFixed(1)}%
              </span>
            </div>

            <div className="ticker-item">
              <span className="label">Max DD</span>
              <span
                className="value"
                style={{ color: pnlColor(-metrics.max_drawdown_dollars) }}
              >
                ${Math.abs(metrics.max_drawdown_dollars).toFixed(2)}
              </span>
            </div>

            <div className="ticker-item">
              <span className="label">Avg/Trade</span>
              <span
                className="value"
                style={{ color: pnlColor(metrics.avg_pnl_per_trade) }}
              >
                ${metrics.avg_pnl_per_trade.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Comparison to Baseline */}
          {comparison && (
            <div className="baseline-comparison">
              <h3>vs RR500 Baseline</h3>
              <div className="comparison-grid">
                <div className="comp-item">
                  <span className="label">Baseline Win Rate</span>
                  <span className="baseline-value">
                    {(comparison.baseline.win_rate * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="comp-item">
                  <span className="label">Your Win Rate</span>
                  <span
                    className="your-value"
                    style={{
                      color: winrateColor(
                        metrics.win_rate,
                        comparison.baseline.win_rate
                      ),
                    }}
                  >
                    {(metrics.win_rate * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="comp-item">
                  <span className="label">Baseline P&L</span>
                  <span className="baseline-value">
                    ${comparison.baseline.pnl_dollars.toFixed(2)}
                  </span>
                </div>

                <div className="comp-item">
                  <span className="label">Your P&L</span>
                  <span
                    className="your-value"
                    style={{ color: pnlColor(metrics.net_pnl_dollars) }}
                  >
                    ${metrics.net_pnl_dollars.toFixed(2)}
                  </span>
                </div>

                <div className="comp-item verdict">
                  <span className="label">Verdict</span>
                  <span
                    className="verdict-badge"
                    style={{
                      backgroundColor:
                        comparison.comparison.performance === 'PASS'
                          ? '#10b981'
                          : '#f59e0b',
                    }}
                  >
                    {comparison.comparison.performance}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Trade Ledger */}
          <div className="trade-ledger">
            <h3>Trade Ledger</h3>
            <div className="trades-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Side</th>
                    <th>Entry</th>
                    <th>Qty</th>
                    <th>Exit</th>
                    <th>Stop</th>
                    <th>Target</th>
                    <th>Status</th>
                    <th>P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((trade) => (
                    <tr key={trade.event_id} className="trade-row">
                      <td className={`side-${trade.side.toLowerCase()}`}>
                        {trade.side}
                      </td>
                      <td>${trade.entry_price.toFixed(2)}</td>
                      <td>{trade.quantity}</td>
                      <td>
                        {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}
                      </td>
                      <td>${trade.stop.toFixed(2)}</td>
                      <td>${trade.target.toFixed(2)}</td>
                      <td className="status">{trade.status}</td>
                      <td style={{ color: pnlColor(trade.pnl_dollars || 0) }}>
                        ${(trade.pnl_dollars || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <div className="lab-info">
        <h4>Shadow Lab - Testing Environment</h4>
        <ul>
          <li>Authority: <strong>ZERO</strong> (hard-locked)</li>
          <li>Live Orders: <strong>OFF</strong> (Market Replay only)</li>
          <li>Broker Orders: <strong>NONE</strong> (Paper trading)</li>
          <li>Purpose: Test strategies against historical NinjaTrader Playback data</li>
          <li>Approval: Strategies must exceed baseline to promote to Paper → Guardian → (Future) Live</li>
        </ul>
      </div>
    </div>
  );
};

export default ShadowLab;
