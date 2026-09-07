import { useState, useEffect } from 'react';
import Badge from './Badge';
import { type Experiment } from './labData';

const API_BASE = 'http://localhost:8000';
const apiHeaders = { 'Machine-ID': 'dashboard-test', 'Fencing-Token': 'test-token' };

export default function ExperimentLedger() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(`${API_BASE}/experiments`, { headers: apiHeaders });

        if (res.status === 401 || res.status === 403) {
          setError('Authentication required. Please refresh your session.');
          return;
        }

        if (!res.ok) {
          throw new Error(`Failed to fetch experiments: ${res.statusText}`);
        }

        const data = await res.json();
        setExperiments(data.experiments || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load experiments');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const preRegistered = experiments.filter((e) => e.status === 'PRE_REGISTERED').length;
  const closed = experiments.filter((e) => e.status === 'FAILED' || e.status === 'REJECTED').length;

  return (
    <section role="region" aria-label="Experiment Ledger" className="lab-grid" style={{ gap: 'var(--spacing-5)' }}>
      <div className="lab-head" style={{ gridColumn: '1 / -1' }}>
        <span className="hq-overline">Experiment Ledger</span>
        <h2>Pre-registered. Frozen. Never deleted.</h2>
        <p>
          Hypothesis, parameters, dataset role, runs, results, costs, rejection reason and next gate. An entry cannot be
          edited once registered. Failures stay visible so the same idea cannot be re-tested as if it were new.
        </p>
      </div>

      {loading && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
          <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
            <p>Loading experiments...</p>
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
        <>
          <div className="hq-panel lab-verdict" style={{ gridColumn: '1 / -1' }}>
            <div>
              <span className="hq-overline">Ledger state</span>
              <strong>
                {experiments.length} entries · {preRegistered} pre-registered · {closed} closed
              </strong>
            </div>
            <div className="lab-chips">
              <Badge status="PRE_REGISTERED" />
              <Badge status="COMPLETED" />
              <Badge status="FAILED" />
              <Badge status="REJECTED" />
            </div>
          </div>

          <div className="hq-panel lab-table-wrap" style={{ gridColumn: '1 / -1' }}>
            <table className="lab-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Experiment</th>
                  <th>Hypothesis</th>
                  <th>Frozen parameters</th>
                  <th>Dataset role</th>
                  <th>Runs</th>
                  <th>Status</th>
                  <th>Result</th>
                  <th>Next gate</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((e) => (
              <tr key={e.id}>
                <td style={{ fontFamily: 'var(--font-geist-mono)' }}>{e.id}</td>
                <td style={{ color: 'var(--hq-fg)', minWidth: 160 }}>{e.name}</td>
                <td style={{ minWidth: 220 }}>{e.hypothesis}</td>
                <td style={{ minWidth: 220 }}>{e.parameters}</td>
                <td>
                  <Badge status={e.datasetRole} tone={e.datasetRole === 'HOLDOUT' ? 'bad' : 'muted'} />
                </td>
                <td style={{ fontFamily: 'var(--font-geist-mono)' }}>{e.runs}</td>
                <td>
                  <Badge status={e.status} />
                </td>
                <td style={{ minWidth: 200 }}>
                  {e.result}
                  {e.rejectionReason && (
                    <div style={{ marginTop: 6, color: 'var(--brand-red-ink)' }}>{e.rejectionReason}</div>
                  )}
                </td>
                <td style={{ minWidth: 180 }}>{e.nextGate}</td>
              </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
