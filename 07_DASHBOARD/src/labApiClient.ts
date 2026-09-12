/**
 * Lab API client — the only place the dashboard talks to private_read_api.
 *
 * Contract: 04_ENGINE/PRIVATE_READ_API_SPEC_DRAFT.md. The API returns bare arrays
 * with snake_case fields; the normalizers below map them onto the UI types in
 * ./lab/labData. Authority: ZERO — every call here is a GET (plus the dev token
 * issue, which is POST but grants nothing beyond read).
 */

import type {
  VaultItem,
  StrategyFamily,
  Experiment,
  QueueItem,
  AgendaSlot,
  LedgerEntry,
  ArenaEntry,
  PromotionGateItem,
  QuantumLane,
  Tone,
} from './lab/labData';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const env = ((import.meta as any).env ?? {}) as Record<string, string | undefined>;

export const API_BASE: string = env.VITE_API_BASE ?? 'http://localhost:8000';
export const MACHINE_ID: string = env.VITE_MACHINE_ID ?? 'dashboard-local';

const TOKEN_KEY = 'ff.fencing_token';

export class AuthError extends Error {
  constructor(message = 'Authentication required. Please refresh your session.') {
    super(message);
    this.name = 'AuthError';
  }
}

let cachedToken: string | null = null;
let tokenInFlight: Promise<string> | null = null; // concurrent mounts share one issue request

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private window, thumbnail capture) — token stays in memory */
  }
}

/**
 * Fencing token bootstrap. Dev/test: ask the API's /dev/issue-token (24h TTL).
 * Production: HP /validate_fencing_token replaces this — the API refuses
 * /dev/issue-token there, and the token must be provisioned into storage.
 */
async function getToken(): Promise<string> {
  if (cachedToken) return cachedToken;
  const stored = readStoredToken();
  if (stored) {
    cachedToken = stored;
    return stored;
  }
  if (!tokenInFlight) {
    tokenInFlight = (async () => {
      const res = await fetch(`${API_BASE}/dev/issue-token?machine_id=${encodeURIComponent(MACHINE_ID)}`, {
        method: 'POST',
      });
      if (!res.ok) throw new AuthError(`Token issue refused (${res.status}). Provision a fencing token.`);
      const body = (await res.json()) as { token?: string };
      if (!body.token) throw new AuthError('Token issue returned no token.');
      cachedToken = body.token;
      storeToken(body.token);
      return body.token;
    })().finally(() => {
      tokenInFlight = null;
    });
  }
  return tokenInFlight;
}

/** Resolve the current fencing token (issuing one in dev). Used by the monitor WebSocket. */
export function getFencingToken(): Promise<string> {
  return getToken();
}

export function resetToken(): void {
  cachedToken = null;
  storeToken(null);
}

async function fetchWithAuth(path: string, signal?: AbortSignal): Promise<Response> {
  const token = await getToken();
  return fetch(`${API_BASE}${path}`, {
    headers: { 'Machine-ID': MACHINE_ID, 'Fencing-Token': token },
    signal,
  });
}

