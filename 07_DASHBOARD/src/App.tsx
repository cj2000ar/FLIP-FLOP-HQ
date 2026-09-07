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
import './fonts.css';
import './brand.css';
import './styles.css';

/**
 * FlipFlop HQ Phase 2 UI Application
 * Authority: ZERO (hard-locked, immutable)
 * Live: OFF (paper-only, no real orders)
 * Read-only operational dashboard
 */

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

  // Simulate truth-age refresh (every 5 seconds)
  useEffect(() => {
    const refreshInterval = setInterval(() => {
      setTruthBar((prev) => ({
        ...prev,
        age_seconds: Math.min(prev.age_seconds + 5, 300),
        warning_level:
          prev.age_seconds + 5 < 10 ? 'fresh' : prev.age_seconds + 5 < 30 ? 'warning' : 'stale',
      }));
    }, 5000);

    return () => clearInterval(refreshInterval);
  }, []);

  // Check for stale condition every 2 seconds
  useEffect(() => {
    const staleCheckInterval = setInterval(() => {
      if (truthBar.age_seconds > 30) {
        // Data is stale - this triggers the modal overlay
      }
    }, 2000);

    return () => clearInterval(staleCheckInterval);
  }, [truthBar.age_seconds]);

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
    // Reset truth-age to fresh
    setTruthBar((prev) => ({
      ...prev,
      age_seconds: 0,
      is_fresh: true,
      warning_level: 'fresh',
    }));

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
