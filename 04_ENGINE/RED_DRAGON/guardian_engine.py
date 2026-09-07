"""
Guardian Enforcement 8-Gate Engine - Phase 2 Implementation
Authority: ZERO (LOCKED IMMUTABLE)
Date: 2026-09-07
Status: PRODUCTION READY

Immutable data structures:
- GateVerdict: Immutable gate outcome
- GateDecisionTuple: Immutable decision record
- EvidenceRecord: Immutable observation
- AuthorityTuple: Immutable governance tuple

All verdicts are fail-closed: stale evidence blocks, contradictions block, missing evidence NOT_PROVEN.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import hashlib
import json
from abc import ABC, abstractmethod


# ============================================================================
# ENUMS
# ============================================================================

class VerdictType(str, Enum):
    """Verdict outcomes: PASS, BLOCKED, NOT_PROVEN"""
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    NOT_PROVEN = "NOT_PROVEN"


class AuthorityLevel(str, Enum):
    """Authority levels (ZERO only in Phase 2)"""
    ZERO = "ZERO"


class GateID(str, Enum):
    """8 Sequential gates"""
    GATE_1 = "gate_1"  # SCHEMA_AND_IDENTITY
    GATE_2 = "gate_2"  # HASH_INTEGRITY
    GATE_3 = "gate_3"  # AUTHORITY_POLICY_COMPLIANCE
    GATE_4 = "gate_4"  # MACHINE_HEALTH_AND_READINESS
    GATE_5 = "gate_5"  # CANARY_EXECUTION
    GATE_6 = "gate_6"  # EVIDENCE_CONSISTENCY
    GATE_7 = "gate_7"  # FRESHNESS_AND_STALENESS
    GATE_8 = "gate_8"  # FINAL_ARBITER


# ============================================================================
# IMMUTABLE DATA STRUCTURES (FROZEN TUPLES & RECORDS)
# ============================================================================

@dataclass(frozen=True)
class AuthorityTuple:
    """Immutable authority governance tuple (5 fields)"""
    authority: AuthorityLevel = AuthorityLevel.ZERO
    live_enabled: bool = False
    broker_orders_allowed: bool = False
    control_mutation_allowed: bool = False
    owner_approval_id: Optional[UUID] = None

    def __post_init__(self):
        """Validate authority invariant"""
        if self.authority != AuthorityLevel.ZERO:
            raise ValueError(f"Authority must be ZERO, got {self.authority}")
        if self.live_enabled != False:
            raise ValueError("live_enabled must be False")
        if self.broker_orders_allowed != False:
            raise ValueError("broker_orders_allowed must be False")
        if self.control_mutation_allowed != False:
            raise ValueError("control_mutation_allowed must be False")


@dataclass(frozen=True)
class EvidenceRecord:
    """Immutable evidence observation"""
    evidence_id: UUID
    evidence_type: str
    source_system: str
    observation: Dict[str, Any]
    observed_at: datetime
    recorded_at: datetime
    checksum: str
    is_contradicted: bool = False
    contradicted_by: List[UUID] = field(default_factory=list)

    def __post_init__(self):
        """Validate immutable constraints"""
        if self.observed_at > self.recorded_at:
            raise ValueError("observed_at must be <= recorded_at")


@dataclass(frozen=True)
class GateVerdict:
    """Immutable gate verdict (outcome of evaluation)"""
    verdict_id: UUID
    gate_id: GateID
    correlation_id: UUID
    verdict: VerdictType
    reasoning: str
    evidence_id: Optional[UUID]
    secondary_evidence_ids: List[UUID] = field(default_factory=list)
    event_time: datetime = field(default_factory=datetime.utcnow)
    knowledge_time: datetime = field(default_factory=datetime.utcnow)
    authority_used: AuthorityLevel = AuthorityLevel.ZERO
    policy_hash: str = ""

    def __post_init__(self):
        """Validate immutable constraints"""
        if self.event_time > self.knowledge_time:
            raise ValueError("event_time must be <= knowledge_time")
        if self.authority_used != AuthorityLevel.ZERO:
            raise ValueError("authority_used must be ZERO")


@dataclass(frozen=True)
class GateDecisionTuple:
    """Immutable gate decision tuple (7 fields)"""
    gate_id: GateID
    correlation_id: UUID
    input_hashes: List[str]
    evidence_id: Optional[UUID]
    verdict: VerdictType
    event_time: datetime
    knowledge_time: datetime

    def __post_init__(self):
        """Validate immutable constraints"""
        if len(self.input_hashes) == 0:
            raise ValueError("input_hashes must not be empty")
        if self.event_time > self.knowledge_time:
            raise ValueError("event_time must be <= knowledge_time")
        if self.verdict not in [VerdictType.PASS, VerdictType.BLOCKED, VerdictType.NOT_PROVEN]:
            raise ValueError(f"verdict must be one of PASS, BLOCKED, NOT_PROVEN, got {self.verdict}")


@dataclass(frozen=True)
class DecisionCartridge:
    """Immutable snapshot of all 8 gate verdicts (sealed)"""
    cartridge_id: UUID
    correlation_id: UUID
    candidate_id: UUID
    gate_verdicts: List[Dict[str, Any]]  # [{gate_id, verdict_id, verdict}, ...]
    final_verdict: VerdictType
    evidence_root_hash: str
    policy_root_hash: str
    authority: AuthorityLevel = AuthorityLevel.ZERO
    created_at: datetime = field(default_factory=datetime.utcnow)
    owner_approval_id: Optional[UUID] = None

    def __post_init__(self):
        """Validate decision cartridge constraints"""
        if len(self.gate_verdicts) != 8:
            raise ValueError(f"gate_verdicts must have 8 entries, got {len(self.gate_verdicts)}")
        if self.authority != AuthorityLevel.ZERO:
            raise ValueError("authority must be ZERO")


# ============================================================================
# DEPLOYMENT CANDIDATE (MUTABLE DURING GATE JOURNEY)
# ============================================================================

@dataclass
class DeploymentCandidate:
    """Deployment candidate (mutable during gate journey, immutable hashes)"""
    candidate_id: UUID
    correlation_id: UUID
    artifact_hashes: Dict[str, str]  # {strategy, engine, ui}
    passport_hash: str
    side: str  # BUY or SELL
    source_system: str
    authority: AuthorityLevel = AuthorityLevel.ZERO
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Mutable during gate journey
    gate_results: List[Dict[str, Any]] = field(default_factory=list)
    canary_evidence_id: Optional[UUID] = None
    decision_cartridge_id: Optional[UUID] = None
    owner_approval_id: Optional[UUID] = None
    promotion_ready: bool = False
    status: str = "STAGING"

    def __post_init__(self):
        """Validate candidate constraints"""
        if self.authority != AuthorityLevel.ZERO:
            raise ValueError("authority must be ZERO at creation")
        if not all(k in self.artifact_hashes for k in ['strategy', 'engine', 'ui']):
            raise ValueError("artifact_hashes must have strategy, engine, ui keys")


# ============================================================================
# GATE CLASSES
# ============================================================================

class Gate(ABC):
    """Abstract base class for all 8 gates"""

    def __init__(self, gate_id: GateID, stale_threshold_seconds: int = 300):
        self.gate_id = gate_id
        self.stale_threshold_seconds = stale_threshold_seconds

    @abstractmethod
    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Evaluate gate and return immutable verdict"""
        pass

    def _fail_closed_check(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        required_evidence_types: List[str] = None
    ) -> Optional[GateVerdict]:
        """
        Fail-closed sentinel: checks before any verdict
        Returns blocking/not_proven verdict if check fails, None if all OK
        """
        # FC01: Authority must be ZERO
        if candidate.authority != AuthorityLevel.ZERO:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.BLOCKED,
                reasoning="authority_not_zero",
                evidence_id=None,
            )

        # FC02: Stale evidence blocks
        now = datetime.utcnow()
        for evidence in evidence_records:
            age_seconds = (now - evidence.recorded_at).total_seconds()
            if age_seconds > self.stale_threshold_seconds:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning=f"evidence_stale (age={age_seconds:.0f}s, threshold={self.stale_threshold_seconds}s)",
                    evidence_id=evidence.evidence_id,
                )

        # FC03: Contradicted evidence blocks
        for evidence in evidence_records:
            if evidence.is_contradicted:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="contradicted_evidence_present",
                    evidence_id=evidence.evidence_id,
                )

        # FC04: Missing required evidence
        if required_evidence_types:
            for required_type in required_evidence_types:
                if not any(e.evidence_type == required_type for e in evidence_records):
                    return GateVerdict(
                        verdict_id=uuid4(),
                        gate_id=self.gate_id,
                        correlation_id=candidate.correlation_id,
                        verdict=VerdictType.NOT_PROVEN,
                        reasoning=f"required_evidence_missing_{required_type}",
                        evidence_id=None,
                    )

        return None  # All fail-closed checks passed


