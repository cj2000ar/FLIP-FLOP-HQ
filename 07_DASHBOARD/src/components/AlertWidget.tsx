import React, { useState } from 'react';
import { AlertRecord, AlertSeverity } from '../types';

/**
 * AlertWidget - Ranked alerts by severity
 * Dismissible, read-only display
 */

interface AlertWidgetProps {
  alerts: AlertRecord[];
  onDismiss?: (alertId: string) => void;
  maxVisible?: number;
}

export const AlertWidget: React.FC<AlertWidgetProps> = ({
  alerts,
  onDismiss,
  maxVisible = 10,
}) => {
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());

  const sortedAlerts = [...alerts].sort((a, b) => {
    const severityOrder: Record<AlertSeverity, number> = {
      critical: 0,
      high: 1,
      medium: 2,
      low: 3,
      info: 4,
    };
    return severityOrder[a.severity] - severityOrder[b.severity];
  });

  const visibleAlerts = sortedAlerts
    .filter((a) => !dismissedAlerts.has(a.alert_id))
    .slice(0, maxVisible);

  const handleDismiss = (alertId: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertId]));
    onDismiss?.(alertId);
  };

  const getSeverityIcon = (severity: AlertSeverity): string => {
    const icons: Record<AlertSeverity, string> = {
      critical: '🔴',
      high: '🟠',
      medium: '🟡',
      low: '🔵',
      info: 'ℹ️',
    };
    return icons[severity];
  };

  const formatTime = (timestamp: number): string => {
    const now = Date.now();
    const diff = Math.floor((now - timestamp) / 1000);

    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  return (
    <div
      className="alert-widget"
      role="region"
      aria-label="System alerts"
      aria-live="polite"
      aria-atomic="false"
    >
      <div
        style={{
          fontSize: 'var(--font-size-lg)',
          fontWeight: 'var(--font-weight-bold)',
          marginBottom: 'var(--spacing-4)',
          paddingBottom: 'var(--spacing-3)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span>Alerts ({visibleAlerts.length})</span>
        {alerts.length > visibleAlerts.length && (
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
            +{alerts.length - visibleAlerts.length} more
          </span>
        )}
      </div>

      {visibleAlerts.length === 0 ? (
        <div
          style={{
            padding: 'var(--spacing-8)',
            textAlign: 'center',
            color: 'var(--color-text-secondary)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          No active alerts
        </div>
      ) : (
        <div className="alert-list" role="list">
          {visibleAlerts.map((alert) => (
            <div
              key={alert.alert_id}
              className={`alert-item ${alert.severity}`}
              role="listitem"
              aria-label={`${alert.severity} alert: ${alert.alert_type}`}
            >
              <div className="alert-icon" aria-hidden="true">
                {getSeverityIcon(alert.severity)}
              </div>
              <div className="alert-content">
                <div className="alert-type">{alert.alert_type}</div>
                <div className="alert-message">{alert.message}</div>
                <div
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-text-tertiary)',
                    marginTop: 'var(--spacing-2)',
                  }}
                >
                  {formatTime(alert.timestamp)}
                  {alert.escalation_flag && (
                    <span style={{ marginLeft: 'var(--spacing-2)', fontWeight: 'bold' }}>
                      • ESCALATED
                    </span>
                  )}
                </div>
              </div>
              <button
                className="alert-dismiss-btn"
                onClick={() => handleDismiss(alert.alert_id)}
                aria-label={`Dismiss ${alert.severity} alert: ${alert.alert_type}`}
                title="Dismiss this alert"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {alerts.length > visibleAlerts.length && (
        <div
          style={{
            marginTop: 'var(--spacing-4)',
            padding: 'var(--spacing-3)',
            backgroundColor: 'var(--color-bg-primary)',
            borderRadius: '6px',
            textAlign: 'center',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-secondary)',
          }}
        >
          Showing {visibleAlerts.length} of {alerts.length} alerts
        </div>
      )}
    </div>
  );
};

export default AlertWidget;
