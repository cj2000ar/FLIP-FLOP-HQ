import { vi } from 'vitest';
import '@testing-library/jest-dom';
import {
  ARENA, EXPERIMENTS, QUEUE, AGENDA_SLOTS, PROMOTION_GATES, QUANTUM_LANES,
} from './src/lab/labData';

// jsdom has no blob URL support; CSV download uses it.
if (typeof URL.createObjectURL !== 'function') {
  URL.createObjectURL = vi.fn(() => 'blob:mock');
}
if (typeof URL.revokeObjectURL !== 'function') {
  URL.revokeObjectURL = vi.fn();
}

/**
 * The mock speaks the API wire contract (PRIVATE_READ_API_SPEC_DRAFT.md): bare
 * arrays, snake_case, free-text extraction/evidence — so the client normalizers
 * are exercised, not bypassed. Content mirrors labData, the frozen Lab spec.
 */
const bitemporal = { event_time: 1_757_600_000, knowledge_time: '2026-09-11T00:00:00Z' };

const mockResponses: Record<string, unknown> = {
  'http://localhost:8000/vault/items': [
    {
      ...bitemporal,
      id: 'rr500-ctrl-v3',
      kind: 'script',
      title: 'RR500 Quant Mirror V3.3.1',
      source: 'Internal',
      extraction: 'VERIFIED',
      evidence: 'MARKET_REPLAY',
      family: 'RR500',
      dna: 'price-flow-order',
      data_needs: null,
    },
    {
      ...bitemporal,
      id: 'ifvg-short',
      kind: 'video',
      title: 'IFVG Short Algo',
      source: 'Pietro Valastro',
      extraction: 'UNREVIEWED',
      evidence: 'CLIP_ONLY',
      family: 'IFVG',
      dna: 'fvg-logic',
      data_needs: 'fill-data',
    },
    {
      ...bitemporal,
      id: 'order-flow-tape',
      kind: 'video',
      title: 'Order Flow Tape Reading',
      source: 'Pietro Valastro',
      extraction: 'UNREVIEWED',
      evidence: 'CLIP_ONLY',
      family: 'ORDER_FLOW',
      dna: 'order-flow-tape',
      data_needs: 'tape-data, footprint',
    },
  ],
  'http://localhost:8000/vault/families': [
    { id: 'F-RR500', name: 'RR500 / FlipFlop Quant Mirror', lineage: 'Core', dna: 'price, flow' },
    { id: 'F-IFVG', name: 'IFVG / FVG', lineage: 'Support', dna: 'fvg' },
    { id: 'F-UT', name: 'UT / NUMKI', lineage: 'Support', dna: 'levels' },
    { id: 'F-KILO', name: 'KiloView', lineage: 'Support', dna: 'volume' },
    { id: 'F-SESSION', name: 'Session / Market Structure Book', lineage: 'Support', dna: 'session' },
    { id: 'F-ORDER_FLOW', name: 'Order Flow', lineage: 'Research', dna: 'order-flow, tape' },
  ],
  'http://localhost:8000/arena/strategies': ARENA.map((a) => ({ ...bitemporal, ...a })),
  'http://localhost:8000/experiments': EXPERIMENTS.map((e) => ({
    ...bitemporal,
    id: e.id,
    name: e.name,
    hypothesis: e.hypothesis,
    parameters: e.parameters,
    dataset_role: e.datasetRole,
    runs: e.runs,
    status: e.status,
    result: e.result,
    rejection_reason: e.rejectionReason ?? null,
    next_gate: e.nextGate,
    created_at: '2026-09-01T00:00:00Z',
    completed_at: null,
  })),
  'http://localhost:8000/queue': QUEUE.map((q) => ({ ...bitemporal, ...q })),
  'http://localhost:8000/agenda/events': AGENDA_SLOTS.map((s) => ({
    ...bitemporal,
    code: s.code,
    name: s.name,
    importance: s.importance,
    status: s.status,
    tone: 'routine',
  })),
  'http://localhost:8000/guardian/wounds': [
    { ...bitemporal, id: 'w1', title: 'Wound 1', detail: 'Test wound', status: 'OPEN', tone: 'alert' },
  ],
  'http://localhost:8000/guardian/calibration': [],
  'http://localhost:8000/promotion/gates': PROMOTION_GATES,
  'http://localhost:8000/quantum/lanes': QUANTUM_LANES,
  'http://localhost:8000/batch/latest': {
    ...bitemporal, batch_id: 'PAPER-NONE', verdict_status: 'NO_BATCH', alert_array: [],
    pnl_summary: { pnl: 0, trades: 0, win_rate: 0 }, risk_metrics: {}, trades: [], pnl_history: [],
  },
  'http://localhost:8000/gates': [],
  'http://localhost:8000/charts/bars': { bars: [], derived: false, base_timeframe: '30m', source: 'NONE', notice: 'mock' },
  'http://localhost:8000/heartbeat/dashboard-local/freshness': {
    machine_id: 'dashboard-local', age_seconds: 0.2, is_fresh: true, warning_level: 'fresh',
    stale_since: null, last_update: '2026-09-11T00:00:00Z',
    cpu_percent: 12.5, memory_percent: 40.0, db_size_bytes: 1024, uptime_seconds: 60,
  },
};

global.fetch = vi.fn((url: string | Request, init?: RequestInit) => {
  const urlStr = typeof url === 'string' ? url : url.url;
  const baseUrl = urlStr.split('?')[0];

  if (baseUrl === 'http://localhost:8000/dev/issue-token' && init?.method === 'POST') {
    return Promise.resolve(
      new Response(JSON.stringify({ token: 'test-token-0000', machine_id: 'dashboard-local', expires_in_seconds: 86400 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  }

  const headers = (init?.headers ?? {}) as Record<string, string>;
  if (!headers['Fencing-Token'] || !headers['Machine-ID']) {
    return Promise.resolve(new Response(JSON.stringify({ detail: 'Missing auth headers' }), { status: 401 }));
  }

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
