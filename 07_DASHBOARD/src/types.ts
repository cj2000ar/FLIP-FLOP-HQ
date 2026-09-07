/**
 * FlipFlop HQ Phase 2 UI Type Definitions
 * Authority: ZERO (hard-locked, immutable)
 * Live: OFF (paper-only, no real orders)
 */

export type FormFactor = 'phone' | 'tablet' | 'desktop';
export type TruthAge = 'fresh' | 'warning' | 'stale';
export type GateVerdict = 'PASS' | 'BLOCKED' | 'NOT_PROVEN';
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type BatchStatus = 'PENDING' | 'PROCESSING' | 'CLOSED' | 'ARCHIVED' | 'APPROVED' | 'BLOCKED';

/**
 * Authority Tuple (Immutable)
 * AUTHORITY = ZERO (non-negotiable hard lock)
 * LIVE = OFF (paper-only)
 */
export interface AuthorityTuple {
  authority: 'ZERO';
  live: false;
  broker_orders: 'NONE';
  control_mutation: 'NONE';
  approval_id: string;
}

/**
 * Gate Verdict Record (Immutable)
 * Each of 8 gates produces a verdict
 */
export interface GateDecision {
  gate_id: number; // 1-8
  gate_name: string;
  verdict: GateVerdict;
  evidence_id: string;
  event_time: number; // Unix timestamp
  knowledge_time: number; // Unix timestamp
  truth_age_seconds: number;
  details?: string;
}

/**
 * Guardian State Snapshot
 * Read-only display of all 8 gates + verdicts
 */
export interface GuardianStateSnapshot {
  state_id: string;
  phase: string;
  authority: 'ZERO';
  gates: GateDecision[];
  final_verdict: GateVerdict;
  promotion_ready: boolean;
  truth_age_seconds: number;
  evidence_status: string;
}

/**
 * Truth Bar State
 * Tracks age of evidence for stale detection
 * < 10s: GREEN (fresh)
 * 10-30s: YELLOW (warning, desaturate)
 * > 30s: RED (stale block, full desaturation)
 */
export interface TruthBarState {
  truth_id: string;
  is_fresh: boolean;
  age_seconds: number;
  stale_since?: number;
  warning_level: TruthAge;
  last_update: number;
}

/**
 * Health Indicator State
 * Machine heartbeat, clock, fencing token
 */
export interface HealthIndicatorState {
  health_id: string;
  heartbeat_age_seconds: number;
  clock_offset_ms: number;
  fencing_token_valid: boolean;
  restart_detected: boolean;
  truth_age_seconds: number;
}

/**
 * Alert Record (Immutable)
 * Ranked by severity
 */
export interface AlertRecord {
  alert_id: string;
  batch_id: string;
  severity: AlertSeverity;
  alert_type: string;
  message: string;
  timestamp: number;
  escalation_flag: boolean;
  resolution_status: 'open' | 'resolved' | 'dismissed';
}

/**
 * Batch Status Display
 * Read-only aggregate of batch verdict + alerts + summary
 */
export interface BatchStatusSnapshot {
  batch_snapshot_id: string;
  verdict_status: BatchStatus;
  alert_array: AlertRecord[];
  report_summary: DayReport;
  guardian_gate_results: GateDecision[];
}

/**
 * Day Report
 * Trade summary, P&L, risk metrics
 */
export interface DayReport {
  report_id: string;
  batch_id: string;
  trade_count: number;
  pnl_summary: {
    gross_pnl: number;
    net_pnl: number;
    currency: string;
  };
  risk_metrics: {
    max_drawdown_pct: number;
    sharpe_ratio: number;
    win_rate_pct: number;
  };
  alert_count: number;
  export_time: number;
}

/**
 * Archive Entry
 * Immutable cartridge for historical data
 */
export interface ArchiveEntry {
  archive_record_id: string;
  batch_id: string;
  storage_path: string;
  retention_years: number;
  immutable_hash: string;
  retrieval_metadata: Record<string, unknown>;
  created_at: number;
}

/**
 * Screen Context
 * Current viewport and form factor
 */
export interface ScreenContext {
  formFactor: FormFactor;
  width: number;
  height: number;
  prefersReducedMotion: boolean;
  darkMode: boolean;
}

/**
 * Component Props for main UI container
 */
