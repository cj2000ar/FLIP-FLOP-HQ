import { vi } from 'vitest';
import '@testing-library/jest-dom';
import {
  ARENA, EXPERIMENTS, QUEUE, AGENDA_SLOTS, WOUNDS, CALIBRATION, PROMOTION_GATES,
} from './src/lab/labData';

// jsdom has no blob URL support; CSV download uses it.
if (typeof URL.createObjectURL !== 'function') {
  URL.createObjectURL = vi.fn(() => 'blob:mock');
}
if (typeof URL.revokeObjectURL !== 'function') {
  URL.revokeObjectURL = vi.fn();
}

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
  'http://localhost:8000/arena': { arena: ARENA },
  'http://localhost:8000/experiments': { experiments: EXPERIMENTS },
  'http://localhost:8000/queue': { queue: QUEUE },
  'http://localhost:8000/agenda/events': { events: AGENDA_SLOTS },
  'http://localhost:8000/guardian/wounds': { wounds: WOUNDS },
  'http://localhost:8000/guardian/calibration': { calibration: CALIBRATION },
  'http://localhost:8000/promotion/gates': { gates: PROMOTION_GATES },
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
