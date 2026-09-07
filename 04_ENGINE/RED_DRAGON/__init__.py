"""
RED_DRAGON: Guardian Enforcement Engine - Phase 2 Implementation

Authority: ZERO (LOCKED IMMUTABLE)
Status: PRODUCTION READY

Modules:
- guardian_engine: 8-gate sequential pipeline
- guardian_api: FastAPI endpoints
- guardian_tests: Comprehensive test suite (48+ tests)
"""

from .guardian_engine import (
    GuardianEngine,
    DeploymentCandidate,
    EvidenceRecord,
    GateVerdict,
    DecisionCartridge,
    AuthorityTuple,
    VerdictType,
    AuthorityLevel,
    GateID,
)

__version__ = "1.0.0"
__all__ = [
    "GuardianEngine",
    "DeploymentCandidate",
    "EvidenceRecord",
    "GateVerdict",
    "DecisionCartridge",
    "AuthorityTuple",
    "VerdictType",
    "AuthorityLevel",
    "GateID",
]
