import React, { useEffect, useState } from 'react';
import ScreenComponent from './components/ScreenComponent';
import {
  GuardianStateSnapshot,
  TruthBarState,
  HealthIndicatorState,
  BatchStatusSnapshot,
  AlertRecord,
  ArchiveEntry,
  createMockGuardianState,
  createMockTruthBar,
  createMockHealthIndicator,
  createMockBatchStatus,
  createMockArchiveEntries,
} from './types';
import { apiGet, MACHINE_ID } from './labApiClient';
import './fonts.css';
import './brand.css';
import './styles.css';

/**
 * FlipFlop HQ Phase 2 UI Application
 * Authority: ZERO (hard-locked, immutable)
 * Live: OFF (paper-only, no real orders)
 * Read-only operational dashboard
 */

interface ApiFreshness {
  is_fresh: boolean;
  age_seconds: number;
  warning_level: 'fresh' | 'warning' | 'stale';
  last_update: string | null;
  stale_since: string | null;
}

const App: React.FC = () => {
  const [guardianState, setGuardianState] = useState<GuardianStateSnapshot>(
    createMockGuardianState()
  );
  const [truthBar, setTruthBar] = useState<TruthBarState>(createMockTruthBar(5));
  const [healthIndicator, setHealthIndicator] = useState<HealthIndicatorState>(
    createMockHealthIndicator()
  );
  const [batchStatus, setBatchStatus] = useState<BatchStatusSnapshot>(createMockBatchStatus());
  const [alerts, setAlerts] = useState<AlertRecord[]>(batchStatus.alert_array);
  const [archives] = useState<ArchiveEntry[]>(createMockArchiveEntries());
  const [isAdmin, setIsAdmin] = useState(false);

  // Truth-age from the API heartbeat (every 5 seconds). Unreachable API = stale.
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const f = await apiGet<ApiFreshness>(`/heartbeat/${encodeURIComponent(MACHINE_ID)}/freshness`);
        if (cancelled) return;
        setTruthBar((prev) => ({
          ...prev,
          is_fresh: f.is_fresh,
          age_seconds: f.age_seconds < 0 ? 999 : f.age_seconds,
          warning_level: f.warning_level,
          last_update: f.last_update ? Date.parse(f.last_update) : prev.last_update,
          stale_since: f.stale_since ? Date.parse(f.stale_since) : undefined,
        }));
      } catch {
        if (cancelled) return;
        setTruthBar((prev) => ({
          ...prev,
          is_fresh: false,
          age_seconds: Math.min(prev.age_seconds + 5, 999),
          warning_level: 'stale',
        }));
      }
    };
    void poll();
    const refreshInterval = setInterval(poll, 5000);
    return () => {
      cancelled = true;
      clearInterval(refreshInterval);
    };
  }, []);

  // Keyboard shortcut: toggle admin mode (Ctrl+Shift+A)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'A') {
        setIsAdmin((prev) => !prev);
      }
      // Refresh on Ctrl+R
      if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        handleRefresh();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleRefresh = () => {
    // Re-touch the API so its heartbeat for this machine is fresh; the poll picks it up.
    void apiGet(`/heartbeat/${encodeURIComponent(MACHINE_ID)}/freshness`).catch(() => undefined);

    // Reload all data (in real app, would fetch from API)
    setGuardianState(createMockGuardianState());
    setHealthIndicator(createMockHealthIndicator());
    const newBatch = createMockBatchStatus();
    setBatchStatus(newBatch);
    setAlerts(newBatch.alert_array);
  };

  const handleAlertDismiss = (alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.alert_id !== alertId));
  };

  return (
    <div
      style={{
        width: '100%',
        height: '100vh',
        backgroundColor: 'var(--color-bg-primary)',
        color: 'var(--color-text-primary)',
      }}
    >
      <ScreenComponent
        guardianState={guardianState}
        truthBar={truthBar}
        healthIndicator={healthIndicator}
        batchStatus={batchStatus}
        alerts={alerts}
        archives={archives}
        onAlertDismiss={handleAlertDismiss}
        onRefresh={handleRefresh}
        isAdmin={isAdmin}
      />

      {/* Development info (remove in production) */}
      {process.env.NODE_ENV === 'development' && (
        <div
          className="dev-info"
          style={{
            position: 'fixed',
            bottom: '1rem',
            right: '1rem',
            fontSize: '0.75rem',
            color: 'var(--color-text-secondary)',
            backgroundColor: 'var(--color-bg-secondary)',
            padding: '0.5rem',
            borderRadius: '4px',
            border: '1px solid var(--color-border)',
            maxWidth: '200px',
          }}
        >
          <div>Admin: {isAdmin ? 'ON' : 'OFF'} (Ctrl+Shift+A)</div>
          <div>Refresh: Ctrl+R</div>
          <div>Truth Age: {truthBar.age_seconds}s</div>
          <div>Status: {truthBar.warning_level.toUpperCase()}</div>
        </div>
      )}
    </div>
  );
};

export default App;
