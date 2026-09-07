import { useState, useEffect } from 'react';
import Badge from './Badge';
import { QUEUE_STATES, type QueueItem } from './labData';
import { API_BASE, API_HEADERS } from '../labApiClient';

export default function ShadowQueue() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(`${API_BASE}/queue`, { headers: API_HEADERS });

        if (res.status === 401 || res.status === 403) {
          setError('Authentication required. Please refresh your session.');
          return;
        }

        if (!res.ok) {
          throw new Error(`Failed to fetch queue: ${res.statusText}`);
        }

        const data = await res.json();
        setQueue(data.queue || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load queue');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <section role="region" aria-label="SHADOW Injection Queue" className="lab-grid" style={{ gap: 'var(--spacing-5)' }}>
      <div className="lab-head" style={{ gridColumn: '1 / -1' }}>
        <span className="hq-overline">SHADOW Injection Queue</span>
        <h2>Every idea visible. Every block explained.</h2>
        <p>
          Pipeline from capture to promotion review. "Build ready" means ready to prepare a SHADOW challenger only — not
          CONTROL-ready, not LIVE-ready. In SHADOW the goal is to destroy an idea cleanly, not to confirm a favorite.
        </p>
      </div>

      {loading && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
          <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
            <p>Loading queue...</p>
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

      {!loading && !error && (
        <div className="lab-kanban" style={{ gridColumn: '1 / -1' }} aria-label="Queue states">
          {QUEUE_STATES.map((state) => {
            const tickets = queue.filter((q) => q.state === state);
          return (
            <div key={state} className="lab-col" role="list" aria-label={state}>
              <div className="lab-col-head">
                <Badge status={state} />
                <b>{tickets.length}</b>
              </div>
              {tickets.length === 0 && <div className="lab-empty">0 items</div>}
              {tickets.map((t) => (
                <div key={t.id} className="lab-ticket" role="listitem">
                  <strong>{t.title}</strong>
                  <span>{t.why}</span>
                </div>
              ))}
            </div>
            );
          })}
        </div>
      )}

      <div className="hq-panel lab-card">
        <h3>SHADOW counts everything</h3>
        <ul>
          <li>trades lost and won · signals omitted · skipped winners</li>
          <li>commissions and slippage · stability by session and regime</li>
          <li>parameter sensitivity · drawdown and trajectory risk</li>
          <li>information leakage · single-period dependence</li>
          <li>replay vs SIM vs real-fill differences</li>
        </ul>
      </div>

      <div className="hq-panel lab-card">
        <h3>Shadow Twin Trade</h3>
        <p>
          When real risk does not fit a small budget, Guardian blocks LIVE and the system can create an identical Shadow
          Twin Trade under hypothetical budgets. Rule: preserve the learning, never force the trade.
        </p>
      </div>
    </section>
  );
}
