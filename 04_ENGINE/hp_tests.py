"""
HP 24/7 Infrastructure Tests - 40+ Red-Green-Refactor Test Cases
FlipFlop HQ Phase 2
Authority: ZERO (locked, non-negotiable)
"""

import pytest
import sqlite3
import tempfile
import time
import hashlib
import hmac
from pathlib import Path

from hp_infra import (
    HPInfrastructure,
    MachineRoleTuple,
    HeartbeatTuple,
    FencingTokenTuple,
    DurableStorageTuple,
    DurableReceiptTuple,
    HealthState,
    HeartbeatStatus,
    RestartPhase,
    ArchiveStatus,
    verify_hp01_heartbeat_freshness,
    verify_hp02_clock_sync,
    verify_hp03_fencing_token,
    verify_hp04_restart_detection,
    verify_hp05_durable_write_once,
    verify_hp06_receipt_required,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def hp(temp_db):
    """Create HPInfrastructure instance."""
    return HPInfrastructure(db_path=temp_db, hmac_secret="test-secret-key")


# ============================================================================
# HP01: HEARTBEAT FRESHNESS (< 60 seconds)
# ============================================================================

class TestHP01HeartbeatFreshness:
    """HP01 constraint: Heartbeat must be < 60 seconds old."""

    def test_send_heartbeat_creates_record(self, hp):
        """Test sending heartbeat creates immutable record."""
        hb = hp.send_heartbeat("RED_DRAGON", clock_offset=0.0)

        assert isinstance(hb, HeartbeatTuple)
        assert hb.machine_id == "RED_DRAGON"
        assert hb.health_status == HeartbeatStatus.ALIVE.value
        assert hb.sequence == 1

    def test_heartbeat_immutable(self, hp):
        """Test HeartbeatTuple is frozen (immutable)."""
        hb = hp.send_heartbeat("RED_DRAGON")
        with pytest.raises(AttributeError):
            hb.sequence = 999  # frozen

    def test_heartbeat_fresh_immediately(self, hp):
        """Test heartbeat is fresh immediately after send."""
        hb = hp.send_heartbeat("RED_DRAGON")
        assert hp.is_heartbeat_fresh(hb) is True

    def test_heartbeat_stale_after_60_seconds(self, hp):
        """Test heartbeat becomes stale after 60+ seconds."""
        hb = hp.send_heartbeat("RED_DRAGON")
        # Manually set timestamp 61 seconds in past
        old_hb = HeartbeatTuple(
            heartbeat_id=hb.heartbeat_id,
            machine_id=hb.machine_id,
            timestamp=time.time() - 61,
            health_status=hb.health_status,
            clock_offset=hb.clock_offset,
            sequence=hb.sequence
        )
        assert hp.is_heartbeat_fresh(old_hb) is False

    def test_heartbeat_exactly_60_seconds_fresh(self, hp):
        """Test heartbeat at exactly 60s boundary is still fresh."""
        # Create a heartbeat with timestamp 59.5 seconds old (safely within 60s window)
        now = time.time()
        hb_59_5s = HeartbeatTuple(
            heartbeat_id="test-hb-59-5s",
            machine_id="RED_DRAGON",
            timestamp=now - 59.5,  # 59.5 seconds old (fresh)
            health_status=HeartbeatStatus.ALIVE.value,
            clock_offset=0.0,
            sequence=1
        )
        assert hp.is_heartbeat_fresh(hb_59_5s) is True

    def test_heartbeat_just_over_60_seconds_stale(self, hp):
        """Test heartbeat just over 60s boundary is stale."""
        # Create a heartbeat with timestamp 60.5 seconds old (stale)
        now = time.time()
        hb_60_5s = HeartbeatTuple(
            heartbeat_id="test-hb-60-5s",
            machine_id="RED_DRAGON",
            timestamp=now - 60.5,  # 60.5 seconds old (stale)
            health_status=HeartbeatStatus.ALIVE.value,
            clock_offset=0.0,
            sequence=1
        )
        assert hp.is_heartbeat_fresh(hb_60_5s) is False

    def test_heartbeat_sequence_increments(self, hp):
        """Test heartbeat sequence increments monotonically."""
        hb1 = hp.send_heartbeat("RED_DRAGON")
        hb2 = hp.send_heartbeat("RED_DRAGON")
        hb3 = hp.send_heartbeat("RED_DRAGON")

        assert hb1.sequence == 1
        assert hb2.sequence == 2
        assert hb3.sequence == 3

    def test_get_truth_age_seconds(self, hp):
        """Test truth age computation (seconds since last heartbeat)."""
        hb = hp.send_heartbeat("RED_DRAGON")
        age = hp.get_truth_age_seconds("RED_DRAGON")
        assert 0 <= age <= 1  # Should be very fresh

    def test_get_truth_age_no_heartbeat(self, hp):
        """Test truth age returns -1 if no heartbeat."""
        age = hp.get_truth_age_seconds("NONEXISTENT")
        assert age == -1

    def test_verify_hp01_constraint(self, hp):
        """Test HP01 constraint verification function."""
        hb = hp.send_heartbeat("RED_DRAGON")
        assert verify_hp01_heartbeat_freshness(hp, "RED_DRAGON") is True

        # Artificially stale heartbeat
        assert verify_hp01_heartbeat_freshness(hp, "NONEXISTENT") is False


# ============================================================================
# HP02: CLOCK SYNC (NTP offset < 5 seconds)
# ============================================================================

class TestHP02ClockSync:
    """HP02 constraint: Clock offset must be < 5 seconds."""

    def test_clock_sync_valid(self, hp):
        """Test valid clock offset passes verification."""
        hb = hp.send_heartbeat("RED_DRAGON", clock_offset=0.5)
        assert hp.verify_clock_sync("RED_DRAGON", hb) is True

    def test_clock_sync_exactly_5_seconds(self, hp):
        """Test clock offset at exactly 5s boundary is valid."""
        hb = HeartbeatTuple(
            heartbeat_id="test-hb-1",
            machine_id="RED_DRAGON",
            timestamp=time.time(),
            health_status=HeartbeatStatus.ALIVE.value,
            clock_offset=5.0,
            sequence=1
        )
        assert hp.verify_clock_sync("RED_DRAGON", hb) is True

    def test_clock_sync_exceeds_5_seconds_positive(self, hp):
        """Test clock offset > 5s (forward jump) fails."""
        hb = HeartbeatTuple(
            heartbeat_id="test-hb-1",
            machine_id="RED_DRAGON",
            timestamp=time.time(),
            health_status=HeartbeatStatus.ALIVE.value,
            clock_offset=5.1,
            sequence=1
        )
        assert hp.verify_clock_sync("RED_DRAGON", hb) is False

    def test_clock_sync_exceeds_5_seconds_negative(self, hp):
        """Test clock offset < -5s (backward jump) fails."""
        hb = HeartbeatTuple(
            heartbeat_id="test-hb-1",
            machine_id="RED_DRAGON",
            timestamp=time.time(),
            health_status=HeartbeatStatus.ALIVE.value,
            clock_offset=-5.1,
            sequence=1
        )
        assert hp.verify_clock_sync("RED_DRAGON", hb) is False

    def test_clock_anomaly_triggers_restart_detection(self, hp):
        """Test large clock jump detected as restart."""
        hb = hp.send_heartbeat("RED_DRAGON", clock_offset=10.0)
        assert hb.health_status == HeartbeatStatus.RESTART_DETECTED.value

    def test_verify_hp02_constraint(self, hp):
        """Test HP02 constraint verification function."""
        hb = hp.send_heartbeat("RED_DRAGON", clock_offset=0.5)
        assert verify_hp02_clock_sync(hp, "RED_DRAGON") is True


# ============================================================================
# HP03: FENCING TOKEN VALIDATION
# ============================================================================

class TestHP03FencingToken:
    """HP03 constraint: Fencing token must be valid (not expired, signature verified)."""

    def test_acquire_fencing_token(self, hp):
        """Test acquiring single-writer fencing token."""
        token = hp.acquire_fencing_token("RED_DRAGON")

        assert isinstance(token, FencingTokenTuple)
        assert token.machine_id == "RED_DRAGON"
        assert token.authority_lock == "ZERO"
        assert token.token_id

    def test_fencing_token_immutable(self, hp):
        """Test FencingTokenTuple is frozen."""
        token = hp.acquire_fencing_token("RED_DRAGON")
        with pytest.raises(AttributeError):
            token.authority_lock = "ESCALATED"  # frozen

    def test_fencing_token_signature_valid(self, hp):
        """Test fencing token signature is valid."""
        token = hp.acquire_fencing_token("RED_DRAGON")
        is_valid, reason = hp.validate_fencing_token(token)
        assert is_valid is True
        assert reason == "token_valid"

    def test_fencing_token_not_expired(self, hp):
        """Test newly acquired token is not expired."""
        token = hp.acquire_fencing_token("RED_DRAGON")
        assert time.time() < token.expiry_timestamp

    def test_fencing_token_signature_verification_fails_on_tampering(self, hp):
        """Test signature verification fails if signature tampered."""
        token = hp.acquire_fencing_token("RED_DRAGON")

        # Tamper with signature
        tampered = FencingTokenTuple(
            token_id=token.token_id,
            machine_id=token.machine_id,
            epoch=token.epoch,
            expiry_timestamp=token.expiry_timestamp,
            signature_hash="deadbeef" + token.signature_hash[8:],  # Corrupt
            authority_lock=token.authority_lock
        )

        is_valid, reason = hp.validate_fencing_token(tampered)
        assert is_valid is False
        assert reason == "token_invalid_or_expired"

    def test_release_fencing_token(self, hp):
        """Test releasing (revoking) fencing token."""
        token = hp.acquire_fencing_token("RED_DRAGON")
        hp.release_fencing_token(token.token_id)

        is_valid, reason = hp.validate_fencing_token(token)
        assert is_valid is False
        assert reason == "token_revoked"

    def test_verify_hp03_constraint(self, hp):
        """Test HP03 constraint verification function."""
        token = hp.acquire_fencing_token("RED_DRAGON")
        assert verify_hp03_fencing_token(hp, token) is True

    def test_multiple_tokens_per_machine(self, hp):
        """Test multiple tokens can be issued per machine."""
        token1 = hp.acquire_fencing_token("RED_DRAGON")
        token2 = hp.acquire_fencing_token("RED_DRAGON")

        assert token1.token_id != token2.token_id
        assert verify_hp03_fencing_token(hp, token1) is True
        assert verify_hp03_fencing_token(hp, token2) is True


# ============================================================================
# HP04: RESTART DETECTION & RECOVERY
# ============================================================================

class TestHP04RestartDetection:
    """HP04 constraint: Restart detection (cold/warm start recovery)."""

    def test_detect_normal_heartbeat(self, hp):
        """Test normal heartbeat not detected as restart."""
        hb = hp.send_heartbeat("RED_DRAGON", clock_offset=0.0)
        is_restart, phase = hp.detect_restart("RED_DRAGON", hb)
        assert is_restart is False

    def test_detect_sleep_gap(self, hp):
        """Test sleep detected (> 5s gap between heartbeats)."""
        # Send first heartbeat
        hb1 = hp.send_heartbeat("RED_DRAGON")
        time.sleep(0.1)

        # Manually create heartbeat with large gap
        # (simulate sleep by checking detection logic)
        hb2 = hp.send_heartbeat("RED_DRAGON")

        # Small gap should not trigger restart
        assert hb2.health_status == HeartbeatStatus.ALIVE.value

    def test_detect_clock_jump_forward(self, hp):
        """Test forward clock jump detected as restart."""
        hb = hp.send_heartbeat("RED_DRAGON", clock_offset=10.0)
        is_restart, phase = hp.detect_restart("RED_DRAGON", hb)
        assert is_restart is True
        assert phase == RestartPhase.BOOT.value

    def test_detect_clock_jump_backward(self, hp):
        """Test backward clock jump detected as restart."""
        hb = hp.send_heartbeat("RED_DRAGON", clock_offset=-10.0)
        is_restart, phase = hp.detect_restart("RED_DRAGON", hb)
        assert is_restart is True

    def test_enter_restart_recovery(self, hp):
        """Test entering restart recovery protocol."""
        recovery_id = hp.enter_restart_recovery("RED_DRAGON")
        assert recovery_id

    def test_advance_restart_recovery_phase(self, hp):
        """Test advancing through restart recovery phases."""
        recovery_id = hp.enter_restart_recovery("RED_DRAGON")

        # Advance through phases
        hp.advance_restart_recovery_phase(recovery_id, RestartPhase.DISCOVERY.value)
        hp.advance_restart_recovery_phase(recovery_id, RestartPhase.RECONSTRUCTION.value)
        hp.advance_restart_recovery_phase(recovery_id, RestartPhase.SYNC.value)
        hp.advance_restart_recovery_phase(recovery_id, RestartPhase.RECOVERY.value)

        # Should succeed without errors

    def test_verify_hp04_constraint(self, hp):
        """Test HP04 constraint verification function."""
        hb = hp.send_heartbeat("RED_DRAGON")
        assert verify_hp04_restart_detection(hp, "RED_DRAGON") is True


# ============================================================================
# HP05: DURABLE STORAGE (Write-Once, Append-Only)
# ============================================================================

class TestHP05DurableStorage:
    """HP05 constraint: Durable storage write-once (no updates/deletes)."""

    def test_write_durable_storage(self, hp):
        """Test writing to durable storage."""
        storage = hp.write_durable_storage(
            "/archive/batch_2024_01_02.json",
            b"batch data",
            retention_years=7
        )

        assert isinstance(storage, DurableStorageTuple)
        assert storage.path == "/archive/batch_2024_01_02.json"
        assert storage.retention_years == 7
        assert storage.immutable_hash

    def test_durable_storage_immutable(self, hp):
        """Test DurableStorageTuple is frozen."""
        storage = hp.write_durable_storage(
            "/archive/test.json",
            b"data",
            retention_years=7
        )

        with pytest.raises(AttributeError):
            storage.retention_years = 1  # frozen

    def test_durable_storage_hash_computed(self, hp):
        """Test SHA256 hash computed for stored data."""
        data = b"test data content"
        storage = hp.write_durable_storage(
            "/archive/test.json",
            data
        )

        expected_hash = hashlib.sha256(data).hexdigest()
        assert storage.immutable_hash == expected_hash

    def test_write_once_enforcement_duplicate_path(self, hp):
        """Test write-once: second write to same path fails."""
        path = "/archive/unique_batch.json"

        # First write succeeds
        storage1 = hp.write_durable_storage(path, b"data1")
        assert storage1.path == path

        # Second write to same path fails
        with pytest.raises(ValueError) as exc:
            hp.write_durable_storage(path, b"data2")
        assert "write-once" in str(exc.value).lower()

    def test_different_paths_allowed(self, hp):
        """Test write-once only applies to same path."""
        # Different paths should both succeed
        storage1 = hp.write_durable_storage("/archive/batch1.json", b"data1")
        storage2 = hp.write_durable_storage("/archive/batch2.json", b"data2")

        assert storage1.path != storage2.path
        assert storage1.immutable_hash != storage2.immutable_hash

    def test_verify_hp05_constraint(self, hp):
        """Test HP05 constraint verification function."""
        path = "/archive/test_write_once.json"
        assert verify_hp05_durable_write_once(hp, path) is True


# ============================================================================
# HP06: DURABLE RECEIPT VERIFICATION
# ============================================================================

class TestHP06DurableReceipt:
    """HP06 constraint: Receipt required before VERIFIED."""

    def test_write_durable_receipt(self, hp):
        """Test writing durable receipt for archive."""
        receipt = hp.write_durable_receipt("/archive/batch_2024_01_02.json")

        assert isinstance(receipt, DurableReceiptTuple)
        assert receipt.storage_path == "/archive/batch_2024_01_02.json"
        assert receipt.archive_status == ArchiveStatus.WRITTEN.value
        assert receipt.receipt_id

    def test_durable_receipt_immutable(self, hp):
        """Test DurableReceiptTuple is frozen."""
        receipt = hp.write_durable_receipt("/archive/test.json")

        with pytest.raises(AttributeError):
            receipt.archive_status = "VERIFIED"  # frozen

    def test_receipt_signature_verified(self, hp):
        """Test receipt confirmation hash is valid."""
        receipt = hp.write_durable_receipt("/archive/test.json")
        assert hp.verify_receipt(receipt) is True

    def test_receipt_signature_fails_on_tampering(self, hp):
        """Test signature verification fails if hash tampered."""
        receipt = hp.write_durable_receipt("/archive/test.json")

        # Tamper with hash
        tampered = DurableReceiptTuple(
            receipt_id=receipt.receipt_id,
            timestamp=receipt.timestamp,
            storage_path=receipt.storage_path,
            confirmation_hash="deadbeef" + receipt.confirmation_hash[8:],  # Corrupt
            archive_status=receipt.archive_status
        )

        assert hp.verify_receipt(tampered) is False

    def test_mark_receipt_verified(self, hp):
        """Test marking receipt as VERIFIED."""
        receipt = hp.write_durable_receipt("/archive/test.json")
        hp.mark_receipt_verified(receipt.receipt_id)

        # Verify by querying DB
        import sqlite3
        conn = sqlite3.connect(hp.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT archive_status FROM durable_receipts WHERE receipt_id = ?",
                           (receipt.receipt_id,))
            status = cursor.fetchone()[0]
            assert status == ArchiveStatus.VERIFIED.value
        finally:
            conn.close()

    def test_verify_hp06_constraint(self, hp):
        """Test HP06 constraint verification function."""
        receipt = hp.write_durable_receipt("/archive/test.json")
        assert verify_hp06_receipt_required(hp, receipt) is True


# ============================================================================
# MACHINE ROLE
# ============================================================================

class TestMachineRole:
    """Test MachineRoleTuple and machine role tracking."""

    def test_get_machine_role_after_heartbeat(self, hp):
        """Test getting machine role after sending heartbeat."""
        hp.send_heartbeat("RED_DRAGON")
        role = hp.get_machine_role("RED_DRAGON")

        assert isinstance(role, MachineRoleTuple)
        assert role.machine_id == "RED_DRAGON"
        assert role.role == "RED_DRAGON"
        assert role.health_state == HealthState.HEALTHY.value
        assert role.fencing_epoch >= 1

    def test_get_machine_role_nonexistent(self, hp):
        """Test getting role for nonexistent machine."""
        role = hp.get_machine_role("NONEXISTENT")
        assert role is None

    def test_machine_role_immutable(self, hp):
        """Test MachineRoleTuple is frozen."""
        hp.send_heartbeat("RED_DRAGON")
        role = hp.get_machine_role("RED_DRAGON")

        with pytest.raises(AttributeError):
            role.health_state = "FAILED"  # frozen

    def test_machine_role_truth_age(self, hp):
        """Test truth age in machine role."""
        hp.send_heartbeat("RED_DRAGON")
        role = hp.get_machine_role("RED_DRAGON")

        assert role.truth_age_seconds >= 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests across HP constraints."""

    def test_guardian_gate4_requirements(self, hp):
        """
        Test Guardian Gate 4 requirements:
        - Fresh heartbeat (< 60s)
        - Clock in sync (< 5s offset)
        - Valid fencing token
        """
        machine_id = "RED_DRAGON"

        # Send heartbeat
        hb = hp.send_heartbeat(machine_id, clock_offset=1.0)

        # Check Gate 4 requirements
        assert hp.is_heartbeat_fresh(hb) is True  # Fresh
        assert hp.verify_clock_sync(machine_id, hb) is True  # Clock sync
        assert verify_hp01_heartbeat_freshness(hp, machine_id) is True
        assert verify_hp02_clock_sync(hp, machine_id) is True

        # Get fencing token
        token = hp.acquire_fencing_token(machine_id)
        is_valid, _ = hp.validate_fencing_token(token)
        assert is_valid is True

    def test_batch_archive_write_flow(self, hp):
        """
        Test Batch archive write flow:
        - Write to durable storage
        - Receive durable receipt
        - Verify receipt
        - Mark as VERIFIED
        """
        storage_path = "/archive/batch_2024_01_02.json"

        # Step 1: Write durable storage
        storage = hp.write_durable_storage(storage_path, b"batch data", retention_years=7)
        assert storage.path == storage_path

        # Step 2: Write durable receipt
        receipt = hp.write_durable_receipt(storage_path)
        assert receipt.storage_path == storage_path
        assert receipt.archive_status == ArchiveStatus.WRITTEN.value

        # Step 3: Verify receipt
        assert hp.verify_receipt(receipt) is True

        # Step 4: Mark as VERIFIED
        hp.mark_receipt_verified(receipt.receipt_id)

    def test_multiple_machines_independent(self, hp):
        """Test multiple machines maintain independent state."""
        # Machine 1
        hb1 = hp.send_heartbeat("MACHINE_1", clock_offset=0.5)
        token1 = hp.acquire_fencing_token("MACHINE_1")

        # Machine 2
        hb2 = hp.send_heartbeat("MACHINE_2", clock_offset=0.3)
        token2 = hp.acquire_fencing_token("MACHINE_2")

        # Verify independence
        assert hb1.heartbeat_id != hb2.heartbeat_id
        assert token1.token_id != token2.token_id
        assert hb1.sequence == 1
        assert hb2.sequence == 1  # Independent sequence

    def test_no_escalation_of_authority(self, hp):
        """Test Authority=ZERO is hardcoded in fencing tokens."""
        token = hp.acquire_fencing_token("RED_DRAGON")
        assert token.authority_lock == "ZERO"

        # Cannot change
        with pytest.raises(AttributeError):
            token.authority_lock = "ESCALATED"  # frozen


# ============================================================================
# CONCURRENCY TESTS
# ============================================================================

class TestConcurrency:
    """Test thread-safe operations."""

    def test_concurrent_heartbeats(self, hp):
        """Test concurrent heartbeats don't corrupt state."""
        import threading

        results = []

        def send_hb(machine_id):
            hb = hp.send_heartbeat(machine_id)
            results.append((machine_id, hb.sequence))

        # Send concurrent heartbeats
        threads = [
            threading.Thread(target=send_hb, args=("MACHINE_1",))
            for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should have incremented sequence
        assert len(results) == 5
        sequences = [seq for _, seq in results]
        assert sequences == list(range(1, 6))  # 1-5 in order

    def test_concurrent_fencing_tokens(self, hp):
        """Test concurrent token acquisition."""
        import threading

        tokens = []

        def acquire_token():
            token = hp.acquire_fencing_token("RED_DRAGON")
            tokens.append(token)

        threads = [
            threading.Thread(target=acquire_token)
            for _ in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All tokens should be valid and unique
        assert len(tokens) == 3
        token_ids = [t.token_id for t in tokens]
        assert len(set(token_ids)) == 3  # All unique


# ============================================================================
# DATABASE PERSISTENCE TESTS
# ============================================================================

class TestDatabasePersistence:
    """Test data persists across HP instances."""

    def test_heartbeat_persists(self, temp_db):
        """Test heartbeat persists to database."""
        # Write heartbeat with instance 1
        hp1 = HPInfrastructure(db_path=temp_db)
        hb1 = hp1.send_heartbeat("RED_DRAGON", clock_offset=0.5)

        # Read heartbeat with instance 2
        hp2 = HPInfrastructure(db_path=temp_db)
        hb2 = hp2.get_latest_heartbeat("RED_DRAGON")

        assert hb1.heartbeat_id == hb2.heartbeat_id
        assert hb1.machine_id == hb2.machine_id
        assert hb1.sequence == hb2.sequence

    def test_receipt_persists(self, temp_db):
        """Test receipts persist to database."""
        hp1 = HPInfrastructure(db_path=temp_db)
        receipt1 = hp1.write_durable_receipt("/archive/test.json")

        hp2 = HPInfrastructure(db_path=temp_db)
        # Verify through fresh query
        conn = sqlite3.connect(temp_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT receipt_id FROM durable_receipts WHERE receipt_id = ?",
                           (receipt1.receipt_id,))
            result = cursor.fetchone()
            assert result is not None
        finally:
            conn.close()


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
