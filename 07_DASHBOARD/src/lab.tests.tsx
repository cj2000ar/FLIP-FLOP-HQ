import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import Lab, { LAB_SECTIONS } from './components/Lab';
import { EXPERIMENTS, PROMOTION_GATES, QUEUE, QUEUE_STATES } from './lab/labData';

const go = (label: string) => fireEvent.click(screen.getByRole('button', { name: label }));

const waitForLoad = () => waitFor(() => {
  expect(screen.queryByText('Loading Lab...')).not.toBeInTheDocument();
}, { timeout: 3000 });

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

  it('2. defaults to Vault and switches sections with aria-pressed', async () => {
    render(<Lab />);
    await waitForLoad();
    expect(screen.getByRole('region', { name: 'Strategy Vault' })).toBeInTheDocument();
    go('Arena');
    await waitFor(() => screen.getByRole('region', { name: 'Strategy Arena' }));
    expect(screen.getByRole('region', { name: 'Strategy Arena' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Arena' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Vault' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('3. exposes no execution or promotion controls anywhere', async () => {
    render(<Lab />);
    await waitForLoad();
    for (const s of LAB_SECTIONS) {
      go(s.label);
      await waitFor(() => expect(screen.queryByText('Loading Lab...')).not.toBeInTheDocument(), { timeout: 1000 }).catch(() => {});
      const offenders = screen
        .getAllByRole('button')
        .filter((b) => /submit|cancel|flatten|promote|activate|execute|approve|run\b/i.test(b.textContent ?? ''));
      expect(offenders, `section ${s.label}`).toHaveLength(0);
      expect(screen.queryAllByRole('textbox')).toHaveLength(0);
    }
  });
});

describe('Strategy Vault', () => {
  it('4. lists the five strategy families and the RR500 CONTROL script', async () => {
    render(<Lab />);
    await waitForLoad();
    expect(screen.getByText('RR500 / FlipFlop Quant Mirror')).toBeInTheDocument();
    expect(screen.getByText('IFVG / FVG')).toBeInTheDocument();
    expect(screen.getByText('UT / NUMKI')).toBeInTheDocument();
    expect(screen.getByText('KiloView')).toBeInTheDocument();
    expect(screen.getByText('Session / Market Structure Book')).toBeInTheDocument();
    expect(screen.getByText(/RR500 Quant Mirror V3\.3\.1/)).toBeInTheDocument();
  });

  it('5. family filter narrows the vault table', async () => {
    render(<Lab />);
    await waitForLoad();
    const table = screen.getByRole('table');
    const before = within(table).getAllByRole('row').length;
    fireEvent.click(screen.getByRole('button', { name: 'ORDER_FLOW' }));
    const after = within(table).getAllByRole('row').length;
    expect(after).toBeLessThan(before);
    expect(within(table).getByText(/Pietro Valastro/)).toBeInTheDocument();
  });

  it('6. unreviewed shorts are marked, never invented', async () => {
    render(<Lab />);
    await waitForLoad();
    expect(screen.getAllByText('UNREVIEWED').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/never invent content from thumbnail/)).toBeInTheDocument();
  });
});

describe('Strategy Arena', () => {
  it('7. shows RR500_CONTROL as frozen CONTROL with the 12-trade baseline', async () => {
    render(<Lab initialSection="arena" />);
    await waitForLoad();
    expect(screen.getByText('RR500_CONTROL')).toBeInTheDocument();
    expect(screen.getByText('83.33%')).toBeInTheDocument();
    expect(screen.getByText('7.5')).toBeInTheDocument();
    expect(screen.getByText('+416')).toBeInTheDocument();
    expect(screen.getByText('+$2,080')).toBeInTheDocument();
  });

  it('8. survivor pair is research-grade and V03 vector is rejected', async () => {
    render(<Lab initialSection="arena" />);
    await waitForLoad();
    expect(screen.getByText('SURVIVOR')).toBeInTheDocument();
    expect(screen.getByText('0.764')).toBeInTheDocument();
    expect(screen.getByText('REJECTED')).toBeInTheDocument();
    expect(screen.getByText(/Holdout consumed\/blocked/)).toBeInTheDocument();
  });
});

describe('Experiment Ledger', () => {
  it('9. registers experiments A–G, all pre-registered with zero runs', async () => {
    render(<Lab initialSection="experiments" />);
    await waitForLoad();
    for (const id of ['A', 'B', 'C', 'D', 'E', 'F', 'G']) {
      const e = EXPERIMENTS.find((x) => x.id === id);
      expect(e?.status).toBe('PRE_REGISTERED');
      expect(e?.runs).toBe(0);
      expect(screen.getByText(e!.name)).toBeInTheDocument();
    }
  });

  it('10. failed holdout and invalid reserve remain visible with reasons', async () => {
    render(<Lab initialSection="experiments" />);
    await waitForLoad();
    expect(within(screen.getByRole('table')).getByText('FAILED')).toBeInTheDocument();
    expect(screen.getByText(/TECHNICALLY_INVALID_UNSCOREABLE/)).toBeInTheDocument();
    expect(screen.getByText(/cannot be reopened or reused/i)).toBeInTheDocument();
  });
});

describe('SHADOW Queue', () => {
  it('11. renders every queue state as a column, including empty PROMOTION_REVIEW', async () => {
    render(<Lab initialSection="queue" />);
    await waitForLoad();
    for (const state of QUEUE_STATES) {
      expect(screen.getByRole('list', { name: state })).toBeInTheDocument();
    }
    const review = screen.getByRole('list', { name: 'PROMOTION_REVIEW' });
    expect(within(review).queryAllByRole('listitem')).toHaveLength(0);
    expect(within(review).getByText('0 items')).toBeInTheDocument();
  });

  it('12. every queue item appears under its state with a reason', async () => {
    render(<Lab initialSection="queue" />);
    await waitForLoad();
    for (const q of QUEUE) {
      const col = screen.getByRole('list', { name: q.state });
      expect(within(col).getByText(q.title)).toBeInTheDocument();
      expect(within(col).getByText(q.why)).toBeInTheDocument();
    }
  });
});

describe('News Agenda', () => {
  it('13. reports no connected feed and leaves event fields empty', async () => {
    render(<Lab initialSection="agenda" />);
    await waitForLoad();
    expect(screen.getByText('No verified capture connected')).toBeInTheDocument();
    expect(screen.getAllByText('NOT_CONNECTED').length).toBeGreaterThanOrEqual(5);
    for (const code of ['CPI', 'NFP', 'FOMC', 'PPI', 'RETAIL']) {
      expect(screen.getByText(code)).toBeInTheDocument();
    }
    expect(screen.queryByText(/\d+\.\d+%/)).not.toBeInTheDocument();
  });
});

describe('Guardian Ledgers', () => {
  it('14. shows core trust architecture, wounds and an empty override ledger', async () => {
    render(<Lab initialSection="guardian" />);
    await waitForLoad();
    expect(screen.getAllByText('CORE NOW').length).toBe(7);
    expect(screen.getAllByText('BUILD SOON').length).toBe(2);
    expect(screen.getByText('V03 PATH is post-decision')).toBeInTheDocument();
    expect(screen.getByText('No manual overrides recorded.')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});

describe('Promotion Gate', () => {
  it('15. has 16 gates, verdict BLOCKED, and owner approval cannot override', async () => {
    render(<Lab initialSection="promotion" />);
    await waitForLoad();
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
  it('16. separates four lanes and reports no quantum evidence', async () => {
    render(<Lab initialSection="quantum" />);
    await waitForLoad();
    for (const lane of ['Real Quantum', 'Quantum Simulator', 'Quantum-inspired', 'Classical benchmark']) {
      expect(screen.getByText(lane)).toBeInTheDocument();
    }
    expect(screen.getAllByText('NO EVIDENCE')).toHaveLength(2);
    expect(screen.getByText('REQUIRED BASELINE')).toBeInTheDocument();
  });
});
