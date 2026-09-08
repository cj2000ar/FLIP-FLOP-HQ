"""
Gate 5 + Canary Executor Integration
Runs canary trades from Market Replay and feeds results to Guardian Gate 5.

Authority: ZERO (LOCKED IMMUTABLE)
Date: 2026-09-07
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from canary_executor import CanaryExecutor, CanaryStatus, CanaryResult
from guardian_engine import EvidenceRecord, VerdictType


class Gate5CanaryIntegration:
    """Bridges canary execution to Guardian Gate 5 evaluation"""

    def __init__(self):
        self.executor = CanaryExecutor()

    def run_canary_and_generate_evidence(
        self,
        strategy_name: str,
        instrument: str,
        trades_data: List[Dict],
        correlation_id: str
    ) -> Tuple[CanaryResult, EvidenceRecord]:
        """
        Run canary trades and generate evidence for Gate 5.
        Returns (canary_result, evidence_record).
        """
        # Execute canary
        status, result = self.executor.run_canary(
            strategy_name,
            instrument,
            trades_data,
            correlation_id
        )

        # Create evidence record for Gate 5
        evidence_id = uuid4()
        now = datetime.utcnow()

        observation = {
            "canary_id": result.canary_id,
            "status": result.status.value,
            "error_rate": result.error_rate,
            "latency_p99_ms": result.max_latency_ms,
            "avg_latency_ms": result.avg_latency_ms,
            "canary_result": "PASS" if result.status == CanaryStatus.PASS else "FAIL",
            "rollback_triggered": result.triggered_rollback,
            "total_trades": result.total_trades,
            "successful_trades": result.successful_trades,
            "failed_trades": result.failed_trades,
            "pnl_dollars": result.pnl_dollars,
        }

        # Compute evidence checksum
        observation_str = json.dumps(observation, sort_keys=True)
        import hashlib
        checksum = hashlib.sha256(observation_str.encode()).hexdigest()

        evidence = EvidenceRecord(
            evidence_id=evidence_id,
            evidence_type="CANARY_RUN",
            source_system="CANARY_EXECUTOR",
            observation=observation,
            observed_at=now,
            recorded_at=now,
            checksum=checksum
        )

        return result, evidence

    def get_canary_status_for_gate_5(self, canary_result: CanaryResult) -> VerdictType:
        """
        Convert canary result to Gate 5 verdict.
        Returns PASS, BLOCKED, or NOT_PROVEN.
        """
        if canary_result.status == CanaryStatus.PASS:
            return VerdictType.PASS

        if canary_result.triggered_rollback:
            return VerdictType.BLOCKED

        return VerdictType.NOT_PROVEN

    def generate_gate5_reasoning(self, canary_result: CanaryResult) -> str:
        """Generate human-readable reasoning for Gate 5 verdict"""
        lines = [
            f"Canary Execution (Gate 5):",
            f"  Canary ID: {canary_result.canary_id}",
            f"  Total Trades: {canary_result.total_trades}",
            f"  Successful: {canary_result.successful_trades}",
            f"  Failed: {canary_result.failed_trades}",
            f"  Error Rate: {canary_result.error_rate * 100:.1f}%",
            f"  Avg Latency: {canary_result.avg_latency_ms}ms",
            f"  Max Latency: {canary_result.max_latency_ms}ms",
            f"  P&L: ${canary_result.pnl_dollars:.2f}",
        ]

        if canary_result.status == CanaryStatus.PASS:
            lines.append(f"  Verdict: PASS (All checks passed)")
        elif canary_result.status == CanaryStatus.HIGH_ERROR_RATE:
            lines.append(f"  Verdict: BLOCKED (Error rate {canary_result.error_rate * 100:.1f}% > 5%)")
        elif canary_result.status == CanaryStatus.HIGH_LATENCY:
            lines.append(f"  Verdict: BLOCKED (Avg latency {canary_result.avg_latency_ms}ms > 200ms)")
        elif canary_result.status == CanaryStatus.CANARY_FAILED:
            lines.append(f"  Verdict: BLOCKED ({canary_result.failed_trades} trades failed)")
        elif canary_result.status == CanaryStatus.ROLLBACK_TRIGGERED:
            lines.append(f"  Verdict: BLOCKED (Rollback triggered)")

        return "\n".join(lines)
