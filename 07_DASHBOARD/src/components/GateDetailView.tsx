import React from 'react';
import { GateDecision } from '../types';

/**
 * GateDetailView - Per-gate verdict and evidence details
 * Clickable from GuardianSeal to drill down
 */

interface GateDetailViewProps {
  gate: GateDecision;
  isAdmin?: boolean;
}

export const GateDetailView: React.FC<GateDetailViewProps> = ({ gate, isAdmin = false }) => {
  const formatTime = (timestamp: number): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getGateDescription = (gateId: number): string => {
    const descriptions: Record<number, string> = {
      1: 'Validates schema and identity. Checks for bad schema, duplicate IDs, missing hash.',
      2: 'Verifies hash integrity. Detects hash mismatches and contradictions.',
      3: 'Enforces authority policy compliance. Authority must equal ZERO. No escalation allowed.',
      4: 'Monitors machine health and readiness. Checks heartbeat, clock sync, restart detection.',
      5: 'Evaluates canary execution. Error rate must be < 5%, latency < 200ms.',
      6: 'Ensures evidence consistency. Detects contradictions and temporal ordering violations.',
      7: 'Enforces freshness and staleness constraints. Evidence must be < 300s old.',
      8: 'Final arbiter gate. Re-verifies all constraints. Authority must be ZERO.',
    };
    return descriptions[gateId] || 'Gate verification';
  };

  return (
    <div
      style={{
        marginTop: 'var(--spacing-3)',
        padding: 'var(--spacing-4)',
        backgroundColor: 'var(--color-bg-tertiary)',
        borderRadius: '6px',
        border: '1px solid var(--color-border)',
      }}
      role="region"
      aria-label={`Details for Gate ${gate.gate_id}`}
    >
      <div
        style={{
          fontWeight: 'var(--font-weight-bold)',
          marginBottom: 'var(--spacing-2)',
          fontSize: 'var(--font-size-sm)',
        }}
      >
        {gate.gate_name}
      </div>

      <div
        style={{
          fontSize: 'var(--font-size-xs)',
          color: 'var(--color-text-secondary)',
          marginBottom: 'var(--spacing-3)',
          lineHeight: '1.4',
        }}
      >
        {getGateDescription(gate.gate_id)}
      </div>

      <div
        style={{
          display: 'grid',
          gap: 'var(--spacing-3)',
          fontSize: 'var(--font-size-xs)',
          fontFamily: 'var(--font-family-mono)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: 'var(--spacing-2)',
            backgroundColor: 'var(--color-bg-primary)',
            borderRadius: '4px',
          }}
        >
          <span style={{ color: 'var(--color-text-secondary)' }}>Verdict:</span>
          <span style={{ fontWeight: 'var(--font-weight-bold)' }}>{gate.verdict}</span>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: 'var(--spacing-2)',
            backgroundColor: 'var(--color-bg-primary)',
            borderRadius: '4px',
          }}
        >
          <span style={{ color: 'var(--color-text-secondary)' }}>Evidence ID:</span>
          <span style={{ wordBreak: 'break-all' }}>{gate.evidence_id}</span>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: 'var(--spacing-2)',
            backgroundColor: 'var(--color-bg-primary)',
            borderRadius: '4px',
          }}
        >
          <span style={{ color: 'var(--color-text-secondary)' }}>Truth Age:</span>
          <span>{gate.truth_age_seconds}s</span>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: 'var(--spacing-2)',
            backgroundColor: 'var(--color-bg-primary)',
            borderRadius: '4px',
          }}
        >
          <span style={{ color: 'var(--color-text-secondary)' }}>Event Time:</span>
          <span>{formatTime(gate.event_time)}</span>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: 'var(--spacing-2)',
            backgroundColor: 'var(--color-bg-primary)',
            borderRadius: '4px',
          }}
        >
          <span style={{ color: 'var(--color-text-secondary)' }}>Knowledge Time:</span>
          <span>{formatTime(gate.knowledge_time)}</span>
        </div>

        {gate.details && (
          <div
            style={{
              padding: 'var(--spacing-2)',
              backgroundColor: 'var(--color-bg-primary)',
              borderRadius: '4px',
              borderLeft: '3px solid var(--color-pass-green)',
            }}
          >
            <span style={{ color: 'var(--color-text-secondary)' }}>Details:</span>
            <div style={{ marginTop: 'var(--spacing-1)', color: 'var(--color-text-primary)' }}>
              {gate.details}
            </div>
          </div>
        )}

        {isAdmin && (
          <div
            style={{
              marginTop: 'var(--spacing-2)',
              padding: 'var(--spacing-2)',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              borderRadius: '4px',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-low-blue)',
            }}
          >
            Admin View: Full audit trail available. Evidence immutable (INSERT-only).
          </div>
        )}
      </div>
    </div>
  );
};

export default GateDetailView;
