import React, { useState } from 'react';
import './GuardianPage.css';

interface GateVerdict {
  gate_id: string;
  verdict: 'PASS' | 'BLOCKED' | 'NOT_PROVEN';
  reasoning: string;
}

interface EvaluationResult {
  cartridge_id: string;
  correlation_id: string;
  final_verdict: 'PASS' | 'BLOCKED' | 'NOT_PROVEN';
  gate_verdicts: GateVerdict[];
  authority: string;
  created_at: string;
}

export const GuardianPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/guardian/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          correlation_id: crypto.randomUUID?.() || Math.random().toString(),
          artifact_hashes: {
            strategy: 'sha256_' + Math.random().toString(36).substring(7),
            engine: 'sha256_' + Math.random().toString(36).substring(7),
            ui: 'sha256_' + Math.random().toString(36).substring(7),
          },
          passport_hash: 'sha256_passport_' + Math.random().toString(36).substring(7),
          side: 'BUY',
          source_system: 'DASHBOARD',
          evidence: [
            {
              evidence_type: 'HASH_MATCH',
              source_system: 'HP_INFRA',
              observation: {
                strategy_sha256: 'sha256_' + Math.random().toString(36).substring(7),
                engine_sha256: 'sha256_' + Math.random().toString(36).substring(7),
                ui_sha256: 'sha256_' + Math.random().toString(36).substring(7),
              },
              observed_at: new Date().toISOString(),
              recorded_at: new Date().toISOString(),
              checksum: 'checksum_' + Math.random().toString(36).substring(7),
            },
            {
              evidence_type: 'POLICY_CHECK',
              source_system: 'GUARDIAN_POLICY',
              observation: {
                authority: 'ZERO',
                live_enabled: false,
                broker_orders_allowed: false,
              },
              observed_at: new Date().toISOString(),
              recorded_at: new Date().toISOString(),
              checksum: 'checksum_policy',
            },
          ],
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        setError(`Evaluation failed: ${response.statusText}`);
      }
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const verdictColor = (verdict: string) => {
    switch (verdict) {
      case 'PASS':
        return '#10b981';
      case 'BLOCKED':
        return '#ef4444';
      case 'NOT_PROVEN':
        return '#f59e0b';
      default:
        return '#6b7280';
    }
  };

  return (
    <div className="guardian-page">
      <div className="guardian-header">
        <h1>Guardian Enforcement</h1>
        <p>8-Gate Sequential Release Pipeline</p>
      </div>

      <div className="guardian-controls">
        <button
          onClick={handleEvaluate}
          disabled={loading}
          className="evaluate-button"
        >
          {loading ? 'Evaluating...' : 'Run Evaluation'}
        </button>
      </div>

      {error && (
        <div className="error-box">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="result-container">
          <div className="verdict-card">
            <div className="verdict-header">
              <h2>Decision Cartridge</h2>
              <div
                className="final-verdict"
                style={{ borderColor: verdictColor(result.final_verdict) }}
              >
                <span style={{ color: verdictColor(result.final_verdict) }}>
                  {result.final_verdict}
                </span>
              </div>
            </div>

            <div className="metadata">
              <div className="meta-row">
                <span className="meta-label">Cartridge ID:</span>
                <code>{result.cartridge_id}</code>
              </div>
              <div className="meta-row">
                <span className="meta-label">Correlation ID:</span>
                <code>{result.correlation_id}</code>
              </div>
              <div className="meta-row">
                <span className="meta-label">Authority:</span>
                <span>{result.authority}</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Evaluated:</span>
                <span>{new Date(result.created_at).toLocaleString()}</span>
              </div>
            </div>

            <div className="gates-grid">
              {result.gate_verdicts.map((gate) => (
                <div
                  key={gate.gate_id}
                  className="gate-card"
                  style={{ borderLeftColor: verdictColor(gate.verdict) }}
                >
                  <div className="gate-name">{gate.gate_id.toUpperCase()}</div>
                  <div className="gate-verdict" style={{ color: verdictColor(gate.verdict) }}>
                    {gate.verdict}
                  </div>
                  <div className="gate-reasoning">{gate.reasoning}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="guardian-info">
        <h3>About Guardian Enforcement</h3>
        <ul>
          <li><strong>Gate 1:</strong> Schema and Identity validation</li>
          <li><strong>Gate 2:</strong> Hash integrity verification</li>
          <li><strong>Gate 3:</strong> Authority policy compliance (ZERO locked)</li>
          <li><strong>Gate 4:</strong> Machine health and readiness</li>
          <li><strong>Gate 5:</strong> Canary execution results</li>
          <li><strong>Gate 6:</strong> Evidence consistency checks</li>
          <li><strong>Gate 7:</strong> Freshness and staleness validation</li>
          <li><strong>Gate 8:</strong> Final arbiter - aggregate decision</li>
        </ul>
        <p className="note">
          Authority: <strong>ZERO</strong> (hard-locked, immutable)<br />
          Live Orders: <strong>OFF</strong> (paper-only)<br />
          Failure Policy: <strong>FAIL-CLOSED</strong> (stale/missing evidence blocks)
        </p>
      </div>
    </div>
  );
};

export default GuardianPage;
