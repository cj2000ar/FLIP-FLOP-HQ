import { useState, useEffect } from 'react';
import Badge from './Badge';
import { type ArenaEntry } from './labData';
import { apiGet } from '../labApiClient';

export default function StrategyArena() {
  const [arena, setArena] = useState<ArenaEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        setArena(await apiGet<ArenaEntry[]>('/arena/strategies'));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load arena data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const control = arena.find((a) => a.state === 'CONTROL');
  const challengers = arena.filter((a) => a.state !== 'CONTROL');

  return (
    <section role="region" aria-label="Strategy Arena" className="lab-grid" style={{ gap: 'var(--spacing-5)' }}>
      <div className="lab-head" style={{ gridColumn: '1 / -1' }}>
        <span className="hq-overline">Strategy Arena</span>
        <h2>CONTROL vs challengers.</h2>
        <p>
          Identical data scope, risk model, costs and reporting. Not ranked by P&amp;L alone: robustness, drawdown,
          leakage, determinism, skipped winners, regime dependence and execution realism weigh equally. CONTROL is frozen;
          promotion is formal and never activates LIVE.
        </p>
      </div>

      {loading && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
          <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
            <p>Loading arena data...</p>
          </div>
        </div>
      )}

      {error && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1', borderColor: 'var(--brand-red-ink)' }}>
          <div style={{ color: 'var(--brand-red-ink)', padding: 'var(--spacing-4)' }}>
            <p><strong>Error:</strong> {error}</p>
            <button onClick={() => window.location.reload()} style={{ marginTop: 'var(--spacing-2)' }}>
              Retry
            </button>
          </div>
        </div>
      )}

      {!loading && !error && control && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1', borderColor: '#2a7d3c55' }}>
          <h3>
            {control.name}
            <Badge status={control.state} />
          </h3>
          <p>
            <b style={{ color: 'var(--hq-fg)' }}>{control.version}</b> — {control.summary}
          </p>
          <div className="lab-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 8 }}>
            {control.metrics.map((m) => (
              <div key={m.label} className="lab-ticket">
                <span>{m.label}</span>
                <strong style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 15 }}>{m.value}</strong>
              </div>
            ))}
          </div>
          <p>{control.note}</p>
        </div>
      )}

      {!loading && !error && challengers.map((c) => (
        <div key={c.id} className="hq-panel lab-card">
          <h3>
            {c.name}
            <Badge status={c.state} />
          </h3>
          <p>
            <b style={{ color: 'var(--hq-fg)' }}>{c.version}</b> — {c.summary}
          </p>
          <div className="lab-kv">
            {c.metrics.map((m) => (
              <div key={m.label}>
                <span>{m.label}</span>
                <span>{m.value}</span>
              </div>
            ))}
          </div>
          <p>{c.note}</p>
        </div>
      ))}

      <div className="hq-panel lab-card">
        <h3>Promotion law</h3>
        <ul>
          <li>A challenger becomes CONTROL only by formal promotion. The prior CONTROL stays immutable and recoverable.</li>
          <li>Promotion to CONTROL does not activate LIVE. A strategy may be approved only for research, replay, SHADOW or SIM.</li>
          <li>Consumed holdouts are never recycled as unseen. Failed results are never deleted.</li>
        </ul>
      </div>
    </section>
  );
}
