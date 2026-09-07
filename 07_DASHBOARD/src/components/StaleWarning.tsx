import React from 'react';

/**
 * StaleWarning - Modal overlay for stale data (> 30s truth-age)
 * Blocks interaction until data is refreshed
 * Full desaturation + watermark on phone/tablet/desktop
 */

interface StaleWarningProps {
  show: boolean;
  truthAgeSecs: number;
  onRefresh?: () => void;
}

export const StaleWarning: React.FC<StaleWarningProps> = ({ show, truthAgeSecs, onRefresh }) => {
  if (!show) return null;

  const minutes = Math.floor(truthAgeSecs / 60);
  const seconds = truthAgeSecs % 60;

  return (
    <>
      <div className="stale-overlay" role="alertdialog" aria-labelledby="stale-title">
        <div className="stale-modal">
          <div className="stale-modal-title" id="stale-title">
            DATA IS STALE
          </div>
          <div className="stale-modal-message">
            Evidence is {minutes}m {seconds}s old. All operations are blocked until data is
            refreshed.
          </div>
          <button
            onClick={onRefresh}
            style={{
              padding: 'var(--spacing-3) var(--spacing-6)',
              backgroundColor: 'white',
              color: 'var(--color-stale-red)',
              border: 'none',
              borderRadius: '4px',
              fontWeight: 'var(--font-weight-bold)',
              cursor: 'pointer',
              transition: 'all var(--transition-base)',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'rgba(255,255,255,0.9)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'white';
            }}
            aria-label="Refresh data"
          >
            REFRESH
          </button>
        </div>
      </div>
      <div className="stale-watermark">STALE</div>
    </>
  );
};

export default StaleWarning;