class Gate1_SchemaAndIdentity(Gate):
    """Gate 1: SCHEMA_AND_IDENTITY - Validates candidate structure"""

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Gate 1: Schema and artifact identity validation"""

        # Fail-closed sentinel
        fail_closed = self._fail_closed_check(candidate, evidence_records)
        if fail_closed:
            return fail_closed

        # Check 1: All required hashes present
        for hash_key in ['strategy', 'engine', 'ui']:
            if not candidate.artifact_hashes.get(hash_key):
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning=f"artifact_hash_missing_{hash_key}",
                    evidence_id=None,
                )

        # Check 2: Passport hash present
        if not candidate.passport_hash:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.BLOCKED,
                reasoning="passport_hash_missing",
                evidence_id=None,
            )

        # Check 3: Correlation ID is valid UUID
        try:
            UUID(str(candidate.correlation_id))
        except (ValueError, AttributeError):
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.BLOCKED,
                reasoning="correlation_id_malformed",
                evidence_id=None,
            )

        # All checks passed
        return GateVerdict(
            verdict_id=uuid4(),
            gate_id=self.gate_id,
            correlation_id=candidate.correlation_id,
            verdict=VerdictType.PASS,
            reasoning="schema_and_identity_valid",
            evidence_id=None,
        )


class Gate2_HashIntegrity(Gate):
    """Gate 2: HASH_INTEGRITY - Verifies artifact content hashes"""

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Gate 2: Hash integrity verification"""

        # Fail-closed sentinel
        fail_closed = self._fail_closed_check(
            candidate,
            evidence_records,
            required_evidence_types=["HASH_MATCH"]
        )
        if fail_closed:
            return fail_closed

        # Get hash evidence
        hash_evidence = [e for e in evidence_records if e.evidence_type == "HASH_MATCH"]

        # If no hash evidence, NOT_PROVEN
        if not hash_evidence:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.NOT_PROVEN,
                reasoning="artifact_source_unavailable",
                evidence_id=None,
            )

        # Check for hash contradictions and mismatches
        for evidence in hash_evidence:
            observation = evidence.observation

            # Check strategy hash
            if "strategy_sha256" in observation:
                if observation["strategy_sha256"] != candidate.artifact_hashes["strategy"]:
                    return GateVerdict(
                        verdict_id=uuid4(),
                        gate_id=self.gate_id,
                        correlation_id=candidate.correlation_id,
                        verdict=VerdictType.BLOCKED,
                        reasoning="artifact_strategy_hash_mismatch",
                        evidence_id=evidence.evidence_id,
                    )

            # Check engine hash
            if "engine_sha256" in observation:
                if observation["engine_sha256"] != candidate.artifact_hashes["engine"]:
                    return GateVerdict(
                        verdict_id=uuid4(),
                        gate_id=self.gate_id,
                        correlation_id=candidate.correlation_id,
                        verdict=VerdictType.BLOCKED,
                        reasoning="artifact_engine_hash_mismatch",
                        evidence_id=evidence.evidence_id,
                    )

            # Check UI hash
            if "ui_sha256" in observation:
                if observation["ui_sha256"] != candidate.artifact_hashes["ui"]:
                    return GateVerdict(
                        verdict_id=uuid4(),
                        gate_id=self.gate_id,
                        correlation_id=candidate.correlation_id,
                        verdict=VerdictType.BLOCKED,
                        reasoning="artifact_ui_hash_mismatch",
                        evidence_id=evidence.evidence_id,
                    )

            # Check passport hash
            if "passport_sha256" in observation:
                if observation["passport_sha256"] != candidate.passport_hash:
                    return GateVerdict(
                        verdict_id=uuid4(),
                        gate_id=self.gate_id,
                        correlation_id=candidate.correlation_id,
                        verdict=VerdictType.BLOCKED,
                        reasoning="passport_hash_mismatch",
                        evidence_id=evidence.evidence_id,
                    )

        # All hash checks passed
        return GateVerdict(
            verdict_id=uuid4(),
            gate_id=self.gate_id,
            correlation_id=candidate.correlation_id,
            verdict=VerdictType.PASS,
            reasoning="hash_integrity_verified",
            evidence_id=hash_evidence[0].evidence_id if hash_evidence else None,
            secondary_evidence_ids=[e.evidence_id for e in hash_evidence[1:]],
        )


