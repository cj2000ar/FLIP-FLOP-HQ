"""
Tests for credential rotation and recovery (Phase D)
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / '04_ENGINE'))

from credential_rotation import CredentialRotator, RotationPolicy, RotationScheduler
from root_recovery import RecoveryCodeManager, RecoveryFlow
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

    # Setup test owner
    import duckdb
    conn = duckdb.connect(str(db_path))
    conn.execute("""
        INSERT INTO owner_credentials (owner_id, password_hash, mfa_secret)
        VALUES ('owner1', 'hash123$abc', 'secret123')
    """)
    conn.close()

    yield str(db_path)

    shutil.rmtree(temp_dir)


class TestPasswordValidation:
    """Tests for password validation"""

    def test_password_too_short(self):
        """Should reject password shorter than policy"""
        rotator = CredentialRotator(":memory:", RotationPolicy(min_password_length=12))

        assert rotator._validate_password("short") is False

    def test_password_no_uppercase(self):
        """Should reject password without uppercase"""
        rotator = CredentialRotator(":memory:", RotationPolicy(require_uppercase=True))

        assert rotator._validate_password("password123!") is False

    def test_password_no_digits(self):
        """Should reject password without digits"""
        rotator = CredentialRotator(":memory:", RotationPolicy(require_digits=True))

        assert rotator._validate_password("Password!@#") is False

    def test_password_no_special(self):
        """Should reject password without special chars"""
        rotator = CredentialRotator(":memory:", RotationPolicy(require_special=True))

        assert rotator._validate_password("Password123") is False

    def test_valid_password(self):
        """Should accept valid password"""
        rotator = CredentialRotator(":memory:")

        assert rotator._validate_password("MyP@ssw0rd") is True


class TestPasswordHashing:
    """Tests for password hashing"""

    def test_password_hash_deterministic(self):
        """Same password should produce different hashes (due to salt)"""
        rotator = CredentialRotator(":memory:")

        password = "MyP@ssw0rd123"
        hash1 = rotator.hash_password(password)
        hash2 = rotator.hash_password(password)

        # Hashes should be different (different salts)
        assert hash1 != hash2

    def test_password_verification(self):
        """Should verify correct password"""
        rotator = CredentialRotator(":memory:")

        password = "MyP@ssw0rd123"
        hashed = rotator.hash_password(password)

        assert rotator.verify_password(password, hashed) is True

    def test_password_wrong_verification(self):
        """Should reject wrong password"""
        rotator = CredentialRotator(":memory:")

        password = "MyP@ssw0rd123"
        hashed = rotator.hash_password(password)

        assert rotator.verify_password("WrongPassword", hashed) is False


class TestPasswordRotation:
    """Tests for password rotation"""

    def test_rotate_password_success(self, temp_db):
        """Should rotate password successfully"""
        rotator = CredentialRotator(temp_db)

        success, message = rotator.rotate_password("owner1", "NewP@ssw0rd123")

        assert success is True
        assert "successfully" in message.lower()

    def test_rotate_password_invalid(self, temp_db):
        """Should reject invalid password"""
        rotator = CredentialRotator(temp_db)

        success, message = rotator.rotate_password("owner1", "weak")

        assert success is False
        assert "policy" in message.lower() or "requirements" in message.lower()

    def test_rotation_history(self, temp_db):
        """Should record rotation history"""
        rotator = CredentialRotator(temp_db)

        rotator.rotate_password("owner1", "NewP@ssw0rd123", reason="SCHEDULED")

        history = rotator.get_rotation_history("owner1")

        assert len(history) > 0
        assert history[0]['rotation_type'] == 'PASSWORD'
        assert history[0]['reason'] == 'SCHEDULED'


class TestMFARotation:
    """Tests for MFA secret rotation"""

    def test_rotate_mfa_success(self, temp_db):
        """Should rotate MFA secret"""
        rotator = CredentialRotator(temp_db)

        success, message = rotator.rotate_mfa_secret("owner1", "newsecret1234567890")

        assert success is True

    def test_mfa_history(self, temp_db):
        """Should record MFA rotation"""
        rotator = CredentialRotator(temp_db)

        rotator.rotate_mfa_secret("owner1", "newsecret1234567890", reason="SCHEDULED")

        history = rotator.get_rotation_history("owner1")

        assert any(h['rotation_type'] == 'MFA_SECRET' for h in history)


class TestRecoveryCodeGeneration:
    """Tests for recovery code generation"""

    def test_generate_recovery_codes(self, temp_db):
        """Should generate recovery codes"""
        manager = RecoveryCodeManager(temp_db)

        codes = manager.generate_recovery_codes("owner1", count=10)

        assert len(codes) == 10
        assert all("-" in code for code in codes)  # Format: XXXX-XXXX

    def test_recovery_code_format(self, temp_db):
        """Recovery codes should be formatted correctly"""
        manager = RecoveryCodeManager(temp_db)

        codes = manager.generate_recovery_codes("owner1", count=1)

        code = codes[0]
        parts = code.split("-")
        assert len(parts) == 2
        assert len(parts[0]) == 4
        assert len(parts[1]) == 4
        assert parts[0].isalnum()
        assert parts[1].isalnum()


class TestRecoveryCodeValidation:
    """Tests for recovery code validation"""

    def test_validate_recovery_code(self, temp_db):
        """Should validate recovery code"""
        manager = RecoveryCodeManager(temp_db)
        codes = manager.generate_recovery_codes("owner1", count=1)

        code = codes[0]
        success, message = manager.validate_recovery_code("owner1", code)

        assert success is True

    def test_recovery_code_one_time_use(self, temp_db):
        """Recovery code should be one-time use only"""
        manager = RecoveryCodeManager(temp_db)
        codes = manager.generate_recovery_codes("owner1", count=1)

        code = codes[0]

        # First use should succeed
        success1, msg1 = manager.validate_recovery_code("owner1", code)
        assert success1 is True

        # Second use should fail
        success2, msg2 = manager.validate_recovery_code("owner1", code)
        assert success2 is False
        assert "already used" in msg2.lower()

    def test_invalid_recovery_code(self, temp_db):
        """Should reject invalid recovery code"""
        manager = RecoveryCodeManager(temp_db)

        success, message = manager.validate_recovery_code("owner1", "INVALID-CODE")

        assert success is False
        assert "invalid" in message.lower()

    def test_recovery_status(self, temp_db):
        """Should track recovery code status"""
        manager = RecoveryCodeManager(temp_db)
        codes = manager.generate_recovery_codes("owner1", count=5)

        # Use one code
        manager.validate_recovery_code("owner1", codes[0])

        status = manager.get_recovery_status("owner1")

        assert status['total_codes'] == 5
        assert status['unused_codes'] == 4


class TestRecoveryFlow:
    """Tests for high-level recovery flow"""

    def test_setup_recovery(self, temp_db):
        """Should setup recovery codes"""
        flow = RecoveryFlow(temp_db)

        codes = flow.setup_recovery("owner1")

        assert len(codes) == 10

    def test_recover_account(self, temp_db):
        """Should recover account with code"""
        flow = RecoveryFlow(temp_db)

        codes = flow.setup_recovery("owner1")
        code = codes[0]

        success, message = flow.recover_account("owner1", code)

        assert success is True
        assert "proceed" in message.lower()

    def test_get_recovery_info(self, temp_db):
        """Should get recovery info"""
        flow = RecoveryFlow(temp_db)

        flow.setup_recovery("owner1")
        info = flow.get_recovery_info("owner1")

        assert info['status']['total_codes'] == 10
        assert info['status']['unused_codes'] == 10
        assert len(info['codes']) == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
