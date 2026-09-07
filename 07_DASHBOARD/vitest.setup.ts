import { vi } from 'vitest';
import '@testing-library/jest-dom';

const mockResponses: Record<string, unknown> = {
  'http://localhost:8000/vault/items': {
    items: [
      {
        id: 'rr500-ctrl-v3',
        kind: 'script',
        title: 'RR500 Quant Mirror V3.3.1',
        source: 'Internal',
        extraction: 'VERIFIED',
        evidence: 'MARKET_REPLAY',
        family: ['RR500'],
        dna: 'price-flow-order',
        dataNeeds: [],
      },
      {
        id: 'ifvg-short',
        kind: 'video',
        title: 'IFVG Short Algo',
        source: 'Pietro Valastro',
        extraction: 'UNREVIEWED',
        evidence: 'CLIP_ONLY',
        family: ['IFVG'],
        dna: 'fvg-logic',
        dataNeeds: ['fill-data'],
      },
      {
        id: 'order-flow-tape',
        kind: 'video',
        title: 'Order Flow Tape Reading',
        source: 'Pietro Valastro',
        extraction: 'UNREVIEWED',
        evidence: 'CLIP_ONLY',
        family: ['ORDER_FLOW'],
        dna: 'order-flow-tape',
        dataNeeds: ['tape-data'],
      },
    ],
  },
  'http://localhost:8000/vault/families': {
    families: [
      { id: 'rr500', name: 'RR500 / FlipFlop Quant Mirror', lineage: 'Core', dna: ['price', 'flow'] },
      { id: 'ifvg', name: 'IFVG / FVG', lineage: 'Support', dna: ['fvg'] },
      { id: 'ut', name: 'UT / NUMKI', lineage: 'Support', dna: ['levels'] },
      { id: 'kilo', name: 'KiloView', lineage: 'Support', dna: ['volume'] },
      { id: 'session', name: 'Session / Market Structure Book', lineage: 'Support', dna: ['session'] },
      { id: 'ORDER_FLOW', name: 'Order Flow', lineage: 'Research', dna: ['order-flow', 'tape'] },
    ],
  },
  'http://localhost:8000/experiments': {
    experiments: [
      {
        id: 'exp-001',
        name: 'RR500 Spread Test',
        hypothesis: 'Wider spreads improve algo',
        parameters: 'spread=2pts',
        datasetRole: 'IN_SAMPLE',
        runs: 5,
        status: 'COMPLETED',
        result: 'PASS',
      },
    ],
  },
  'http://localhost:8000/queue': {
    queue: [
      { id: 'q1', title: 'Video 1', state: 'CAPTURED', why: 'Waiting processing' },
    ],
  },
  'http://localhost:8000/agenda/events': {
    events: [
      { code: 'NFP', name: 'Non-Farm Payroll', importance: 'HIGH', status: 'NOT_CONNECTED' },
    ],
  },
  'http://localhost:8000/guardian/wounds': {
    wounds: [
      { id: 'w1', title: 'Wound 1', detail: 'Test wound', status: 'OPEN', tone: 'bad' },
    ],
  },
  'http://localhost:8000/guardian/calibration': {
    calibration: [
      { id: 'c1', title: 'Cal 1', detail: 'Test cal', status: 'ACTIVE', tone: 'ok' },
    ],
  },
};

global.fetch = vi.fn((url: string | Request) => {
  const urlStr = typeof url === 'string' ? url : url.url;
  const baseUrl = urlStr.split('?')[0];

  const data = mockResponses[baseUrl];
  if (data) {
    return Promise.resolve(
      new Response(JSON.stringify(data), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  }

  return Promise.reject(new Error(`Unmocked API: ${baseUrl}`));
});