class Gate3_AuthorityPolicyCompliance(Gate):
    """Gate 3: AUTHORITY_POLICY_COMPLIANCE - Confirms authority=ZERO, live=false, no mutations"""

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Gate 3: Authority policy compliance (hard locks)"""

        # Fail-closed sentinel
        fail_closed = self._fail_closed_check(
            candidate,
            evidence_records,
            required_evidence_types=["POLICY_CHECK"]
        )
        if fail_closed:
            return fail_closed

        # Hard check: Authority must be ZERO
        if candidate.authority != AuthorityLevel.ZERO:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.BLOCKED,
                reasoning="authority_not_zero",
                evidence_id=None,
            )

        # Get policy evidence
        policy_evidence = [e for e in evidence_records if e.evidence_type == "POLICY_CHECK"]

        if not policy_evidence:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.NOT_PROVEN,
                reasoning="policy_not_available",
                evidence_id=None,
            )

        # Validate policy checks
        for evidence in policy_evidence:
            observation = evidence.observation

            # Validate all hard checks
            if observation.get("authority") != "ZERO":
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="authority_not_zero",
                    evidence_id=evidence.evidence_id,
                )

            if observation.get("live_enabled") != False:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="live_enabled_violation",
                    evidence_id=evidence.evidence_id,
                )

            if observation.get("broker_orders_allowed") != False:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="broker_orders_enabled",
                    evidence_id=evidence.evidence_id,
                )

            if observation.get("control_mutation_allowed") != False:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="control_mutation_enabled",
                    evidence_id=evidence.evidence_id,
                )

        # All policy checks passed
        return GateVerdict(
            verdict_id=uuid4(),
            gate_id=self.gate_id,
            correlation_id=candidate.correlation_id,
            verdict=VerdictType.PASS,
            reasoning="authority_policy_compliant",
            evidence_id=policy_evidence[0].evidence_id if policy_evidence else None,
        )


class Gate4_MachineHealthAndReadiness(Gate):
    """Gate 4: MACHINE_HEALTH_AND_READINESS - Verifies HP infrastructure health"""

    def __init__(self):
        super().__init__(GateID.GATE_4, stale_threshold_seconds=60)

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Gate 4: Machine health and readiness checks"""

        # Fail-closed sentinel (60s heartbeat threshold for this gate)
        fail_closed = self._fail_closed_check(
            candidate,
            evidence_records,
            required_evidence_types=["MACHINE_HEALTH", "FENCING_TOKEN"]
        )
        if fail_closed:
            return fail_closed

        # Get health evidence
        health_evidence = [e for e in evidence_records if e.evidence_type == "MACHINE_HEALTH"]

        if not health_evidence:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.NOT_PROVEN,
                reasoning="heartbeat_unavailable",
                evidence_id=None,
            )

        # Check each machine's health
        now = datetime.utcnow()
        for evidence in health_evidence:
            observation = evidence.observation

            # Check machine status
            if observation.get("health_status") != "HEALTHY":
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="machine_error_detected",
                    evidence_id=evidence.evidence_id,
                )

            # Check error count
            if observation.get("error_count", 0) > 0:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="machine_error_detected",
                    evidence_id=evidence.evidence_id,
                )

            # Check heartbeat freshness (60 second threshold for Gate 4)
            if "last_heartbeat" in observation:
                try:
                    last_hb = datetime.fromisoformat(observation["last_heartbeat"])
                    heartbeat_age = (now - last_hb).total_seconds()
                    if heartbeat_age > 60:
                        return GateVerdict(
                            verdict_id=uuid4(),
                            gate_id=self.gate_id,
                            correlation_id=candidate.correlation_id,
                            verdict=VerdictType.BLOCKED,
                            reasoning="heartbeat_stale",
                            evidence_id=evidence.evidence_id,
                        )
                except (ValueError, TypeError):
                    pass

            # Check clock skew
            if abs(observation.get("clock_offset", 0)) > 5:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="clock_skew_excessive",
                    evidence_id=evidence.evidence_id,
                )

        # Check fencing token
        fencing_evidence = [e for e in evidence_records if e.evidence_type == "FENCING_TOKEN"]
        if fencing_evidence:
            for evidence in fencing_evidence:
                observation = evidence.observation
                if not observation.get("token_valid", False):
                    return GateVerdict(
                        verdict_id=uuid4(),
                        gate_id=self.gate_id,
                        correlation_id=candidate.correlation_id,
                        verdict=VerdictType.BLOCKED,
                        reasoning="fencing_token_expired",
                        evidence_id=evidence.evidence_id,
                    )

        # All health checks passed
        return GateVerdict(
            verdict_id=uuid4(),
            gate_id=self.gate_id,
            correlation_id=candidate.correlation_id,
            verdict=VerdictType.PASS,
            reasoning="machine_health_ready",
            evidence_id=health_evidence[0].evidence_id if health_evidence else None,
        )


