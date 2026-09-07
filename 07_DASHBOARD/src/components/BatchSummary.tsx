import React from 'react';
import { DayReport, BatchStatus } from '../types';

/**
 * BatchSummary - P&L, trades, alerts summary
 * Read-only display of batch execution results
 */

interface BatchSummaryProps {
  report: DayReport;
  batchStatus: BatchStatus;
  isAdmin?: boolean;
}

export const BatchSummary: React.FC<BatchSummaryProps> = ({ report, batchStatus, isAdmin = false }) => {
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: report.pnl_summary.currency,
      minimumFractionDigits: 2,
    }).format(value);
  };

  const getStatusColor = (status: BatchStatus): string => {
    switch (status) {
      case 'APPROVED':
        return 'var(--color-pass-green)';
      case 'BLOCKED':
        return 'var(--color-blocked-red)';
      case 'CLOSED':
        return 'var(--color-info-gray)';
      default:
        return 'var(--color-text-primary)';
    }
  };

  return (
    <div className="batch-summary" role="region" aria-label="Batch execution summary">
      <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)' }}>
        Batch Summary
      </div>

      <div className="summary-section">
        <div className="summary-title">Verdict</div>
        <div
          className="summary-row"
          style={{ backgroundColor: 'transparent', padding: 'var(--spacing-4) 0' }}
        >
          <div className="summary-label">Status</div>
          <div className="summary-value" style={{ color: getStatusColor(batchStatus) }}>
            {batchStatus}
          </div>
        </div>
      </div>

      <div className="summary-section">
        <div className="summary-title">P&L</div>
        <div className="summary-row">
          <div className="summary-label">Gross P&L</div>
          <div className="summary-value" style={{ color: 'var(--color-pass-green)' }}>
            {formatCurrency(report.pnl_summary.gross_pnl)}
          </div>
        </div>
        <div className="summary-row">
          <div className="summary-label">Net P&L</div>
          <div
            className="summary-value"
            style={{
              color:
                report.pnl_summary.net_pnl >= 0
                  ? 'var(--color-pass-green)'
                  : 'var(--color-blocked-red)',
            }}
          >
            {formatCurrency(report.pnl_summary.net_pnl)}
          </div>
        </div>
      </div>

      <div className="summary-section">
        <div className="summary-title">Trade Metrics</div>
        <div className="summary-row">
          <div className="summary-label">Trade Count</div>
          <div className="summary-value">{report.trade_count}</div>
        </div>
        <div className="summary-row">
          <div className="summary-label">Win Rate</div>
          <div className="summary-value">{report.risk_metrics.win_rate_pct.toFixed(1)}%</div>
        </div>
        <div className="summary-row">
          <div className="summary-label">Max Drawdown</div>
          <div className="summary-value">{report.risk_metrics.max_drawdown_pct.toFixed(2)}%</div>
        </div>
        <div className="summary-row">
          <div className="summary-label">Sharpe Ratio</div>
          <div className="summary-value">{report.risk_metrics.sharpe_ratio.toFixed(2)}</div>
        </div>
      </div>

      <div className="summary-section">
        <div className="summary-title">Alerts</div>
        <div className="summary-row">
          <div className="summary-label">Alert Count</div>
          <div className="summary-value">
            {report.alert_count}
            {report.alert_count > 0 && (
              <span style={{ fontSize: 'var(--font-size-xs)', marginLeft: 'var(--spacing-2)' }}>
                (see Alerts section)
              </span>
            )}
          </div>
        </div>
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
          Admin View: Batch data is immutable after close. Authority=ZERO locked throughout.
          Export time: {new Date(report.export_time).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default BatchSummary;
