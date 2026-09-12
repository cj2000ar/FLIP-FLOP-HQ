/**
 * Monitor tab — mounts the real-time monitoring dashboard against private_read_api.
 * Resolves a *validated* fencing token through labApiClient first (a stored token
 * can be stale after an API restart), so the WebSocket and the polling hooks carry
 * credentials the API currently accepts. Authority: ZERO, read-only.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { RealtimeMonitoringDashboard } from './RealtimeMonitoringDashboard';
import { API_BASE, MACHINE_ID, apiGet, getFencingToken, resetToken } from '../labApiClient';

const WS_URL = `${API_BASE.replace(/^http/, 'ws')}/ws`;
const REBOOTSTRAP_COOLDOWN_MS = 15_000;

export default function MonitorPage() {
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lastBootstrap = useRef(0);

  const bootstrap = useCallback(async () => {
    lastBootstrap.current = Date.now();
    setError(null);
    try {
      // apiGet retries once with a fresh token on 401/403, so the token we read after is live.
      await apiGet(`/heartbeat/${encodeURIComponent(MACHINE_ID)}/freshness`);
      setToken(await getFencingToken());
    } catch (err: unknown) {
      setToken(null);
      setError(err instanceof Error ? err.message : 'Token bootstrap failed');
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  // The dashboard reports auth/connection failures here; refresh credentials, throttled.
  const handleAuthError = useCallback(
    (msg: string) => {
      if (Date.now() - lastBootstrap.current < REBOOTSTRAP_COOLDOWN_MS) return;
      console.warn('[monitor] re-bootstrapping credentials:', msg);
      resetToken();
      void bootstrap();
    },
    [bootstrap]
  );

  if (error) {
    return (
      <div className="hq-panel lab-card" style={{ borderColor: 'var(--brand-red-ink)', padding: 'var(--spacing-4)' }}>
        <p>
          <strong>Monitor unavailable:</strong> {error}
        </p>
        <p style={{ color: 'var(--hq-muted-2)' }}>API expected at {API_BASE}.</p>
        <button
          type="button"
          onClick={() => {
            resetToken();
            void bootstrap();
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="lab-empty" style={{ padding: 'var(--spacing-4)' }}>
        <p>Connecting to monitoring feed...</p>
      </div>
    );
  }

  return (
    <RealtimeMonitoringDashboard
      key={token}
      apiBaseUrl={API_BASE}
      wsUrl={WS_URL}
      machineId={MACHINE_ID}
      fencingToken={token}
      onAuthError={handleAuthError}
    />
  );
}
