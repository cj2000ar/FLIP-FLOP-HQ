"""
Tests for device-bound authentication (Phase C)
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / '04_ENGINE'))

from device_fingerprint import DeviceFingerprinter, HardwareIDGenerator, DeviceInfo
from device_auth import DeviceAuthManager, DeviceAuthFlow
from migrations.migration_framework import MigrationFramework


@pytest.fixture
def temp_db():
    """Create temporary DuckDB for tests"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.duckdb"

    # Initialize DB with migrations
    mf = MigrationFramework(str(db_path), str(Path(__file__).parent.parent / '04_ENGINE' / 'migrations'))
    mf.init_migrations_table()
    mf.apply_all_pending()

    # device_registrations.owner_id has an FK to owner_credentials
    import duckdb
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT INTO owner_credentials (owner_id, password_hash, mfa_secret)
        VALUES ('owner1', 'hash123$abc', 'secret123')
    """)
    conn.close()

    yield str(db_path)

    # Cleanup
    shutil.rmtree(temp_dir)


class TestDeviceFingerprinting:
    """Tests for device fingerprinting"""

    def test_fingerprint_generation(self):
        """Fingerprint should be deterministic"""
        fingerprinter = DeviceFingerprinter()
        device_info = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="abc123def456"
        )

        fp1 = fingerprinter.generate_fingerprint(device_info)
        fp2 = fingerprinter.generate_fingerprint(device_info)

        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex

    def test_fingerprint_varies_by_device(self):
        """Different devices should have different fingerprints"""
        fingerprinter = DeviceFingerprinter()

        device1 = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw1"
        )

        device2 = DeviceInfo(
            os_name="macOS 14",
            os_version="14.2",
            browser_name="Safari",
            browser_version="17.2",
            hardware_id="hw2"
        )

        fp1 = fingerprinter.generate_fingerprint(device1)
        fp2 = fingerprinter.generate_fingerprint(device2)

        assert fp1 != fp2

    def test_user_agent_parsing(self):
        """User agent parsing should extract OS and browser"""
        fingerprinter = DeviceFingerprinter()

        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        parsed = fingerprinter.parse_user_agent(ua)

        assert parsed['os_name'] == "Windows"
        assert parsed['browser_name'] == "Chrome"

    def test_hardware_id_generation(self):
        """Hardware ID should be non-empty and deterministic"""
        hw_gen = HardwareIDGenerator()

        hw1 = hw_gen.generate_from_system()
        hw2 = hw_gen.generate_from_system()

        assert hw1
        assert len(hw1) == 64  # SHA256 hex
        assert hw1 == hw2  # Same machine should have same ID


class TestDeviceRegistration:
    """Tests for device registration"""

    def test_register_device(self, temp_db):
        """Should register new device"""
        manager = DeviceAuthManager(temp_db)

        device_info = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw123"
        )

        success, result = manager.register_device("owner1", device_info)

        assert success is True
        assert result  # device_id returned

    def test_register_duplicate_device(self, temp_db):
        """Should reject duplicate device fingerprint for same owner"""
        manager = DeviceAuthManager(temp_db)

        device_info = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw123"
        )

        success1, device_id1 = manager.register_device("owner1", device_info)
        success2, error = manager.register_device("owner1", device_info)

        assert success1 is True
        assert success2 is False
        assert "already registered" in error.lower()

    def test_primary_device_demotion(self, temp_db):
        """Setting new device as primary should demote old primary"""
        manager = DeviceAuthManager(temp_db)

        device1 = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw1"
        )

        device2 = DeviceInfo(
            os_name="macOS 14",
            os_version="14.2",
            browser_name="Safari",
            browser_version="17.2",
            hardware_id="hw2"
        )

        success1, device_id1 = manager.register_device("owner1", device1, is_primary=True)
        success2, device_id2 = manager.register_device("owner1", device2, is_primary=True)

        primary = manager.get_primary_device("owner1")
        assert primary == device_id2  # device2 should be primary now

    def test_list_owner_devices(self, temp_db):
        """Should list all devices for owner"""
        manager = DeviceAuthManager(temp_db)

        for i in range(3):
            device_info = DeviceInfo(
                os_name=f"OS{i}",
                os_version="1.0",
                browser_name=f"Browser{i}",
                browser_version="1.0",
                hardware_id=f"hw{i}"
            )
            manager.register_device("owner1", device_info)

        devices = manager.list_owner_devices("owner1")
        assert len(devices) == 3

    def test_get_device_info(self, temp_db):
        """Should retrieve device info"""
        manager = DeviceAuthManager(temp_db)

        device_info = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw123"
        )

        success, device_id = manager.register_device("owner1", device_info)
        device = manager.get_device(device_id)

        assert device is not None
        assert device['os_name'] == "Windows 11"
        assert device['browser_name'] == "Chrome"


class TestDeviceChallenge:
    """Tests for new device challenge"""

    def test_known_device_no_challenge(self, temp_db):
        """Known device should not need challenge"""
        manager = DeviceAuthManager(temp_db)
        fingerprinter = DeviceFingerprinter()

        device_info = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw123"
        )

        # Register device
        success, device_id = manager.register_device("owner1", device_info)
        assert success

        # Challenge same fingerprint
        fp = fingerprinter.generate_fingerprint(device_info)
        is_known, result = manager.challenge_new_device("owner1", fp)

        assert is_known is True
        assert result == device_id

    def test_new_device_challenge(self, temp_db):
        """Unknown device should generate challenge"""
        manager = DeviceAuthManager(temp_db)
        fingerprinter = DeviceFingerprinter()

        device1 = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw1"
        )

        device2 = DeviceInfo(
            os_name="macOS 14",
            os_version="14.2",
            browser_name="Safari",
            browser_version="17.2",
            hardware_id="hw2"
        )

        # Register device1
        success, device_id = manager.register_device("owner1", device1)
        assert success

        # Challenge device2
        fp2 = fingerprinter.generate_fingerprint(device2)
        is_known, challenge_id = manager.challenge_new_device("owner1", fp2)

        assert is_known is False
        assert challenge_id  # Challenge ID returned


class TestDeviceAuthFlow:
    """Tests for high-level auth flow"""

    def test_login_known_device(self, temp_db):
        """Should login on known device without challenge"""
        flow = DeviceAuthFlow(temp_db)
        fingerprinter = DeviceFingerprinter()

        device_info = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw123"
        )

        # Register device first
        manager = flow.manager
        success, device_id = manager.register_device("owner1", device_info)
        assert success

        # Login on same device
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        hw = device_info.hardware_id
        success, result = flow.login_with_device("owner1", ua, hw, "192.168.1.1")

        assert success is True
        assert result == device_id

    def test_device_deactivation(self, temp_db):
        """Should deactivate device"""
        manager = DeviceAuthManager(temp_db)

        device_info = DeviceInfo(
            os_name="Windows 11",
            os_version="22631",
            browser_name="Chrome",
            browser_version="120.0.0.0",
            hardware_id="hw123"
        )

        success, device_id = manager.register_device("owner1", device_info)
        assert success

        # Deactivate
        deactivated = manager.deactivate_device(device_id)
        assert deactivated

        device = manager.get_device(device_id)
        assert device['is_active'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