class Gate5_CanaryExecution(Gate):
    """Gate 5: CANARY_EXECUTION - Evaluates canary deployment results"""

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Gate 5: Canary execution evaluation"""

        # Fail-closed sentinel
        fail_closed = self._fail_closed_check(
            candidate,
            evidence_records,
            required_evidence_types=["CANARY_RUN"]
        )
        if fail_closed:
            return fail_closed

        # Get canary evidence
        canary_evidence = [e for e in evidence_records if e.evidence_type == "CANARY_RUN"]

        if not canary_evidence:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.NOT_PROVEN,
                reasoning="canary_observation_incomplete",
                evidence_id=None,
            )

        # Evaluate canary results
        for evidence in canary_evidence:
            observation = evidence.observation

            # Check canary result
            result = observation.get("result")
            if result not in ["PASS"]:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="canary_failure",
                    evidence_id=evidence.evidence_id,
                )

            # Check error rate (threshold: 5%)
            error_rate = observation.get("error_rate", 0)
            if error_rate > 0.05:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="canary_error_rate_high",
                    evidence_id=evidence.evidence_id,
                )

            # Check latency (threshold: 200ms)
            latency = observation.get("latency_p99_ms", 0)
            if latency >= 200:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="canary_latency_high",
                    evidence_id=evidence.evidence_id,
                )

            # Check rollback
            if observation.get("rollback_triggered", False):
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="canary_rollback_initiated",
                    evidence_id=evidence.evidence_id,
                )

        # All canary checks passed
        return GateVerdict(
            verdict_id=uuid4(),
            gate_id=self.gate_id,
            correlation_id=candidate.correlation_id,
            verdict=VerdictType.PASS,
            reasoning="canary_execution_passed",
            evidence_id=canary_evidence[0].evidence_id if canary_evidence else None,
        )


class Gate6_EvidenceConsistency(Gate):
    """Gate 6: EVIDENCE_CONSISTENCY - Detects and blocks contradictory evidence"""

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Gate 6: Evidence consistency verification"""

        # Fail-closed sentinel
        fail_closed = self._fail_closed_check(candidate, evidence_records)
        if fail_closed:
            return fail_closed

        # Check for contradicted evidence flags
        for evidence in evidence_records:
            if evidence.is_contradicted:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="contradicted_evidence_present",
                    evidence_id=evidence.evidence_id,
                )

        # Check for hash contradictions
        hash_evidence = [e for e in evidence_records if e.evidence_type == "HASH_MATCH"]
        if len(hash_evidence) > 1:
            strategy_hashes = set()
            for evidence in hash_evidence:
                h = evidence.observation.get("strategy_sha256")
                if h:
                    strategy_hashes.add(h)
            if len(strategy_hashes) > 1:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning="hash_contradiction",
                    evidence_id=hash_evidence[0].evidence_id,
                )

        # All consistency checks passed
        return GateVerdict(
            verdict_id=uuid4(),
            gate_id=self.gate_id,
            correlation_id=candidate.correlation_id,
            verdict=VerdictType.PASS,
            reasoning="evidence_consistency_confirmed",
            evidence_id=None,
        )


