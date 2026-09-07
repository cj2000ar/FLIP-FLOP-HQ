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
export const ARENA: ArenaEntry[] = [
  {
    id: 'rr500-control',
    name: 'RR500_CONTROL',
    state: 'CONTROL',
    version: 'v3.3.1',
    summary: '12-trade baseline',
    metrics: [
      { label: 'Win Rate', value: '83.33%' },
      { label: 'Profit Factor', value: '7.5' },
      { label: 'Trades', value: '+416' },
      { label: 'PnL', value: '+$2,080' },
    ],
    note: 'Frozen CONTROL baseline'
  },
  {
    id: 'survivor-pair',
    name: 'SURVIVOR',
    state: 'SURVIVOR',
    version: 'v2.1',
    summary: 'Research-grade survivor pair',
    metrics: [
      { label: 'Correlation', value: '0.764' },
      { label: 'Status', value: 'APPROVED' },
    ],
    note: 'Holdout consumed/blocked'
  },
  {
    id: 'v03-vector',
    name: 'V03_VECTOR',
    state: 'REJECTED',
    version: 'v1.0',
    summary: 'V03 vector rejected',
    metrics: [
      { label: 'Status', value: 'REJECTED' },
    ],
    note: 'Holdout consumed/blocked'
  },
];

// Type definitions only - data fetched from API
export const EXPERIMENTS: Experiment[] = [
  { id: 'A', name: 'Exp A', hypothesis: 'H1', parameters: 'p1', datasetRole: 'IN_SAMPLE', runs: 0, status: 'PRE_REGISTERED', result: 'PASS', nextGate: 'G1' },
  { id: 'B', name: 'Exp B', hypothesis: 'H2', parameters: 'p2', datasetRole: 'IN_SAMPLE', runs: 0, status: 'PRE_REGISTERED', result: 'PASS', nextGate: 'G1' },
  { id: 'C', name: 'Exp C', hypothesis: 'H3', parameters: 'p3', datasetRole: 'IN_SAMPLE', runs: 0, status: 'PRE_REGISTERED', result: 'PASS', nextGate: 'G1' },
  { id: 'D', name: 'Exp D', hypothesis: 'H4', parameters: 'p4', datasetRole: 'IN_SAMPLE', runs: 0, status: 'PRE_REGISTERED', result: 'PASS', nextGate: 'G1' },
  { id: 'E', name: 'Exp E', hypothesis: 'H5', parameters: 'p5', datasetRole: 'IN_SAMPLE', runs: 0, status: 'PRE_REGISTERED', result: 'PASS', nextGate: 'G1' },
  { id: 'F', name: 'Exp F', hypothesis: 'H6', parameters: 'p6', datasetRole: 'HOLDOUT', runs: 0, status: 'FAILED', result: 'FAILED', rejectionReason: 'TECHNICALLY_INVALID_UNSCOREABLE', nextGate: 'G1' },
  { id: 'G', name: 'Exp G', hypothesis: 'H7', parameters: 'p7', datasetRole: 'IN_SAMPLE', runs: 0, status: 'PRE_REGISTERED', result: 'PASS', nextGate: 'G1' },
];

// Type definitions only - data fetched from API
export const QUEUE: QueueItem[] = [
  { id: 'q1', title: 'Queue 1', state: 'CAPTURED', why: 'Waiting processing' },
  { id: 'q2', title: 'Queue 2', state: 'READY_FOR_SHADOW_BUILD', why: 'Ready for build' },
];

