import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import Lab, { LAB_SECTIONS } from './components/Lab';
import { EXPERIMENTS, PROMOTION_GATES, QUEUE, QUEUE_STATES } from './lab/labData';

const go = (label: string) => fireEvent.click(screen.getByRole('button', { name: label }));

describe('Lab shell', () => {
  it('1. renders authority banner and all 8 section buttons', () => {
    render(<Lab />);
    expect(screen.getByText(/AUTHORITY=ZERO · LIVE=NO · BROKER_ORDERS=NONE/)).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: /Lab sections/ });
    expect(within(nav).getAllByRole('button')).toHaveLength(8);
    expect(LAB_SECTIONS.map((s) => s.label)).toEqual([
      'Vault', 'Arena', 'Experiments', 'Queue', 'Agenda', 'Guardian', 'Promotion', 'Quantum',
    ]);
  });

  it('2. defaults to Vault and switches sections with aria-pressed', () => {
    render(<Lab />);
    expect(screen.getByRole('region', { name: 'Strategy Vault' })).toBeInTheDocument();
    go('Arena');
    expect(screen.getByRole('region', { name: 'Strategy Arena' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Arena' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Vault' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('3. exposes no execution or promotion controls anywhere', () => {
    render(<Lab />);
    for (const s of LAB_SECTIONS) {
      go(s.label);
      const offenders = screen
        .getAllByRole('button')
        .filter((b) => /submit|cancel|flatten|promote|activate|execute|approve|run\b/i.test(b.textContent ?? ''));
      expect(offenders, `section ${s.label}`).toHaveLength(0);
      expect(screen.queryAllByRole('textbox')).toHaveLength(0);
    }
  });
});

describe('Strategy Vault', () => {
  it('4. lists the five strategy families and the RR500 CONTROL script', () => {
    render(<Lab />);
    expect(screen.getByText('RR500 / FlipFlop Quant Mirror')).toBeInTheDocument();
    expect(screen.getByText('IFVG / FVG')).toBeInTheDocument();
    expect(screen.getByText('UT / NUMKI')).toBeInTheDocument();
    expect(screen.getByText('KiloView')).toBeInTheDocument();
    expect(screen.getByText('Session / Market Structure Book')).toBeInTheDocument();
    expect(screen.getByText(/RR500 Quant Mirror V3\.3\.1/)).toBeInTheDocument();
  });

  it('5. family filter narrows the vault table', () => {
    render(<Lab />);
    const table = screen.getByRole('table');
    const before = within(table).getAllByRole('row').length;
    fireEvent.click(screen.getByRole('button', { name: 'ORDER_FLOW' }));
    const after = within(table).getAllByRole('row').length;
    expect(after).toBeLessThan(before);
    expect(within(table).getByText(/Pietro Valastro/)).toBeInTheDocument();
  });

  it('6. unreviewed shorts are marked, never invented', () => {
    render(<Lab />);
    expect(screen.getAllByText('UNREVIEWED').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/never invent content from thumbnail/)).toBeInTheDocument();
  });
});

describe('Strategy Arena', () => {
  it('7. shows RR500_CONTROL as frozen CONTROL with the 12-trade baseline', () => {
    render(<Lab initialSection="arena" />);
    expect(screen.getByText('RR500_CONTROL')).toBeInTheDocument();
    expect(screen.getByText('83.33%')).toBeInTheDocument();
    expect(screen.getByText('7.5')).toBeInTheDocument();
    expect(screen.getByText('+416')).toBeInTheDocument();
    expect(screen.getByText('+$2,080')).toBeInTheDocument();
  });

  it('8. survivor pair is research-grade and V03 vector is rejected', () => {
    render(<Lab initialSection="arena" />);
    expect(screen.getByText('SURVIVOR')).toBeInTheDocument();
    expect(screen.getByText('0.764')).toBeInTheDocument();
    expect(screen.getByText('REJECTED')).toBeInTheDocument();
    expect(screen.getByText(/Holdout consumed\/blocked/)).toBeInTheDocument();
  });
});

describe('Experiment Ledger', () => {
  it('9. registers experiments A–G, all pre-registered with zero runs', () => {
    render(<Lab initialSection="experiments" />);
    for (const id of ['A', 'B', 'C', 'D', 'E', 'F', 'G']) {
      const e = EXPERIMENTS.find((x) => x.id === id);
      expect(e?.status).toBe('PRE_REGISTERED');
      expect(e?.runs).toBe(0);
      expect(screen.getByText(e!.name)).toBeInTheDocument();
    }
  });

  it('10. failed holdout and invalid reserve remain visible with reasons', () => {
    render(<Lab initialSection="experiments" />);
    expect(within(screen.getByRole('table')).getByText('FAILED')).toBeInTheDocument();
    expect(screen.getByText(/TECHNICALLY_INVALID_UNSCOREABLE/)).toBeInTheDocument();
    expect(screen.getByText(/cannot be reopened or reused/i)).toBeInTheDocument();
  });
});

describe('SHADOW Queue', () => {
  it('11. renders every queue state as a column, including empty PROMOTION_REVIEW', () => {
    render(<Lab initialSection="queue" />);
    for (const state of QUEUE_STATES) {
      expect(screen.getByRole('list', { name: state })).toBeInTheDocument();
    }
    const review = screen.getByRole('list', { name: 'PROMOTION_REVIEW' });
    expect(within(review).queryAllByRole('listitem')).toHaveLength(0);
    expect(within(review).getByText('0 items')).toBeInTheDocument();
  });

  it('12. every queue item appears under its state with a reason', () => {
    render(<Lab initialSection="queue" />);
    for (const q of QUEUE) {
      const col = screen.getByRole('list', { name: q.state });
      expect(within(col).getByText(q.title)).toBeInTheDocument();
      expect(within(col).getByText(q.why)).toBeInTheDocument();
    }
  });
});

describe('News Agenda', () => {
  it('13. reports no connected feed and leaves event fields empty', () => {
    render(<Lab initialSection="agenda" />);
    expect(screen.getByText('No verified capture connected')).toBeInTheDocument();
    expect(screen.getAllByText('NOT_CONNECTED').length).toBeGreaterThanOrEqual(5);
    for (const code of ['CPI', 'NFP', 'FOMC', 'PPI', 'RETAIL']) {
      expect(screen.getByText(code)).toBeInTheDocument();
    }
    expect(screen.queryByText(/\d+\.\d+%/)).not.toBeInTheDocument();
  });
});

describe('Guardian Ledgers', () => {
  it('14. shows core trust architecture, wounds and an empty override ledger', () => {
    render(<Lab initialSection="guardian" />);
    expect(screen.getAllByText('CORE NOW').length).toBe(7);
    expect(screen.getAllByText('BUILD SOON').length).toBe(2);
    expect(screen.getByText('V03 PATH is post-decision')).toBeInTheDocument();
    expect(screen.getByText('No manual overrides recorded.')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});

describe('Promotion Gate', () => {
  it('15. has 16 gates, verdict BLOCKED, and owner approval cannot override', () => {
    render(<Lab initialSection="promotion" />);
    expect(PROMOTION_GATES).toHaveLength(16);
    expect(screen.getByText('BLOCKED')).toBeInTheDocument();
    expect(screen.getByText('LIVE_AUTHORITY=BLOCKED')).toBeInTheDocument();
    expect(screen.getByText(/cannot override gates 1–15/)).toBeInTheDocument();
    const notProven = PROMOTION_GATES.filter((g) => g.status === 'NOT_PROVEN').length;
    expect(notProven).toBeGreaterThan(0);
    expect(screen.getAllByText('NOT_PROVEN')).toHaveLength(notProven);
  });
});

describe('Quantum Lab', () => {
  it('16. separates four lanes and reports no quantum evidence', () => {
    render(<Lab initialSection="quantum" />);
    for (const lane of ['Real Quantum', 'Quantum Simulator', 'Quantum-inspired', 'Classical benchmark']) {
      expect(screen.getByText(lane)).toBeInTheDocument();
    }
    expect(screen.getAllByText('NO EVIDENCE')).toHaveLength(2);
    expect(screen.getByText('REQUIRED BASELINE')).toBeInTheDocument();
  });
});
