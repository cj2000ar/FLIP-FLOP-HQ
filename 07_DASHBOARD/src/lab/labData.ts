/**
 * Lab research data — illustrative state derived from the Strategy Intelligence Master (2026-09-07).
 * Authority: ZERO. Nothing here grants LIVE authority, Passport status or broker routing.
 */

export type Tone = 'ok' | 'warn' | 'bad' | 'muted' | 'info';

export type EvidenceGrade =
  | 'CLIP_ONLY'
  | 'BACKTEST'
  | 'MARKET_REPLAY'
  | 'REALTIME_SIM'
  | 'BROKER_AUDITED'
  | 'SEALED_VALIDATED';

export type ExtractionStatus = 'NOT_STARTED' | 'UNREVIEWED' | 'IN_PROGRESS' | 'EXTRACTED' | 'VERIFIED';

export interface VaultItem {
  id: string;
  kind: 'video' | 'script' | 'paper';
  title: string;
  source: string;
  extraction: ExtractionStatus;
  evidence: EvidenceGrade;
  family: string[];
  dna: string;
  dataNeeds: string[];
}

export interface StrategyFamily {
  id: string;
  name: string;
  lineage: string;
  dna: string[];
}

export type ArenaState = 'CONTROL' | 'SHADOW_RUNNING' | 'PROMOTION_CANDIDATE' | 'REJECTED' | 'SURVIVOR';

export interface ArenaEntry {
  id: string;
  name: string;
  state: ArenaState;
  version: string;
  summary: string;
  metrics: { label: string; value: string }[];
  note: string;
}

export type ExperimentStatus = 'PRE_REGISTERED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'REJECTED';

export interface Experiment {
  id: string;
  name: string;
  hypothesis: string;
  parameters: string;
  datasetRole: 'IN_SAMPLE' | 'OUT_OF_SAMPLE' | 'HOLDOUT' | 'FORWARD' | 'DEV_ONLY';
  runs: number;
  status: ExperimentStatus;
  result: string;
  rejectionReason?: string;
  nextGate: string;
}

export const QUEUE_STATES = [
  'CAPTURED',
  'NEEDS_EXTRACTION',
  'DUPLICATE_DNA',
  'READY_FOR_SPEC',
  'BLOCKED_DATA',
  'READY_FOR_SHADOW_BUILD',
  'SHADOW_RUNNING',
  'REJECTED',
  'SURVIVOR',
  'PROMOTION_REVIEW',
] as const;
export type QueueState = (typeof QUEUE_STATES)[number];

export interface QueueItem {
  id: string;
  title: string;
  state: QueueState;
  why: string;
}

export interface AgendaSlot {
  code: string;
  name: string;
  importance: 'HIGH' | 'MEDIUM';
  status: 'NOT_CONNECTED';
}

export interface LedgerEntry {
  id: string;
  title: string;
  detail: string;
  status: string;
  tone: Tone;
}

export type GateStatus = 'PASS' | 'PARTIAL' | 'NOT_PROVEN' | 'PENDING';

export interface PromotionGateItem {
  id: number;
  name: string;
  requirement: string;
  status: GateStatus;
  evidence: string;
}

export interface QuantumLane {
  id: string;
  name: string;
  definition: string;
  status: string;
  tone: Tone;
}

export const AUTHORITY_BANNER = 'AUTHORITY=ZERO · LIVE=NO · BROKER_ORDERS=NONE · CONTROL_MUTATION=NONE';

export function toneFor(status: string): Tone {
  switch (status) {
    case 'PASS':
    case 'VERIFIED':
    case 'SURVIVOR':
    case 'CONTROL':
    case 'COMPLETED':
    case 'CORE NOW':
      return 'ok';
    case 'PARTIAL':
    case 'PENDING':
    case 'IN_PROGRESS':
    case 'SHADOW_RUNNING':
    case 'RUNNING':
    case 'BLOCKED_DATA':
    case 'BUILD SOON':
    case 'PRE_REGISTERED':
      return 'warn';
    case 'REJECTED':
    case 'FAILED':
    case 'BLOCKED':
    case 'NOT_PROVEN':
    case 'NO EVIDENCE':
    case 'NOT_CONNECTED':
      return 'bad';
    case 'PROMOTION_CANDIDATE':
    case 'PROMOTION_REVIEW':
    case 'READY_FOR_SHADOW_BUILD':
    case 'READY_FOR_SPEC':
      return 'info';
    default:
      return 'muted';
  }
}

// Type definitions only - data fetched from API
export const STRATEGY_FAMILIES: StrategyFamily[] = [];

export const MARKETS = {
  primary: ['NQ', 'MNQ'],
  priority: ['ES/MES', 'GC/MGC/1OZ', '6E/M6E'],
  later: ['CL/MCL/NG', 'RTY/M2K', 'YM/MYM', 'ZN/ZB/ZF'],
  rule: 'Each market needs its own math and Passport. NQ stops, ticks, sessions and risk are never copied to another product.',
};

// Type definitions only - data fetched from API
export const VAULT_ITEMS: VaultItem[] = [];

// Type definitions only - data fetched from API
export const ARENA: ArenaEntry[] = [];

// Type definitions only - data fetched from API
export const EXPERIMENTS: Experiment[] = [];

// Type definitions only - data fetched from API
export const QUEUE: QueueItem[] = [];

// Type definitions only - data fetched from API
export const AGENDA_SLOTS: AgendaSlot[] = [];

export const AGENDA_CONTRACT = [
  'event · country · category · importance',
  'exact time · timezone / DST',
  'actual · forecast · previous — revisions stored separately, original never deleted',
  'windows: before / during / after',
  'NQ/MNQ price path · volatility · volume · delta · liquidity response',
  'signals emitted / blocked / skipped',
  'opening shock · no-chase',
  'CONTROL result · challenger results',
  'human overrides',
  'evidence artifacts · freshness',
];

// Type definitions only - data fetched from API
export const AGENDA_FEEDS: LedgerEntry[] = [];

// Type definitions only - data fetched from API
export const GUARDIAN_CORE: LedgerEntry[] = [];

// Type definitions only - data fetched from API
export const WOUNDS: LedgerEntry[] = [];

// Type definitions only - data fetched from API
export const CALIBRATION: LedgerEntry[] = [];

// Type definitions only - data fetched from API
export const PROMOTION_GATES: PromotionGateItem[] = [];

// Type definitions only - data fetched from API
export const QUANTUM_LANES: QuantumLane[] = [];

export const QUANTUM_RULE =
  '"Quant Mirror" is a real project lineage. "Quantum" is a creative/technical direction with no recovered evidence of quantum hardware or an executed quantum algorithm improving trading. No technique gets credit for sounding advanced: same data, costs, splits and metrics as its classical baseline, or no promotion.';