// Type definitions only - data fetched from API
export const AGENDA_SLOTS: AgendaSlot[] = [
  { code: 'CPI', name: 'Consumer Price Index', importance: 'HIGH', status: 'NOT_CONNECTED' },
  { code: 'NFP', name: 'Non-Farm Payroll', importance: 'HIGH', status: 'NOT_CONNECTED' },
  { code: 'FOMC', name: 'FOMC Meeting', importance: 'HIGH', status: 'NOT_CONNECTED' },
  { code: 'PPI', name: 'Producer Price Index', importance: 'MEDIUM', status: 'NOT_CONNECTED' },
  { code: 'RETAIL', name: 'Retail Sales', importance: 'MEDIUM', status: 'NOT_CONNECTED' },
];

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
export const GUARDIAN_CORE: LedgerEntry[] = [
  { id: 'core1', title: 'CORE NOW', detail: 'Core path 1', status: 'CORE NOW', tone: 'ok' },
  { id: 'core2', title: 'CORE NOW', detail: 'Core path 2', status: 'CORE NOW', tone: 'ok' },
  { id: 'core3', title: 'CORE NOW', detail: 'Core path 3', status: 'CORE NOW', tone: 'ok' },
  { id: 'core4', title: 'CORE NOW', detail: 'Core path 4', status: 'CORE NOW', tone: 'ok' },
  { id: 'core5', title: 'CORE NOW', detail: 'Core path 5', status: 'CORE NOW', tone: 'ok' },
  { id: 'core6', title: 'CORE NOW', detail: 'Core path 6', status: 'CORE NOW', tone: 'ok' },
  { id: 'core7', title: 'CORE NOW', detail: 'Core path 7', status: 'CORE NOW', tone: 'ok' },
  { id: 'build1', title: 'BUILD SOON', detail: 'Build path 1', status: 'BUILD SOON', tone: 'warn' },
  { id: 'build2', title: 'BUILD SOON', detail: 'Build path 2', status: 'BUILD SOON', tone: 'warn' },
];

// Type definitions only - data fetched from API
export const WOUNDS: LedgerEntry[] = [
  { id: 'w1', title: 'Wound 1', detail: 'Test wound', status: 'OPEN', tone: 'bad' },
];

// Type definitions only - data fetched from API
export const CALIBRATION: LedgerEntry[] = [];

// Type definitions only - data fetched from API
export const PROMOTION_GATES: PromotionGateItem[] = [
  { id: 1, name: 'Gate 1', requirement: 'R1', status: 'NOT_PROVEN', evidence: 'E1' },
  { id: 2, name: 'Gate 2', requirement: 'R2', status: 'PASS', evidence: 'E2' },
  { id: 3, name: 'Gate 3', requirement: 'R3', status: 'NOT_PROVEN', evidence: 'E3' },
  { id: 4, name: 'Gate 4', requirement: 'R4', status: 'PASS', evidence: 'E4' },
  { id: 5, name: 'Gate 5', requirement: 'R5', status: 'NOT_PROVEN', evidence: 'E5' },
  { id: 6, name: 'Gate 6', requirement: 'R6', status: 'PASS', evidence: 'E6' },
  { id: 7, name: 'Gate 7', requirement: 'R7', status: 'PASS', evidence: 'E7' },
  { id: 8, name: 'Gate 8', requirement: 'R8', status: 'NOT_PROVEN', evidence: 'E8' },
  { id: 9, name: 'Gate 9', requirement: 'R9', status: 'PASS', evidence: 'E9' },
  { id: 10, name: 'Gate 10', requirement: 'R10', status: 'NOT_PROVEN', evidence: 'E10' },
  { id: 11, name: 'Gate 11', requirement: 'R11', status: 'PASS', evidence: 'E11' },
  { id: 12, name: 'Gate 12', requirement: 'R12', status: 'PASS', evidence: 'E12' },
  { id: 13, name: 'Gate 13', requirement: 'R13', status: 'NOT_PROVEN', evidence: 'E13' },
  { id: 14, name: 'Gate 14', requirement: 'R14', status: 'PASS', evidence: 'E14' },
  { id: 15, name: 'Gate 15', requirement: 'R15', status: 'NOT_PROVEN', evidence: 'E15' },
  { id: 16, name: 'Gate 16', requirement: 'R16', status: 'PASS', evidence: 'E16' },
];

// Type definitions only - data fetched from API
export const QUANTUM_LANES: QuantumLane[] = [];

export const QUANTUM_RULE =
  '"Quant Mirror" is a real project lineage. "Quantum" is a creative/technical direction with no recovered evidence of quantum hardware or an executed quantum algorithm improving trading. No technique gets credit for sounding advanced: same data, costs, splits and metrics as its classical baseline, or no promotion.';
