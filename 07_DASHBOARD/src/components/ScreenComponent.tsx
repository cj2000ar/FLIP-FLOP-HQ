import React, { useEffect, useState } from 'react';
import { ScreenComponentProps, FormFactor } from '../types';
import TruthBar from './TruthBar';
import GuardianSeal from './GuardianSeal';
import HealthIndicator from './HealthIndicator';
import AlertWidget from './AlertWidget';
import StaleWarning from './StaleWarning';
import BatchSummary from './BatchSummary';
import ArchiveViewer from './ArchiveViewer';
import Brand from './Brand';
import Lab from './Lab';
import GuardianPage from './GuardianPage';
import ShadowLab from './ShadowLab';
import TradesView from './TradesView';
import PerformanceView from './PerformanceView';
import CalendarView from './CalendarView';
import AgentsView from './AgentsView';

/**
 * ScreenComponent - Main responsive UI container
 * Handles form factors: Phone (375px), Tablet (768px), Desktop (1440px+)
 * Implements truth-age state machine with stale detection
 */

export const ScreenComponent: React.FC<ScreenComponentProps> = ({
  guardianState,
  truthBar,
  healthIndicator,
  batchStatus,
  alerts,
  archives,
  onAlertDismiss,
  onRefresh,
  isAdmin = false,
}) => {
  const [formFactor, setFormFactor] = useState<FormFactor>('desktop');
  const [showStaleWarning, setShowStaleWarning] = useState(false);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  const [activeNav, setActiveNav] = useState<string>('overview');

  const navItems: { id: string; label: string; short?: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'trades', label: 'Trades' },
    { id: 'performance', label: 'Performance', short: 'Perf' },
    { id: 'calendar', label: 'Calendar' },
    { id: 'agents', label: 'Agents' },
    { id: 'shadow', label: 'Shadow', short: 'Lab' },
    { id: 'guardian', label: 'Guardian', short: 'Guard' },
    { id: 'lab', label: 'Lab' },
  ];

  // Detect form factor based on window width
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setFormFactor('phone');
      } else if (window.innerWidth < 1440) {
        setFormFactor('tablet');
      } else {
        setFormFactor('desktop');
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Monitor truth-age for stale detection
  useEffect(() => {
    if (truthBar.age_seconds > 30) {
      setShowStaleWarning(true);
    } else {
      setShowStaleWarning(false);
    }
  }, [truthBar.age_seconds]);

  const handleAlertDismiss = (alertId: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertId]));
    onAlertDismiss?.(alertId);
  };

  const handleRefresh = () => {
    setShowStaleWarning(false);
    onRefresh?.();
  };

  // Filter alerts to not show dismissed ones
  const visibleAlerts = alerts.filter((a) => !dismissedAlerts.has(a.alert_id));

  return (
    <div className="screen-container">
      <TruthBar
        truthBar={truthBar}
        brokerStatus="NONE"
        controlStatus="NONE"
      />

      <StaleWarning
        show={showStaleWarning}
        truthAgeSecs={truthBar.age_seconds}
        onRefresh={handleRefresh}
      />

      <div className="screen-layout">
        {/* Sidebar Navigation */}
        {formFactor !== 'phone' && (
          <nav className="sidebar">
            <div className="sidebar-brand">
              <Brand />
            </div>
            <div className="sidebar-nav">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  className={`sidebar-item ${activeNav === item.id ? 'active' : ''}`}
                  onClick={() => setActiveNav(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </nav>
        )}

      <div className="screen-content">
        {/* Overview Tab - Default Landing */}
        {activeNav === 'overview' && (
          <div
            role="main"
            aria-label="Command center overview"
            style={{
              display: 'grid',
              gap: 'var(--spacing-6)',
              gridTemplateColumns: formFactor === 'phone' ? '1fr' : formFactor === 'tablet' ? '1fr 1fr' : '1fr 1fr 1fr 1fr',
              gridAutoRows: 'auto',
              padding: formFactor === 'phone' ? 'var(--spacing-2)' : 'var(--spacing-6)',
            }}
          >
            {/* Portfolio Overview - Full Width */}
            <div
              style={{
                gridColumn: formFactor === 'phone' ? '1' : '1 / -1',
                padding: 'var(--spacing-6)',
                background: 'var(--hq-panel-bg)',
                borderRadius: '12px',
                border: '1px solid var(--color-border)',
                backdropFilter: 'blur(10px)',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
              }}
            >
              <div className="portfolio-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-4)' }}>
                <div>
                  <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold', marginBottom: 'var(--spacing-2)' }}>
                    Official Portfolio
                  </h2>
                  <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>Owner · SIMULATED</p>
                </div>
                <select style={{
                  padding: 'var(--spacing-2) var(--spacing-3)',
                  background: 'rgba(51, 65, 85, 0.5)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '6px',
                  color: 'var(--color-text-primary)',
                  fontSize: 'var(--font-size-sm)',
                  cursor: 'pointer',
                }}>
                  <option>Live Account 1</option>
                </select>
              </div>
            </div>

            {/* P&L Live */}
            <div style={{
              padding: 'var(--spacing-4)',
              background: 'var(--hq-panel-bg)',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              backdropFilter: 'blur(10px)',
            }}>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--spacing-2)' }}>LIVE P&L</p>
              <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-pass-green)' }}>+$838</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>Today</p>
            </div>

            {/* Risk Used */}
            <div style={{
              padding: 'var(--spacing-4)',
              background: 'var(--hq-panel-bg)',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              backdropFilter: 'blur(10px)',
            }}>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--spacing-2)' }}>Risk Used</p>
              <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-warning-yellow)' }}>1.24%</p>
              <div style={{ width: '100%', height: '4px', background: 'rgba(51, 65, 85, 0.5)', borderRadius: '2px', marginTop: 'var(--spacing-2)' }}>
                <div style={{ width: '12.4%', height: '100%', background: 'var(--color-warning-yellow)', borderRadius: '2px' }} />
              </div>
            </div>

            {/* Win Rate */}
            <div style={{
              padding: 'var(--spacing-4)',
              background: 'var(--hq-panel-bg)',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              backdropFilter: 'blur(10px)',
            }}>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--spacing-2)' }}>Win Rate</p>
              <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-low-blue)' }}>50%</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>Simulated</p>
            </div>

            {/* Profit Factor */}
            <div style={{
              padding: 'var(--spacing-4)',
              background: 'var(--hq-panel-bg)',
              borderRadius: '12px',
              border: '1px solid var(--color-border)',
              backdropFilter: 'blur(10px)',
            }}>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--spacing-2)' }}>Profit Factor</p>
              <p style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'bold', color: 'var(--color-pass-green)' }}>2.37</p>
              <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>Simulated</p>
            </div>

            {/* Guardian seal */}
            <GuardianSeal
              gates={guardianState.gates}
              finalVerdict={guardianState.final_verdict}
              promotionReady={guardianState.promotion_ready}
              isAdmin={isAdmin}
            />

            {/* Batch summary */}
            <BatchSummary
              report={batchStatus.report_summary}
              batchStatus={batchStatus.verdict_status}
              isAdmin={isAdmin}
            />

            {/* Machine health */}
            <HealthIndicator health={healthIndicator} isAdmin={isAdmin} />

            {/* Alerts */}
            <div style={{ gridColumn: formFactor === 'phone' ? '1' : '1 / 3' }}>
              <AlertWidget
                alerts={visibleAlerts}
                onDismiss={handleAlertDismiss}
                maxVisible={20}
              />
            </div>

            {/* Archives */}
            {archives.length > 0 && <ArchiveViewer archives={archives} isAdmin={isAdmin} />}
          </div>
        )}

        {/* Trades Tab */}
        {activeNav === 'trades' && <TradesView />}

        {/* Performance Tab */}
        {activeNav === 'performance' && <PerformanceView />}

        {/* Calendar Tab */}
        {activeNav === 'calendar' && <CalendarView />}

        {/* Agents Tab */}
        {activeNav === 'agents' && <AgentsView />}

        {/* Lab Tab */}
        {activeNav === 'lab' && <Lab />}

        {/* Shadow Lab Tab */}
        {activeNav === 'shadow' && <ShadowLab />}

        {/* Guardian Tab */}
        {activeNav === 'guardian' && <GuardianPage />}
      </div>

      {/* Mobile Bottom Navigation */}
      {formFactor === 'phone' && (
        <div
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            height: '60px',
            background: 'var(--hq-nav-bg)',
            borderTop: '1px solid var(--hq-nav-border)',
            display: 'flex',
            justifyContent: 'space-around',
            alignItems: 'center',
            gap: '4px',
            padding: '6px 4px',
            backdropFilter: 'blur(10px)',
          }}
        >
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveNav(item.id)}
              style={{
                flex: 1,
                minWidth: 0,
                padding: '6px 4px',
                background: activeNav === item.id ? 'var(--hq-surface-3)' : 'transparent',
                border: activeNav === item.id ? '1px solid #ffffff12' : '1px solid transparent',
                color: activeNav === item.id ? '#ffffff' : 'var(--hq-muted-2)',
                borderRadius: '8px',
                fontSize: '10px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontWeight: activeNav === item.id ? 'bold' : 'normal',
                cursor: 'pointer',
                transition: 'all var(--transition-base)',
              }}
            >
              {item.short ?? item.label}
            </button>
          ))}
        </div>
      )}
      </div>
    </div>
  );
};

export default ScreenComponent;
