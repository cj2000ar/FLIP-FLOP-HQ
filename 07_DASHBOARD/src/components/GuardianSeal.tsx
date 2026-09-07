import React, { useState } from 'react';
import { GateDecision, GateVerdict } from '../types';
import GateDetailView from './GateDetailView';

/**
 * GuardianSeal - Displays 8 Guardian gates with verdicts
 * Shows pass/blocked count and clickable detail view per gate
 * All gates must PASS for promotion (fail-closed)
 */

interface GuardianSealProps {
  gates: GateDecision[];
  finalVerdict: GateVerdict;
  promotionReady: boolean;
  onGateClick?: (gateId: number) => void;
  isAdmin?: boolean;
}

export const GuardianSeal: React.FC<GuardianSealProps> = ({
  gates,
  finalVerdict,
  promotionReady,
  onGateClick,
  isAdmin = false,
}) => {
  const [selectedGateId, setSelectedGateId] = useState<number | null>(null);

  const passCount = gates.filter((g) => g.verdict === 'PASS').length;
  const blockedCount = gates.filter((g) => g.verdict === 'BLOCKED').length;

  const handleGateClick = (gateId: number) => {
    setSelectedGateId(selectedGateId === gateId ? null : gateId);
    onGateClick?.(gateId);
  };

  const getVerdictClass = (verdict: GateVerdict): string => {
    switch (verdict) {
      case 'PASS':
        return 'pass';
      case 'BLOCKED':
        return 'blocked';
      case 'NOT_PROVEN':
        return 'not-proven';
      default:
        return '';
    }
  };

  const getFinalVerdictLabel = (): string => {
    if (finalVerdict === 'PASS' && promotionReady) {
      return '✓ PROMOTION READY';
    }
    if (finalVerdict === 'BLOCKED') {
      return '✗ BLOCKED';
    }
    return '? NOT PROVEN';
  };

  return (
    <div className="guardian-seal">
      <div className="seal-header">
        <div className="seal-title">Guardian Seal (8/8 Gates)</div>
        <div className="seal-stats">
          <div className="seal-stat">
            <div className="seal-stat-value" style={{ color: 'var(--color-pass-green)' }}>
              {passCount}
            </div>
            <div className="seal-stat-label">Passed</div>
          </div>
          <div className="seal-stat">
            <div className="seal-stat-value" style={{ color: 'var(--color-blocked-red)' }}>
              {blockedCount}
            </div>
            <div className="seal-stat-label">Blocked</div>
          </div>
          <div className="seal-stat">
            <div
              className="seal-stat-value"
              style={{
                color:
                  finalVerdict === 'PASS' && promotionReady
                    ? 'var(--color-pass-green)'
                    : finalVerdict === 'BLOCKED'
                      ? 'var(--color-blocked-red)'
                      : 'var(--color-not-proven-gray)',
              }}
            >
              {getFinalVerdictLabel()}
            </div>
            <div className="seal-stat-label">Status</div>
          </div>
        </div>
      </div>

      <div className="gates-grid">
        {gates.map((gate) => (
          <div key={gate.gate_id}>
            <button
              type="button"
              className="gate-item"
              onClick={() => handleGateClick(gate.gate_id)}
              aria-expanded={selectedGateId === gate.gate_id}
              aria-label={`Gate ${gate.gate_id}: ${gate.gate_name}, verdict: ${gate.verdict}`}
            >
              <div className="gate-name">Gate {gate.gate_id}</div>
              <div className={`gate-verdict ${getVerdictClass(gate.verdict)}`}>
                {gate.verdict}
              </div>
            </button>
            {selectedGateId === gate.gate_id && (
              <GateDetailView gate={gate} isAdmin={isAdmin} />
            )}
          </div>
        ))}
      </div>

      {!promotionReady && (
        <div
          role="alert"
          style={{
            padding: 'var(--spacing-4)',
            backgroundColor: 'rgba(220, 38, 38, 0.1)',
            border: '1px solid var(--color-stale-red)',
            borderRadius: '4px',
            color: 'var(--color-stale-red)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          ⚠️ Not all gates have passed. Promotion is blocked.
        </div>
      )}
    </div>
  );
};

export default GuardianSeal;
