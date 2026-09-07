import React from 'react';
import { HealthIndicatorState } from '../types';

/**
 * HealthIndicator - Machine health metrics
 * Displays: fencing_epoch, heartbeat_age, anomaly flags
 */

interface HealthIndicatorProps {
  health: HealthIndicatorState;
  isAdmin?: boolean;
}

export const HealthIndicator: React.FC<HealthIndicatorProps> = ({ health, isAdmin = false }) => {
  const getHealthStatus = (): 'healthy' | 'degraded' | 'critical' => {
    if (health.heartbeat_age_seconds > 60 || health.clock_offset_ms > 5000) {
      return 'critical';
    }
    if (health.heartbeat_age_seconds > 30 || health.clock_offset_ms > 2000) {
      return 'degraded';
    }
    return 'healthy';
  };

  const getHealthStatusClass = (): string => {
    const status = getHealthStatus();
    return `health-status-${status}`;
  };

  const getHealthLabel = (): string => {
    const status = getHealthStatus();
    switch (status) {
      case 'healthy':
        return '✓ Healthy';
      case 'degraded':
        return '⚠️ Degraded';
      case 'critical':
        return '✗ Critical';
    }
  };

  return (
    <div
      className="health-indicator"
      role="region"
      aria-label="Machine health status"
      aria-live="polite"
    >
      <div
        style={{
          fontSize: 'var(--font-size-lg)',
          fontWeight: 'var(--font-weight-bold)',
          marginBottom: 'var(--spacing-4)',
          paddingBottom: 'var(--spacing-3)',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        HP Machine Health
      </div>

      <div className="health-metric">
        <div className="health-metric-label">Status</div>
        <div className={`health-metric-value ${getHealthStatusClass()}`}>
          {getHealthLabel()}
        </div>
      </div>

      <div className="health-metric">
        <div className="health-metric-label">Heartbeat Age</div>
        <div className="health-metric-value">{health.heartbeat_age_seconds}s</div>
      </div>

      <div className="health-metric">
        <div className="health-metric-label">Clock Offset</div>
        <div className="health-metric-value">{health.clock_offset_ms}ms</div>
      </div>

      <div className="health-metric">
        <div className="health-metric-label">Fencing Token</div>
        <div
          className="health-metric-value"
          style={{
            color: health.fencing_token_valid
              ? 'var(--color-pass-green)'
              : 'var(--color-blocked-red)',
          }}
        >
          {health.fencing_token_valid ? '✓ Valid' : '✗ Invalid'}
        </div>
      </div>

      <div className="health-metric">
        <div className="health-metric-label">Restart Detected</div>
        <div
          className="health-metric-value"
          style={{
            color: health.restart_detected
              ? 'var(--color-warning-yellow)'
              : 'var(--color-pass-green)',
          }}
        >
          {health.restart_detected ? '⚠️ Yes' : '✓ No'}
        </div>
      </div>

      <div className="health-metric">
        <div className="health-metric-label">Truth Age</div>
        <div className="health-metric-value">{health.truth_age_seconds}s</div>
      </div>

      {isAdmin && (
        <div
          style={{
            marginTop: 'var(--spacing-4)',
            padding: 'var(--spacing-4)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderRadius: '6px',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-low-blue)',
          }}
          role="complementary"
          aria-label="Admin information"
        >
          Admin View: Machine role is RED_DRAGON. Heartbeat freshness &lt; 60s required. Clock sync
          &lt; 5s required. Fencing token prevents unauthorized promotion.
        </div>
      )}
    </div>
  );
};

export default HealthIndicator;
