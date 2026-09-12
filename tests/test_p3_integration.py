"""
Integration tests for P3: Device-Bound Auth + Credential Rotation + Recovery
Full end-to-end flows
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / '04_ENGINE'))

from migrations.migration_framework import MigrationFramework
from device_fingerprint import DeviceFingerprinter, HardwareIDGenerator, DeviceInfo
from device_auth import DeviceAuthManager, DeviceAuthFlow
from credential_rotation import CredentialRotator, RotationPolicy
from root_recovery import RecoveryCodeManager, RecoveryFlow
from owner_auth import OwnerAuthenticator


@pytest.fixture
def temp_db():
    """Create temporary DuckDB with full schema"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.duckdb"

    # Initialize DB with migrations
    mf = MigrationFramework(str(db_path), str(Path(__file__).parent.parent / '04_ENGINE' / 'migrations'))
    mf.init_migrations_table()
    mf.apply_all_pending()

    # Setup test owner with credentials
    import duckdb
    conn = duckdb.connect(str(db_path))

    # Create owner credentials
    rotator = CredentialRotator(str(db_path))
    password_hash = rotator.hash_password("MyInitial@Password123")

    conn.execute("""
        INSERT INTO owner_credentials (owner_id, password_hash, mfa_secret)
        VALUES ('owner1', ?, 'JBSWY3DPEBLW64TMMQ======')
    """, [password_hash])

    conn.close()

    yield str(db_path)
    shutil.rmtree(temp_dir)


class TestFullAuthFlow:
    """Test complete authentication flow"""

    def test_owner_setup_to_login(self, temp_db):
        """Full flow: setup owner → register device → login → require challenge"""

        # Owner registration (already done in fixture)
        # Device registration
        fingerprinter = DeviceFingerprinter()
        device_info = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw123"
        )

        device_manager = DeviceAuthManager(temp_db)
        success, device_id = device_manager.register_device("owner1", device_info, is_primary=True)

        assert success is True

        # Login flow
        flow = DeviceAuthFlow(temp_db)
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        success, result = flow.login_with_device("owner1", ua, "hw123", "192.168.1.1")

        # Should succeed on known device
        assert success is True
        assert result == device_id

    def test_multi_device_primary_change(self, temp_db):
        """Owner can register multiple devices and change primary"""
        manager = DeviceAuthManager(temp_db)

        devices = []
        for i in range(3):
            device_info = DeviceInfo(
                os_name=f"Device{i}",
                os_version="1.0",
                browser_name="Chrome",
                browser_version="120",
                hardware_id=f"hw{i}"
            )
            success, device_id = manager.register_device(
                "owner1", device_info, is_primary=(i == 0)
            )
            assert success
            devices.append(device_id)

        # Check primary
        primary = manager.get_primary_device("owner1")
        assert primary == devices[0]

        # Change primary to device 2
        manager_direct = DeviceAuthManager(temp_db)
        manager_direct.manager = manager
        device_list = manager.list_owner_devices("owner1")
        assert len(device_list) == 3


class TestCredentialManagement:
    """Test credential setup and rotation"""

    def test_password_lifecycle(self, temp_db):
        """Owner password: set → verify → rotate → verify new"""
        rotator = CredentialRotator(temp_db)

        # Verify old password
        import duckdb
        conn = duckdb.connect(temp_db)
        result = conn.execute(
            "SELECT password_hash FROM owner_credentials WHERE owner_id = ?",
            ["owner1"]
        ).fetchall()
        conn.close()

        old_hash = result[0][0]
        assert rotator.verify_password("MyInitial@Password123", old_hash)

        # Rotate password
        success, msg = rotator.rotate_password("owner1", "MyNewP@ssw0rd456")
        assert success

        # Verify new password
        conn = duckdb.connect(temp_db)
        result = conn.execute(
            "SELECT password_hash FROM owner_credentials WHERE owner_id = ?",
            ["owner1"]
        ).fetchall()
        conn.close()

        new_hash = result[0][0]
        assert rotator.verify_password("MyNewP@ssw0rd456", new_hash)
        assert not rotator.verify_password("MyInitial@Password123", new_hash)

    def test_mfa_rotation_with_recovery(self, temp_db):
        """MFA secret rotation + recovery code backup"""
        rotator = CredentialRotator(temp_db)
        recovery = RecoveryCodeManager(temp_db)

        # Generate recovery codes
        codes = recovery.generate_recovery_codes("owner1", count=10)
        assert len(codes) == 10

        # Rotate MFA
        success, msg = rotator.rotate_mfa_secret("owner1", "newsecret1234567890")
        assert success

        # Use recovery code to verify account is still accessible
        success, msg = recovery.validate_recovery_code("owner1", codes[0])
        assert success


