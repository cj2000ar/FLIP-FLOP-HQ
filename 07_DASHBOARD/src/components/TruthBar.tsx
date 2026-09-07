import React from 'react';
import { TruthBarState, TruthAge } from '../types';

/**
 * TruthBar - Fixed top bar displaying truth-age state
 * Authority: ZERO (hard-locked)
 * Live: OFF (paper-only)
 * Truth-age:
 *   < 10s: GREEN (fresh), full opacity, enabled
 *   10-30s: YELLOW (warning), desaturate 50%, disabled pending
 *   > 30s: RED (stale block), full desaturation, modal overlay
 */

interface TruthBarProps {
  truthBar: TruthBarState;
  brokerStatus?: string;
  controlStatus?: string;
}

export const TruthBar: React.FC<TruthBarProps> = ({
  truthBar,
  brokerStatus = 'NONE',
  controlStatus = 'NONE'
}) => {
  const getTruthAgeLabel = (age: number): string => {
    if (age < 60) return `${age}s ago`;
    const minutes = Math.floor(age / 60);
    return `${minutes}m ago`;
  };

  const getWarningLevelClass = (level: TruthAge): string => {
    return level;
  };

  return (
    <div
      className={`truth-bar ${getWarningLevelClass(truthBar.warning_level)}`}
      role="region"
      aria-label="Truth age and system status indicator"
      aria-live="polite"
    >
      <div className="truth-bar-section">
        <div
          className="authority-badge"
          role="status"
          aria-label="Authority level is ZERO - no escalation possible"
        >
          🔒 Authority: ZERO
        </div>
        <div
          className="live-indicator"
          role="status"
          aria-label="Live trading is OFF - paper trades only"
        >
          🔴 Live: OFF
        </div>
      </div>

      <div className="truth-bar-section">
        <div
          className="truth-age-display"
          role="status"
          aria-label={`Data freshness: ${getTruthAgeLabel(truthBar.age_seconds)}`}
        >
          Data: {getTruthAgeLabel(truthBar.age_seconds)}
        </div>
        {truthBar.warning_level === 'stale' && (
          <div
            className="truth-age-display"
            role="alert"
            aria-label="Data is stale - more than 30 seconds old"
          >
            ⚠️ STALE
          </div>
        )}
      </div>

      <div className="truth-bar-section">
        <div
          className="truth-age-display"
          role="status"
          aria-label={`Broker orders: ${brokerStatus}`}
        >
          Broker: {brokerStatus}
        </div>
        <div
          className="truth-age-display"
          role="status"
          aria-label={`Control mutations: ${controlStatus}`}
        >
          Control: {controlStatus}
        </div>
      </div>
    </div>
  );
};

export default TruthBar;
