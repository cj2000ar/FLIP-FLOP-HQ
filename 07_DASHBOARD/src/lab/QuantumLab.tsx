import { useEffect, useState } from 'react';
import Badge from './Badge';
import { QUANTUM_LANES, QUANTUM_RULE, type QuantumLane } from './labData';
import { apiGet } from '../labApiClient';

export default function QuantumLab() {
  // Local lanes are the frozen definition; the API can only confirm them, never add evidence.
  const [lanes, setLanes] = useState<QuantumLane[]>(QUANTUM_LANES);

  useEffect(() => {
    let cancelled = false;
    apiGet<QuantumLane[]>('/quantum/lanes')
      .then((data) => {
        if (!cancelled && data.length) setLanes(data);
      })
      .catch(() => {
        /* keep the local definition */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section role="region" aria-label="Quantum Lab" className="lab-grid" style={{ gap: 'var(--spacing-5)' }}>
      <div className="lab-head" style={{ gridColumn: '1 / -1' }}>
        <span className="hq-overline">Quantum Lab · future</span>
        <h2>Four lanes. One baseline.</h2>
        <p>{QUANTUM_RULE}</p>
      </div>

      {lanes.map((l) => (
        <div key={l.id} className="hq-panel lab-card">
          <h3>
            {l.name}
            <Badge status={l.status} tone={l.tone} />
          </h3>
          <p>{l.definition}</p>
        </div>
      ))}

      <div className="hq-panel lab-card" style={{ gridColumn: '1 / -1' }}>
        <h3>Promotion criteria</h3>
        <ul>
          <li>Exactly the same data, costs, splits and metrics as the classical baseline.</li>
          <li>Must improve robustness, stability, search or computational cost — otherwise no promotion.</li>
          <li>No marketing science: results are labeled by lane (real / simulator / inspired / classical).</li>
        </ul>
      </div>
    </section>
  );
}