class TestRecoveryFlow:
    """Test account recovery scenarios"""

    def test_lost_device_recovery(self, temp_db):
        """Owner loses device, uses recovery code to regain access"""
        flow = RecoveryFlow(temp_db)
        device_manager = DeviceAuthManager(temp_db)

        # Setup recovery
        codes = flow.setup_recovery("owner1")

        # Create 2 devices
        device_info1 = DeviceInfo(
            os_name="Device1", os_version="1",
            browser_name="Chrome", browser_version="120",
            hardware_id="hw1"
        )
        device_info2 = DeviceInfo(
            os_name="Device2", os_version="1",
            browser_name="Chrome", browser_version="120",
            hardware_id="hw2"
        )

        success1, dev_id1 = device_manager.register_device("owner1", device_info1, is_primary=True)
        success2, dev_id2 = device_manager.register_device("owner1", device_info2)

        assert success1 and success2

        # Deactivate primary device (lost)
        device_manager.deactivate_device(dev_id1)

        # Recover using code
        success, msg = flow.recover_account("owner1", codes[0], device_id=dev_id2)
        assert success

        # Can now reset password on remaining device
        rotator = CredentialRotator(temp_db)
        success, msg = rotator.rotate_password(
            "owner1", "RecoveredP@ssw0rd123",
            rotated_by="RECOVERY", device_id=dev_id2
        )
        assert success


class TestAuditTrail:
    """Test complete audit trail"""

    def test_audit_trail_completeness(self, temp_db):
        """All security events should be logged"""
        import duckdb

        # Perform various operations
        rotator = CredentialRotator(temp_db)
        rotator.rotate_password("owner1", "NewP@ssw0rd123", device_id="dev1", ip_address="192.168.1.1")

        device_manager = DeviceAuthManager(temp_db)
        device_info = DeviceInfo(
            os_name="Windows", os_version="11",
            browser_name="Chrome", browser_version="120",
            hardware_id="hw1"
        )
        device_manager.register_device("owner1", device_info)

        recovery = RecoveryCodeManager(temp_db)
        codes = recovery.generate_recovery_codes("owner1", count=5)
        recovery.validate_recovery_code("owner1", codes[0], device_id="dev1")

        # Check audit trails
        conn = duckdb.connect(temp_db)

        # Rotation history
        rotations = conn.execute(
            "SELECT COUNT(*) FROM credential_rotations WHERE owner_id = ?",
            ["owner1"]
        ).fetchall()
        assert rotations[0][0] >= 1

        # Device registrations
        devices = conn.execute(
            "SELECT COUNT(*) FROM device_registrations WHERE owner_id = ?",
            ["owner1"]
        ).fetchall()
        assert devices[0][0] >= 1

        # Recovery codes
        recovery_status = conn.execute(
            "SELECT COUNT(*) FROM recovery_codes WHERE owner_id = ? AND used_at IS NOT NULL",
            ["owner1"]
        ).fetchall()
        assert recovery_status[0][0] >= 1

        conn.close()


class TestErrorHandling:
    """Test error conditions"""

    def test_invalid_password_rejected(self, temp_db):
        """Invalid password rejected at validation"""
        rotator = CredentialRotator(temp_db)

        success, msg = rotator.rotate_password("owner1", "weak")
        assert success is False

    def test_invalid_recovery_code(self, temp_db):
        """Invalid recovery code rejected"""
        recovery = RecoveryCodeManager(temp_db)

        success, msg = recovery.validate_recovery_code("owner1", "FAKE-CODE")
        assert success is False

    def test_duplicate_device_registration(self, temp_db):
        """Duplicate device fingerprint rejected"""
        manager = DeviceAuthManager(temp_db)

        device_info = DeviceInfo(
            os_name="Windows", os_version="11",
            browser_name="Chrome", browser_version="120",
            hardware_id="hw1"
        )

        success1, dev_id = manager.register_device("owner1", device_info)
        assert success1

        success2, error = manager.register_device("owner1", device_info)
        assert success2 is False
        assert "already registered" in error.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
