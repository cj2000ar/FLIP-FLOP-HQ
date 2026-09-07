import React, { useState, useEffect, ReactNode } from 'react';
import '../lab/lab.css';
import { AUTHORITY_BANNER } from '../lab/labData';
import StrategyVault from '../lab/StrategyVault';
import StrategyArena from '../lab/StrategyArena';
import ExperimentLedger from '../lab/ExperimentLedger';
import ShadowQueue from '../lab/ShadowQueue';
import NewsAgenda from '../lab/NewsAgenda';
import GuardianLedgers from '../lab/GuardianLedgers';
import PromotionGate from '../lab/PromotionGate';
import QuantumLab from '../lab/QuantumLab';

const API_BASE = 'http://localhost:8000';

const apiHeaders = {
  'Machine-ID': 'dashboard-test',
  'Fencing-Token': 'test-token',
};

class ErrorBoundary extends React.Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    console.error('Lab error:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="hq-panel lab-card" style={{ borderColor: 'var(--brand-red-ink)' }}>
          <div style={{ color: 'var(--brand-red-ink)' }}>
            <p><strong>Error:</strong> {this.state.error?.message || 'An error occurred'}</p>
            <button onClick={() => window.location.reload()}>Reload page</button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export const LAB_SECTIONS = [
  { id: 'vault', label: 'Vault', Component: StrategyVault },
  { id: 'arena', label: 'Arena', Component: StrategyArena },
  { id: 'experiments', label: 'Experiments', Component: ExperimentLedger },
  { id: 'queue', label: 'Queue', Component: ShadowQueue },
  { id: 'agenda', label: 'Agenda', Component: NewsAgenda },
  { id: 'guardian', label: 'Guardian', Component: GuardianLedgers },
  { id: 'promotion', label: 'Promotion', Component: PromotionGate },
  { id: 'quantum', label: 'Quantum', Component: QuantumLab },
] as const;

export type LabSectionId = (typeof LAB_SECTIONS)[number]['id'];

function LabContent({ initialSection = 'vault' }: { initialSection?: LabSectionId }) {
  const [section, setSection] = useState<LabSectionId>(initialSection);
  const [globalLoading, setGlobalLoading] = useState(true);

  useEffect(() => {
    const prefetchAll = async () => {
      try {
        setGlobalLoading(true);
        // Parallel pre-fetch all API endpoints
        await Promise.all([
          fetch(`${API_BASE}/vault/items`, { headers: apiHeaders }),
          fetch(`${API_BASE}/vault/families`, { headers: apiHeaders }),
          fetch(`${API_BASE}/experiments`, { headers: apiHeaders }),
          fetch(`${API_BASE}/queue`, { headers: apiHeaders }),
          fetch(`${API_BASE}/agenda/events`, { headers: apiHeaders }),
          fetch(`${API_BASE}/guardian/wounds`, { headers: apiHeaders }),
          fetch(`${API_BASE}/guardian/calibration`, { headers: apiHeaders }),
        ]);
      } catch (err) {
        // Silently fail pre-fetch - individual components will handle errors
        console.debug('Pre-fetch completed with some errors (handled by components)');
      } finally {
        setGlobalLoading(false);
      }
    };

    prefetchAll();
  }, []);

  const active = LAB_SECTIONS.find((s) => s.id === section) ?? LAB_SECTIONS[0];
  const Active = active.Component;

  return (
    <div className="lab" role="main" aria-label="Research lab workspace">
      <div className="lab-banner" role="status">
        <span>{AUTHORITY_BANNER}</span>
        <span>Lab is a read-only research surface. Nothing here submits, cancels, flattens, promotes or activates.</span>
      </div>

      <nav className="lab-subnav" aria-label="Lab sections">
        {LAB_SECTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            aria-pressed={section === s.id}
            onClick={() => setSection(s.id)}
            disabled={globalLoading}
          >
            {s.label}
          </button>
        ))}
      </nav>

      {globalLoading && (
        <div className="hq-panel lab-card" style={{ margin: 'var(--spacing-5)' }}>
          <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
            <p>Loading Lab...</p>
          </div>
        </div>
      )}

      {!globalLoading && <Active />}
    </div>
  );
}

export default function Lab({ initialSection = 'vault' }: { initialSection?: LabSectionId }) {
  return (
    <ErrorBoundary>
      <LabContent initialSection={initialSection} />
    </ErrorBoundary>
  );
}
