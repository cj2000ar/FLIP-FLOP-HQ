import React from 'react';

const PerformanceView: React.FC = () => {
  const metrics = {
    dailyReturn: 1.24,
    monthlyReturn: 8.75,
    yearlyReturn: 24.30,
    sharpeRatio: 1.85,
    sortinoRatio: 2.41,
    maxDrawdown: 3.20,
    recoveryFactor: 4.92,
    profitFactor: 2.37,
    winRate: 62.0,
  };

  const equity = [
    { date: 'Day 1', value: 100000 },
    { date: 'Day 5', value: 101240 },
    { date: 'Day 10', value: 101875 },
    { date: 'Day 15', value: 103240 },
    { date: 'Day 20', value: 105120 },
    { date: 'Day 25', value: 107850 },
  ];

  const maxEquity = Math.max(...equity.map((e) => e.value));

  return (
    <div style={{ padding: 'var(--spacing-6)' }}>
      {/* Charts Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: 'var(--spacing-6)',
          marginBottom: 'var(--spacing-6)',
        }}
      >
        {/* Equity Curve */}
        <div
          style={{
            padding: 'var(--spacing-6)',
            background: 'var(--hq-panel-bg)',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
          }}
        >
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
            Equity Curve
          </h3>
          <div style={{ height: '200px', display: 'flex', alignItems: 'flex-end', gap: '8px', paddingRight: 'var(--spacing-3)' }}>
            {equity.map((point, idx) => {
              const heightPercent = (point.value / maxEquity) * 100;
              return (
                <div
                  key={idx}
                  style={{
                    flex: 1,
                    height: `${heightPercent}%`,
                    background: 'linear-gradient(180deg, var(--color-low-blue), var(--color-low-blue) 70%, transparent)',
                    borderRadius: '4px 4px 0 0',
                    opacity: 0.8,
                    transition: 'all 0.3s ease',
                  }}
                />
              );
            })}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'var(--spacing-3)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
            {equity.map((point) => (
              <div key={point.date}>{point.date}</div>
            ))}
          </div>
        </div>

        {/* Risk Metrics */}
        <div
          style={{
            padding: 'var(--spacing-6)',
            background: 'var(--hq-panel-bg)',
            borderRadius: '12px',
            border: '1px solid var(--color-border)',
          }}
        >
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
            Risk Metrics
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-4)' }}>
            <div>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                Max Drawdown
              </p>
              <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-fail-red)' }}>
                -{metrics.maxDrawdown}%
              </p>
            </div>

            <div>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                Recovery Factor
              </p>
              <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-pass-green)' }}>
                {metrics.recoveryFactor}x
              </p>
            </div>

            <div>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
                Win Rate
              </p>
              <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-low-blue)' }}>
                {metrics.winRate}%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: 'var(--spacing-4)',
        }}
      >
        <MetricCard label="Daily Return" value={`+${metrics.dailyReturn}%`} color="green" />
        <MetricCard label="Monthly Return" value={`+${metrics.monthlyReturn}%`} color="green" />
        <MetricCard label="Yearly Return" value={`+${metrics.yearlyReturn}%`} color="green" />
        <MetricCard label="Sharpe Ratio" value={metrics.sharpeRatio.toFixed(2)} color="blue" />
        <MetricCard label="Sortino Ratio" value={metrics.sortinoRatio.toFixed(2)} color="blue" />
        <MetricCard label="Profit Factor" value={metrics.profitFactor.toFixed(2)} color="green" />
      </div>
    </div>
  );
};

const MetricCard: React.FC<{ label: string; value: string; color: 'green' | 'blue' | 'red' }> = ({ label, value, color }) => {
  const colorMap = {
    green: 'var(--color-pass-green)',
    blue: 'var(--color-low-blue)',
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
      <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: colorMap[color] }}>{value}</p>
    </div>
  );
};

export default PerformanceView;