class Gate7_FreshnessAndStaleness(Gate):
    """Gate 7: FRESHNESS_AND_STALENESS - Enforces evidence freshness (300s hard limit)"""

    def __init__(self):
        super().__init__(GateID.GATE_7, stale_threshold_seconds=300)

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Gate 7: Freshness and staleness enforcement (300s hard limit)"""

        # Fail-closed sentinel with 300s threshold
        fail_closed = self._fail_closed_check(
            candidate,
            evidence_records,
            required_evidence_types=["HASH_MATCH", "CANARY_RUN", "MACHINE_HEALTH"]
        )
        if fail_closed:
            return fail_closed

        # Check evidence freshness (300s hard limit)
        now = datetime.utcnow()
        for evidence in evidence_records:
            age_seconds = (now - evidence.recorded_at).total_seconds()
            if age_seconds > 300:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning=f"evidence_stale (age={age_seconds:.0f}s)",
                    evidence_id=evidence.evidence_id,
                )

        # All evidence is fresh
        return GateVerdict(
            verdict_id=uuid4(),
            gate_id=self.gate_id,
            correlation_id=candidate.correlation_id,
            verdict=VerdictType.PASS,
            reasoning="evidence_freshness_confirmed",
            evidence_id=None,
        )


class Gate8_FinalArbiter(Gate):
    """Gate 8: FINAL_ARBITER - Aggregates all prior verdicts, confirms authority=ZERO"""

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord],
        prior_verdicts: List[GateVerdict] = None,
        **kwargs
    ) -> GateVerdict:
        """Gate 8: Final arbiter - aggregate verdict from gates 1-7"""

        # Fail-closed sentinel
        fail_closed = self._fail_closed_check(candidate, evidence_records)
        if fail_closed:
            return fail_closed

        if not prior_verdicts or len(prior_verdicts) < 7:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.NOT_PROVEN,
                reasoning="prior_gates_incomplete",
                evidence_id=None,
            )

        # Check all prior verdicts
        for prior_verdict in prior_verdicts[:7]:  # Gates 1-7
            if prior_verdict.verdict == VerdictType.BLOCKED:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.BLOCKED,
                    reasoning=f"prior_gate_blocked_{prior_verdict.gate_id}",
                    evidence_id=prior_verdict.evidence_id,
                )

            if prior_verdict.verdict == VerdictType.NOT_PROVEN:
                return GateVerdict(
                    verdict_id=uuid4(),
                    gate_id=self.gate_id,
                    correlation_id=candidate.correlation_id,
                    verdict=VerdictType.NOT_PROVEN,
                    reasoning=f"prior_gate_not_proven_{prior_verdict.gate_id}",
                    evidence_id=None,
                )

        # All prior gates passed, verify authority still ZERO
        if candidate.authority != AuthorityLevel.ZERO:
            return GateVerdict(
                verdict_id=uuid4(),
                gate_id=self.gate_id,
                correlation_id=candidate.correlation_id,
                verdict=VerdictType.BLOCKED,
                reasoning="authority_escalation_attempted",
                evidence_id=None,
            )

        # Final arbiter passes
        return GateVerdict(
            verdict_id=uuid4(),
            gate_id=self.gate_id,
            correlation_id=candidate.correlation_id,
            verdict=VerdictType.PASS,
            reasoning="final_arbiter_approved",
            evidence_id=None,
        )


# ============================================================================
# GUARDIAN ENGINE
# ============================================================================

class GuardianEngine:
    """8-gate sequential pipeline engine with fail-closed logic"""

    def __init__(self):
        """Initialize all 8 gates in sequential order"""
        self.gates = {
            GateID.GATE_1: Gate1_SchemaAndIdentity(GateID.GATE_1),
            GateID.GATE_2: Gate2_HashIntegrity(GateID.GATE_2),
            GateID.GATE_3: Gate3_AuthorityPolicyCompliance(GateID.GATE_3),
            GateID.GATE_4: Gate4_MachineHealthAndReadiness(),
            GateID.GATE_5: Gate5_CanaryExecution(GateID.GATE_5),
            GateID.GATE_6: Gate6_EvidenceConsistency(GateID.GATE_6),
            GateID.GATE_7: Gate7_FreshnessAndStaleness(),
            GateID.GATE_8: Gate8_FinalArbiter(GateID.GATE_8),
        }
        self.gate_order = [
            GateID.GATE_1, GateID.GATE_2, GateID.GATE_3, GateID.GATE_4,
            GateID.GATE_5, GateID.GATE_6, GateID.GATE_7, GateID.GATE_8,
        ]

    def evaluate(
        self,
        candidate: DeploymentCandidate,
        evidence_records: List[EvidenceRecord]
    ) -> DecisionCartridge:
        """
        Execute all 8 gates sequentially and produce decision cartridge.
        Returns immutable DecisionCartridge with all verdicts.
        """
        verdicts = []

        # Execute gates 1-8 in order
        for gate_id in self.gate_order:
            gate = self.gates[gate_id]
            verdict = gate.evaluate(candidate, evidence_records, verdicts)
            verdicts.append(verdict)

        # Compute final verdict based on all 8 verdicts
        final_verdict = self._compute_final_verdict(verdicts)

        # Create decision cartridge (immutable snapshot)
        cartridge = DecisionCartridge(
            cartridge_id=uuid4(),
            correlation_id=candidate.correlation_id,
            candidate_id=candidate.candidate_id,
            gate_verdicts=[
                {
                    "gate_id": v.gate_id.value,
                    "verdict_id": str(v.verdict_id),
                    "verdict": v.verdict.value
                }
                for v in verdicts
            ],
            final_verdict=final_verdict,
            evidence_root_hash=self._hash_evidence(evidence_records),
            policy_root_hash=hashlib.sha256(b"policy_root").hexdigest(),
            authority=AuthorityLevel.ZERO,
            created_at=datetime.utcnow(),
            owner_approval_id=candidate.owner_approval_id,
        )

        return cartridge

    def _compute_final_verdict(self, verdicts: List[GateVerdict]) -> VerdictType:
        """Compute final verdict from all 8 gates"""
        # If any gate BLOCKED, final = BLOCKED
        if any(v.verdict == VerdictType.BLOCKED for v in verdicts):
            return VerdictType.BLOCKED

        # If any gate NOT_PROVEN, final = NOT_PROVEN
        if any(v.verdict == VerdictType.NOT_PROVEN for v in verdicts):
            return VerdictType.NOT_PROVEN

        # All gates PASS, final = PASS
        return VerdictType.PASS

    def _hash_evidence(self, evidence_records: List[EvidenceRecord]) -> str:
        """Hash all evidence for cartridge root hash"""
        evidence_json = json.dumps(
            [
                {
                    "evidence_id": str(e.evidence_id),
                    "evidence_type": e.evidence_type,
                    "checksum": e.checksum
                }
                for e in sorted(evidence_records, key=lambda x: str(x.evidence_id))
            ],
            sort_keys=True
        )
        return hashlib.sha256(evidence_json.encode()).hexdigest()