export interface ScreenComponentProps {
  guardianState: GuardianStateSnapshot;
  truthBar: TruthBarState;
  healthIndicator: HealthIndicatorState;
  batchStatus: BatchStatusSnapshot;
  alerts: AlertRecord[];
  archives: ArchiveEntry[];
  onAlertDismiss?: (alertId: string) => void;
  onRefresh?: () => void;
  isAdmin?: boolean;
}

/**
 * Mock data generators for testing
 */
export const createMockGuardianState = (): GuardianStateSnapshot => ({
  state_id: 'state-001',
  phase: 'evaluation',
  authority: 'ZERO',
  gates: Array.from({ length: 8 }, (_, i) => ({
    gate_id: i + 1,
    gate_name: [
      'SCHEMA_AND_IDENTITY',
      'HASH_INTEGRITY',
      'AUTHORITY_POLICY_COMPLIANCE',
      'MACHINE_HEALTH_AND_READINESS',
      'CANARY_EXECUTION',
      'EVIDENCE_CONSISTENCY',
      'FRESHNESS_AND_STALENESS',
      'FINAL_ARBITER',
    ][i],
    verdict: 'PASS' as GateVerdict,
    evidence_id: `evidence-${i + 1}`,
    event_time: Date.now(),
    knowledge_time: Date.now(),
    truth_age_seconds: 5,
    details: 'Gate passed all checks',
  })),
  final_verdict: 'PASS',
  promotion_ready: true,
  truth_age_seconds: 5,
  evidence_status: 'complete',
});

export const createMockTruthBar = (age_seconds: number = 5): TruthBarState => ({
  truth_id: 'truth-001',
  is_fresh: age_seconds < 10,
  age_seconds,
  stale_since: age_seconds > 30 ? Date.now() : undefined,
  warning_level: age_seconds < 10 ? 'fresh' : age_seconds < 30 ? 'warning' : 'stale',
  last_update: Date.now(),
});

export const createMockHealthIndicator = (): HealthIndicatorState => ({
  health_id: 'health-001',
  heartbeat_age_seconds: 5,
  clock_offset_ms: 2,
  fencing_token_valid: true,
  restart_detected: false,
  truth_age_seconds: 5,
});

export const createMockBatchStatus = (): BatchStatusSnapshot => ({
  batch_snapshot_id: 'batch-001',
  verdict_status: 'APPROVED',
  alert_array: [
    {
      alert_id: 'alert-1',
      batch_id: 'batch-001',
      severity: 'info',
      alert_type: 'completion',
      message: 'Batch processing completed successfully',
      timestamp: Date.now(),
      escalation_flag: false,
      resolution_status: 'resolved',
    },
  ],
  report_summary: {
    report_id: 'report-001',
    batch_id: 'batch-001',
    trade_count: 42,
    pnl_summary: {
      gross_pnl: 15000,
      net_pnl: 12500,
      currency: 'USD',
    },
    risk_metrics: {
      max_drawdown_pct: 2.5,
      sharpe_ratio: 1.8,
      win_rate_pct: 62,
    },
    alert_count: 1,
    export_time: Date.now(),
  },
  guardian_gate_results: Array.from({ length: 8 }, (_, i) => ({
    gate_id: i + 1,
    gate_name: [
      'SCHEMA_AND_IDENTITY',
      'HASH_INTEGRITY',
      'AUTHORITY_POLICY_COMPLIANCE',
      'MACHINE_HEALTH_AND_READINESS',
      'CANARY_EXECUTION',
      'EVIDENCE_CONSISTENCY',
      'FRESHNESS_AND_STALENESS',
      'FINAL_ARBITER',
    ][i],
    verdict: 'PASS' as GateVerdict,
    evidence_id: `evidence-${i + 1}`,
    event_time: Date.now(),
    knowledge_time: Date.now(),
    truth_age_seconds: 5,
  })),
});

export const createMockArchiveEntries = (): ArchiveEntry[] => [
  {
    archive_record_id: 'archive-001',
    batch_id: 'batch-001',
    storage_path: '/archive/2026/09/07/batch-001.tar.gz',
    retention_years: 7,
    immutable_hash: 'sha256:abcd1234',
    retrieval_metadata: { format: 'tar.gz', size_bytes: 1048576 },
    created_at: Date.now(),
  },
];
