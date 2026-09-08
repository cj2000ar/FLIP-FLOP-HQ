"""
V2 Launcher Integration Tests
Tests package verification, exit code 78, and immutable event logging.
"""

import pytest
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add RED_DRAGON to path
sys.path.insert(0, str(Path(__file__).parent / "RED_DRAGON"))

from guardian_package_verifier import (
    GuardianPackageVerifier,
    ArtifactManifest,
    VerificationStatus
)
from guardian_v2_launcher import GuardianV2Launcher


class TestGuardianPackageVerifier:
    """Test package verifier core functionality"""

    def test_init_event_store(self):
        """Test event store initialization"""
        verifier = GuardianPackageVerifier("test_events.db")
        assert os.path.exists("test_events.db")
        os.remove("test_events.db")

    def test_missing_artifact(self):
        """Test verification fails when artifact missing"""
        verifier = GuardianPackageVerifier("test_verify.db")
        manifest = ArtifactManifest(
            strategy_hash="abc123",
            engine_hash="def456",
            ui_hash="ghi789",
            passport_hash="jkl012",
            created_at=datetime.utcnow().isoformat()
        )

        artifact_paths = {
            "strategy": "/nonexistent/strategy.py",
            "engine": "/nonexistent/engine.py",
            "ui": "/nonexistent/ui.js",
            "passport": "/nonexistent/passport.json"
        }

        correlation_id = str(uuid4())
        status, events = verifier.verify_package(manifest, artifact_paths, correlation_id)

        assert status == VerificationStatus.MISSING_ARTIFACT
        assert len(events) > 0
        assert all(e.exit_code == 78 for e in events if e.status != VerificationStatus.PASS)

        os.remove("test_verify.db")

    def test_event_immutability(self):
        """Test verification events are immutable (frozen dataclass)"""
        verifier = GuardianPackageVerifier("test_immutable.db")

        # Create event
        from guardian_package_verifier import VerificationEvent
        event = VerificationEvent(
            event_id=str(uuid4()),
            correlation_id=str(uuid4()),
            artifact_type="strategy",
            expected_hash="abc123",
            actual_hash="def456",
            status=VerificationStatus.HASH_MISMATCH,
            event_time=datetime.utcnow().isoformat(),
            verified_at=datetime.utcnow().isoformat(),
            exit_code=78
        )

        # Verify frozen (no modification)
        with pytest.raises(AttributeError):
            event.exit_code = 0

        os.remove("test_immutable.db")

    def test_event_logging(self):
        """Test events are logged to immutable store"""
        verifier = GuardianPackageVerifier("test_logging.db")
        correlation_id = str(uuid4())

        manifest = ArtifactManifest(
            strategy_hash="abc123",
            engine_hash="def456",
            ui_hash="ghi789",
            passport_hash="jkl012",
            created_at=datetime.utcnow().isoformat()
        )

        artifact_paths = {
            "strategy": "/missing/strategy.py",
        }

        # Verify
        status, events = verifier.verify_package(manifest, artifact_paths, correlation_id)

        # Retrieve events
        retrieved = verifier.get_verification_events(correlation_id)
        assert len(retrieved) > 0
        assert retrieved[0]["correlation_id"] == correlation_id

        os.remove("test_logging.db")


class TestGuardianV2Launcher:
    """Test V2 launcher staged execution"""

    def test_launcher_init(self):
        """Test launcher initializes from manifest"""
        # Create test manifest
        manifest_data = {
            "strategy_hash": "abc123",
            "engine_hash": "def456",
            "ui_hash": "ghi789",
            "passport_hash": "jkl012",
            "created_at": datetime.utcnow().isoformat()
        }

        manifest_path = "test_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f)

        launcher = GuardianV2Launcher(manifest_path)
        assert launcher.manifest.strategy_hash == "abc123"
        assert launcher.correlation_id is not None

        os.remove(manifest_path)

    def test_launcher_exit_code_78(self):
        """Test launcher exits with code 78 on verification failure"""
        assert GuardianV2Launcher.GUARDIAN_EXIT_CODE == 78

    def test_verification_events_retrieval(self):
        """Test launcher can retrieve verification events"""
        manifest_data = {
            "strategy_hash": "abc123",
            "engine_hash": "def456",
            "ui_hash": "ghi789",
            "passport_hash": "jkl012"
        }

        manifest_path = "test_manifest_events.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f)

        launcher = GuardianV2Launcher(manifest_path)
        events = launcher.get_verification_events()

        # Should be empty initially
        assert isinstance(events, list)

        os.remove(manifest_path)


class TestAuthority:
    """Test Authority-ZERO constraint"""

    def test_authority_zero_enforcement(self):
        """Verify Authority-ZERO is immutable"""
        from guardian_engine import AuthorityTuple, AuthorityLevel

        # Create valid ZERO authority
        auth = AuthorityTuple(
            authority=AuthorityLevel.ZERO,
            live_enabled=False,
            broker_orders_allowed=False,
            control_mutation_allowed=False
        )

        assert auth.authority == AuthorityLevel.ZERO
        assert auth.live_enabled is False
        assert auth.broker_orders_allowed is False

        # Verify frozen
        with pytest.raises(AttributeError):
            auth.live_enabled = True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
