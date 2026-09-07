import { useState, useEffect } from 'react';
import Badge from './Badge';
import { MARKETS, type VaultItem, type StrategyFamily } from './labData';
import { API_BASE, API_HEADERS } from '../labApiClient';

const ALL = 'ALL';

export default function StrategyVault() {
  const [family, setFamily] = useState<string>(ALL);
  const [items, setItems] = useState<VaultItem[]>([]);
  const [families, setFamilies] = useState<StrategyFamily[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [vaultRes, familiesRes] = await Promise.all([
          fetch(`${API_BASE}/vault/items${family !== ALL ? `?family=${family}` : ''}`, { headers: API_HEADERS, signal: controller.signal }),
          fetch(`${API_BASE}/vault/families`, { headers: API_HEADERS, signal: controller.signal }),
        ]);

        if (vaultRes.status === 401 || vaultRes.status === 403) {
          setError('Authentication required. Please refresh your session.');
          return;
        }

        if (!vaultRes.ok) {
          throw new Error(`Failed to fetch vault items: ${vaultRes.statusText}`);
        }

        if (!familiesRes.ok) {
          throw new Error(`Failed to fetch families: ${familiesRes.statusText}`);
        }

        const vaultData = await vaultRes.json();
        const familiesData = await familiesRes.json();

        setItems(vaultData.items || []);
        setFamilies(familiesData.families || []);
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    return () => controller.abort();
  }, [family]);

  const familyList = families.map((f) => f.id).sort();
  const filteredItems = family === ALL ? items : items.filter((v) => v.family.includes(family));

  return (
    <section role="region" aria-label="Strategy Vault" className="lab-grid" style={{ gap: 'var(--spacing-5)' }}>
      <div className="lab-head" style={{ gridColumn: '1 / -1' }}>
        <span className="hq-overline">Strategy Vault</span>
        <h2>Library, not proof.</h2>
        <p>
          Videos, links, scripts and claims keep URL, capture status, rules, data needs, evidence grade and family DNA.
          Ingesting an item correctly proves nothing about a strategy and grants no authority.
        </p>
      </div>

      {loading && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
          <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
            <p>Loading vault data...</p>
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
          <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
            <h3>
              Strategy families
              <Badge status={`${families.length} FAMILIES`} tone="muted" />
            </h3>
            <div className="lab-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {families.map((f) => (
            <div key={f.id} className="lab-ticket">
              <strong>{f.name}</strong>
              <span>{f.lineage}</span>
              <div className="lab-chips">
                {f.dna.map((d) => (
                  <span key={d} className="lab-chip">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
            <h3>
              Vault items
              <span className="lab-chips" role="group" aria-label="Family filter">
                {[ALL, ...familyList].map((f) => (
              <button
                key={f}
                type="button"
                className="lab-chip"
                aria-pressed={family === f}
                onClick={() => setFamily(f)}
                style={{
                  cursor: 'pointer',
                  color: family === f ? '#fff' : undefined,
                  background: family === f ? 'var(--hq-surface-3)' : undefined,
                }}
              >
                {f}
              </button>
            ))}
          </span>
        </h3>
        <div className="lab-table-wrap">
          <table className="lab-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Source</th>
                <th>Extraction</th>
                <th>Evidence</th>
                <th>DNA</th>
                <th>Data needs</th>
              </tr>
                </thead>
                <tbody>
                  {filteredItems.map((v) => (
                <tr key={v.id}>
                  <td>
                    {v.title}
                    <div className="lab-chips" style={{ marginTop: 6 }}>
                      {v.family.map((f) => (
                        <span key={f} className="lab-chip">
                          {f}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td style={{ fontFamily: 'var(--font-geist-mono)', fontSize: 11 }}>{v.source}</td>
                  <td>
                    <Badge status={v.extraction} tone={v.extraction === 'VERIFIED' ? 'ok' : v.extraction === 'EXTRACTED' ? 'info' : 'warn'} />
                  </td>
                  <td>
                    <Badge status={v.evidence} tone={v.evidence === 'CLIP_ONLY' ? 'muted' : 'info'} />
                  </td>
                  <td>{v.dna}</td>
                  <td>{v.dataNeeds.length ? v.dataNeeds.join(' · ') : '—'}</td>
                </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      <div className="hq-panel lab-card">
        <h3>Markets</h3>
        <div className="lab-kv">
          <div>
            <span>Primary</span>
            <span>{MARKETS.primary.join(' · ')}</span>
          </div>
          <div>
            <span>High-priority expansion</span>
            <span>{MARKETS.priority.join(' · ')}</span>
          </div>
          <div>
            <span>Later</span>
            <span>{MARKETS.later.join(' · ')}</span>
          </div>
        </div>
        <p>{MARKETS.rule}</p>
      </div>

      <div className="hq-panel lab-card">
        <h3>Evidence ladder</h3>
        <div className="lab-chips">
          {['CLIP_ONLY', 'BACKTEST', 'MARKET_REPLAY', 'REALTIME_SIM', 'BROKER_AUDITED', 'SEALED_VALIDATED'].map((g, i) => (
            <span key={g} className="lab-chip">
              {i + 1} · {g}
            </span>
          ))}
        </div>
        <p>
          NinjaTrader Market Replay is ground truth for execution research. TradingView is visual support only. A clip
          never demonstrates latency, queue position, partial fills, rejects or recovery.
        </p>
      </div>
    </section>
  );
}
