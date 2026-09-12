import { useState, useEffect } from 'react';
import Badge from './Badge';
import { type PromotionGateItem } from './labData';
import { apiGet } from '../labApiClient';

const CANDIDATE = 'rr500-control';

export default function PromotionGate() {
  const [gates, setGates] = useState<PromotionGateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        setGates(await apiGet<PromotionGateItem[]>(`/promotion/gates?candidate=${CANDIDATE}`));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load promotion gates');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const pass = gates.filter((g) => g.status === 'PASS').length;
  const blocking = gates.filter((g) => g.status === 'NOT_PROVEN').map((g) => g.id);
  const verdict = blocking.length === 0 ? 'READY FOR REVIEW' : 'BLOCKED';

  return (
    <section role="region" aria-label="Promotion Gate" className="lab-grid" style={{ gap: 'var(--spacing-5)' }}>
      <div className="lab-head" style={{ gridColumn: '1 / -1' }}>
        <span className="hq-overline">Promotion Gate</span>
        <h2>Sixteen gates. All must pass.</h2>
        <p>
          Formal review before a challenger can replace CONTROL or become LIVE-eligible. Owner approval is the last gate
          and cannot override failed integrity or safety gates.
        </p>
      </div>

      {loading && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
          <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
            <p>Loading promotion gates...</p>
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
          <div className="hq-panel lab-verdict" style={{ gridColumn: '1 / -1', borderColor: '#dd281c55' }}>
            <div style={{ display: 'grid', gap: 6, flex: 1, minWidth: 220 }}>
              <span className="hq-overline">Candidate · RR500_CONTROL lineage</span>
              <strong style={{ color: 'var(--brand-red-ink)' }}>{verdict}</strong>
              <div className="lab-progress" aria-label={`${pass} of ${gates.length} gates pass`}>
                <i style={{ width: `${(pass / gates.length) * 100}%` }} />
              </div>
              <span style={{ fontSize: 12, color: 'var(--hq-muted)' }}>
                {pass} / {gates.length} PASS · blocking gates: {blocking.join(', ')}
              </span>
            </div>
            <div className="lab-chips">
              <Badge status="LIVE_AUTHORITY=BLOCKED" />
              <Badge status="BROKER_ORDERS=NONE" tone="bad" />
            </div>
          </div>

          <div className="hq-panel lab-table-wrap" style={{ gridColumn: '1 / -1' }}>
            <table className="lab-table" aria-label="Promotion gate checklist">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Gate</th>
                  <th>Requirement</th>
                  <th>Status</th>
                  <th>Evidence on record</th>
                </tr>
              </thead>
              <tbody>
                {gates.map((g) => (
                  <tr key={g.id}>
                    <td style={{ fontFamily: 'var(--font-geist-mono)' }}>{g.id}</td>
                    <td style={{ color: 'var(--hq-fg)' }}>{g.name}</td>
                    <td style={{ minWidth: 220 }}>{g.requirement}</td>
                    <td>
                      <Badge status={g.status} />
                    </td>
                    <td style={{ minWidth: 240 }}>{g.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
            <h3>Owner approval</h3>
            <p>
              Final sign-off is recorded in the Override Ledger with reason and outcome. It cannot override gates 1–15. No
              interface, AI, file or old result grants LIVE authority by itself.
            </p>
          </div>
        </>
      )}
    </section>
  );
}