/** GET a JSON resource. One retry with a fresh token on 401/403. */
export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res = await fetchWithAuth(path, signal);
  if (res.status === 401 || res.status === 403) {
    resetToken();
    res = await fetchWithAuth(path, signal);
  }
  if (res.status === 401 || res.status === 403) throw new AuthError();
  if (!res.ok) throw new Error(`${path}: ${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

/**
 * Authenticated streaming GET (SSE). Returns the raw Response so the caller can
 * read `body`. One retry with a fresh token on 401/403, like apiGet.
 */
export async function apiStream(path: string, signal?: AbortSignal): Promise<Response> {
  let res = await fetchWithAuth(path, signal);
  if (res.status === 401 || res.status === 403) {
    resetToken();
    res = await fetchWithAuth(path, signal);
  }
  if (res.status === 401 || res.status === 403) throw new AuthError();
  return res;
}

// ---------------------------------------------------------------------------
// API wire shapes (snake_case, per spec) and normalizers onto UI types
// ---------------------------------------------------------------------------

export interface ApiVaultItem {
  id: string;
  kind: string;
  title: string;
  source: string;
  extraction?: string | null;
  evidence?: string | null;
  family: string | string[];
  dna?: string | null;
  data_needs?: string | string[] | null;
}

export interface ApiStrategyFamily {
  id: string;
  name: string;
  lineage: string;
  dna: string | string[];
}

export interface ApiExperiment {
  id: string;
  name: string;
  hypothesis: string;
  parameters: string | Record<string, unknown>;
  dataset_role: string;
  runs: number;
  status: string;
  result?: string | null;
  rejection_reason?: string | null;
  next_gate?: string | null;
}

export interface ApiQueueItem {
  id: string;
  title: string;
  state: string;
  why: string;
}

export interface ApiEventSlot {
  code: string;
  name: string;
  importance: string;
  status: string;
}

export interface ApiWound {
  id: string;
  title: string;
  detail: string;
  status: string;
  tone?: string | null;
}

export interface ApiCalibrationEntry {
  id: string;
  prediction: string;
  actual: string;
  score: number;
  notes?: string | null;
}

const splitList = (v: string | string[] | null | undefined): string[] => {
  if (!v) return [];
  if (Array.isArray(v)) return v;
  return v
    .split(/[,;·]\s*/)
    .map((s) => s.trim())
    .filter(Boolean);
};

/** API tones (alert / learning / reference / routine) → UI tones. */
export function toneFromApi(tone: string | null | undefined, fallback: Tone = 'muted'): Tone {
  switch ((tone ?? '').toLowerCase()) {
    case 'alert':
    case 'bad':
      return 'bad';
    case 'learning':
    case 'warn':
      return 'warn';
    case 'ok':
      return 'ok';
    case 'info':
      return 'info';
    case 'reference':
    case 'routine':
    case 'muted':
      return 'muted';
    default:
      return fallback;
  }
}

export const toVaultItem = (v: ApiVaultItem): VaultItem => ({
  id: v.id,
  kind: (v.kind as VaultItem['kind']) ?? 'note',
  title: v.title,
  source: v.source,
  extraction: v.extraction ?? 'NOT_STARTED',
  evidence: v.evidence ?? 'CLIP_ONLY',
  family: Array.isArray(v.family) ? v.family : [v.family],
  dna: v.dna ?? '',
  dataNeeds: splitList(v.data_needs),
});

export const toStrategyFamily = (f: ApiStrategyFamily): StrategyFamily => ({
  id: f.id,
  name: f.name,
  lineage: f.lineage,
  dna: splitList(f.dna),
});

export const toExperiment = (e: ApiExperiment): Experiment => ({
  id: e.id,
  name: e.name,
  hypothesis: e.hypothesis,
  parameters:
    typeof e.parameters === 'string'
      ? e.parameters
      : Object.entries(e.parameters ?? {})
          .map(([k, v]) => `${k}=${String(v)}`)
          .join(' · '),
  datasetRole: e.dataset_role,
  runs: e.runs,
  status: e.status as Experiment['status'],
  result: e.result ?? '—',
  rejectionReason: e.rejection_reason ?? undefined,
  nextGate: e.next_gate ?? '—',
});

export const toQueueItem = (q: ApiQueueItem): QueueItem => ({
  id: q.id,
  title: q.title,
  state: q.state as QueueItem['state'],
  why: q.why,
});

export const toAgendaSlot = (s: ApiEventSlot): AgendaSlot => ({
  code: s.code,
  name: s.name,
  importance: s.importance,
  status: s.status,
});

export const toWoundEntry = (w: ApiWound): LedgerEntry => ({
  id: w.id,
  title: w.title,
  detail: w.detail,
  status: w.status,
  tone: toneFromApi(w.tone, 'bad'),
});

export const toCalibrationEntry = (c: ApiCalibrationEntry): LedgerEntry => ({
  id: c.id,
  title: c.prediction,
  detail: c.notes ? `${c.actual} — ${c.notes}` : c.actual,
  status: `${Math.round(c.score * 100)}%`,
  tone: c.score >= 0.9 ? 'ok' : c.score >= 0.7 ? 'warn' : 'bad',
});

// Arena, promotion gates and quantum lanes already travel in UI shape.
export type ApiArenaEntry = ArenaEntry;
export type ApiPromotionGate = PromotionGateItem;
export type ApiQuantumLane = QuantumLane;
