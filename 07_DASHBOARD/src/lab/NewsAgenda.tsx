import { useState, useEffect } from 'react';
import Badge from './Badge';
import { AGENDA_CONTRACT, AGENDA_FEEDS, type AgendaSlot } from './labData';
import { API_BASE, API_HEADERS } from '../labApiClient';

const FIELDS = ['Actual', 'Forecast', 'Previous', 'Revision', 'NQ response', 'Signals', 'CONTROL result'];

export default function NewsAgenda() {
  const [events, setEvents] = useState<AgendaSlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(`${API_BASE}/agenda/events`, { headers: API_HEADERS });

        if (res.status === 401 || res.status === 403) {
          setError('Authentication required. Please refresh your session.');
          return;
        }

        if (!res.ok) {
          throw new Error(`Failed to fetch agenda events: ${res.statusText}`);
        }

        const data = await res.json();
        setEvents(data.events || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load agenda events');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <section role="region" aria-label="News Agenda" className="lab-grid" style={{ gap: 'var(--spacing-5)' }}>
      <div className="lab-head" style={{ gridColumn: '1 / -1' }}>
        <span className="hq-overline">News Agenda</span>
        <h2>Not a calendar. A behavior record.</h2>
        <p>
          Lives in Calendar. Joins each release with what NQ/MNQ did and what the system emitted, blocked or skipped — so
          we can ask how CONTROL behaves on CPI, NFP, FOMC, PPI or retail-sales days without turning news into a
          retrospective excuse.
        </p>
      </div>

      <div className="hq-panel lab-verdict" style={{ gridColumn: '1 / -1' }}>
        <div>
          <span className="hq-overline">Feed status</span>
          <strong>No verified capture connected</strong>
        </div>
        <Badge status="NOT_CONNECTED" />
      </div>

      {loading && (
        <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
          <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
            <p>Loading agenda events...</p>
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
        <div className="hq-panel lab-table-wrap" style={{ gridColumn: '1 / -1' }}>
          <table className="lab-table" aria-label="Event slots">
            <thead>
              <tr>
                <th>Event</th>
                <th>Importance</th>
                {FIELDS.map((f) => (
                  <th key={f}>{f}</th>
                ))}
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {events.map((s) => (
              <tr key={s.code}>
                <td>
                  {s.code}
                  <div style={{ fontWeight: 400, color: 'var(--hq-muted-2)', fontSize: 11 }}>{s.name}</div>
                </td>
                <td>
                  <Badge status={s.importance} tone={s.importance === 'HIGH' ? 'warn' : 'muted'} />
                </td>
                {FIELDS.map((f) => (
                  <td key={f} style={{ fontFamily: 'var(--font-geist-mono)', color: 'var(--hq-muted-2)' }}>
                    —
                  </td>
                ))}
                <td>
                  <Badge status={s.status} />
                </td>
              </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="hq-panel lab-card">
        <h3>Per-event contract</h3>
        <ul>
          {AGENDA_CONTRACT.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </div>

      <div className="hq-panel lab-card">
        <h3>Sources</h3>
        <div className="lab-kv">
          {AGENDA_FEEDS.map((f) => (
            <div key={f.id}>
              <span>
                {f.title}
                <div style={{ fontSize: 11, color: 'var(--hq-muted-2)' }}>{f.detail}</div>
              </span>
              <span>
                <Badge status={f.status} tone={f.tone} />
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
