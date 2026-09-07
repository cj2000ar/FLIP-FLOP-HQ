import { useState, useEffect } from 'react';
import Badge from './Badge';
import { GUARDIAN_CORE, type LedgerEntry } from './labData';

const API_BASE = 'http://localhost:8000';
const apiHeaders = { 'Machine-ID': 'dashboard-test', 'Fencing-Token': 'test-token' };

export default function GuardianLedgers() {
  const [wounds, setWounds] = useState<LedgerEntry[]>([]);
  const [calibration, setCalibration] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [woundsRes, calibrationRes] = await Promise.all([
          fetch(`${API_BASE}/guardian/wounds`, { headers: apiHeaders }),
          fetch(`${API_BASE}/guardian/calibration`, { headers: apiHeaders }),
        ]);

        if (woundsRes.status === 401 || woundsRes.status === 403 || calibrationRes.status === 401 || calibrationRes.status === 403) {
          setError('Authentication required. Please refresh your session.');
          return;
        }

        if (!woundsRes.ok) {
          throw new Error(`Failed to fetch wounds: ${woundsRes.statusText}`);
        }

        if (!calibrationRes.ok) {
          throw new Error(`Failed to fetch calibration: ${calibrationRes.statusText}`);
        }

        const woundsData = await woundsRes.json();
        const calibrationData = await calibrationRes.json();

        setWounds(woundsData.wounds || []);
        setCalibration(calibrationData.calibration || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load guardian data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <section role="region" aria-label="Guardian Ledgers" className="lab-grid" style={{ gap: 'var(--spacing-5)' }}>
      <div className="lab-head" style={{ gridColumn: '1 / -1' }}>
        <span className="hq-overline">Guardian · memory · trust</span>
        <h2>Every decision reconstructible.</h2>
        <p>
          Decision Cartridges, Calibration Ledger, Bitemporal Event Store, Wound Registry and Override Ledger. The system
          builds scar tissue: each reproduced incident becomes a permanent scenario with fixed inputs and expected result.
        </p>
      </div>

      <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
        <h3>Trust architecture</h3>
        <div className="lab-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 8 }}>
          {GUARDIAN_CORE.map((g) => (
            <div key={g.id} className="lab-ticket">
              <strong style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                {g.title}
                <Badge status={g.status} tone={g.tone} />
              </strong>
              <span>{g.detail}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="hq-panel lab-card">
        <h3>Decision Cartridges</h3>
        <div className="lab-kv">
          <div>
            <span>Forward cartridges</span>
            <span>0</span>
          </div>
          <div>
            <span>Replay sessions on record</span>
            <span>12 + 23 (SESSION_E2_PROVEN)</span>
          </div>
          <div>
            <span>FIRST_TOUCH native vs V03</span>
            <span>DELTA_MS = 0</span>
          </div>
          <div>
            <span>Nightly bit-identical proof</span>
            <span>NOT_PROVEN forward</span>
          </div>
        </div>
      </div>

      <div className="hq-panel lab-card">
        <h3>Bitemporal query</h3>
        <div className="lab-kv">
          <div>
            <span>event_time</span>
            <span>when it happened</span>
          </div>
          <div>
            <span>knowledge_time</span>
            <span>when HQ learned it</span>
          </div>
          <div>
            <span>Late data</span>
            <span>keeps both; past never rewritten</span>
          </div>
        </div>
        <p>Read-only surface. Query execution requires the private read API (not connected in this build).</p>
      </div>

      {loading && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
          <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
            <p>Loading guardian data...</p>
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
          <div className="hq-panel lab-card">
            <h3>Calibration Ledger</h3>
            <div className="lab-kv">
              {calibration.map((c) => (
                <div key={c.id}>
                  <span>
                    {c.title}
                    <div style={{ fontSize: 11, color: 'var(--hq-muted-2)' }}>{c.detail}</div>
                  </span>
                  <span>
                    <Badge status={c.status} tone={c.tone} />
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="hq-panel lab-card">
            <h3>Override Ledger</h3>
            <p>No manual overrides recorded.</p>
            <div className="lab-chips">
              {['who', 'reason', 'state before', 'state after', 'outcome'].map((f) => (
                <span key={f} className="lab-chip">
                  {f}
                </span>
              ))}
            </div>
          </div>

          <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
            <h3>
              Wound Registry
              <Badge status={`${wounds.length} WOUNDS`} tone="muted" />
            </h3>
            <div className="lab-table-wrap">
              <table className="lab-table" aria-label="Wound Registry">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Wound</th>
                    <th>Detail</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {wounds.map((w) => (
                    <tr key={w.id}>
                      <td style={{ fontFamily: 'var(--font-geist-mono)' }}>{w.id}</td>
                      <td style={{ color: 'var(--hq-fg)' }}>{w.title}</td>
                      <td>{w.detail}</td>
                      <td>
                        <Badge status={w.status} tone={w.tone} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
