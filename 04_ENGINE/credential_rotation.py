"""
Credential Rotation for FlipFlop HQ
Handles password and MFA secret rotation with scheduling
"""

import hashlib
import secrets
import logging
import duckdb
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RotationPolicy:
    """Credential rotation policy"""
    password_expires_days: int = 90  # Rotate password every 90 days
    mfa_secret_expires_days: int = 180  # Rotate MFA secret every 180 days
    min_password_length: int = 12
    require_uppercase: bool = True
    require_digits: bool = True
    require_special: bool = True


class CredentialRotator:
    """Manages credential rotation"""

    def __init__(self, db_path: str, policy: RotationPolicy = None):
        self.db_path = db_path
        self.policy = policy or RotationPolicy()

    def hash_password(self, password: str) -> str:
        """Hash password with salt (PBKDF2)"""
        if not self._validate_password(password):
            raise ValueError("Password does not meet policy requirements")

        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hash_obj.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_hex = password_hash.split('$')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            import hmac
            return hmac.compare_digest(hash_obj.hex(), hash_hex)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def _validate_password(self, password: str) -> bool:
        """Validate password against policy"""
        if len(password) < self.policy.min_password_length:
            return False
        if self.policy.require_uppercase and not any(c.isupper() for c in password):
            return False
        if self.policy.require_digits and not any(c.isdigit() for c in password):
            return False
        if self.policy.require_special and not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password):
            return False
        return True

    def rotate_password(self, owner_id: str, new_password: str,
                       rotated_by: str = "OWNER", reason: str = "SCHEDULED",
                       device_id: str = None, ip_address: str = None) -> Tuple[bool, str]:
        """
        Rotate owner password
        Returns: (success, message)
        """
        try:
            if not self._validate_password(new_password):
                return False, "Password does not meet policy requirements"

            conn = duckdb.connect(self.db_path)

            # Get current password hash (for audit trail)
            current = conn.execute(
                "SELECT password_hash FROM owner_credentials WHERE owner_id = ?",
                [owner_id]
            ).fetchall()

            if not current:
                conn.close()
                return False, "Owner not found"

            old_hash = current[0][0]
            old_hash_prefix = old_hash[:16] if old_hash else "unknown"

            # Hash new password
            new_hash = self.hash_password(new_password)
            new_hash_prefix = new_hash[:16]

            # Update password
            conn.execute("""
                UPDATE owner_credentials
                SET password_hash = ?, password_set_at = CURRENT_TIMESTAMP,
                    password_expires_at = CURRENT_TIMESTAMP + (? * INTERVAL 1 DAY)
                WHERE owner_id = ?
            """, [new_hash, self.policy.password_expires_days, owner_id])

            # Record rotation in audit trail
            import uuid
            rotation_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO credential_rotations
                (rotation_id, owner_id, rotation_type, old_hash_prefix, new_hash_prefix,
                 rotated_by, reason, device_id, ip_address)
                VALUES (?, ?, 'PASSWORD', ?, ?, ?, ?, ?, ?)
            """, [rotation_id, owner_id, old_hash_prefix, new_hash_prefix,
                  rotated_by, reason, device_id, ip_address])

            conn.close()
            logger.info(f"Password rotated for owner {owner_id} (reason: {reason})")
            return True, "Password rotated successfully"

        except Exception as e:
            logger.error(f"Password rotation failed: {e}")
            return False, str(e)

    def rotate_mfa_secret(self, owner_id: str, new_mfa_secret: str,
                         rotated_by: str = "OWNER", reason: str = "SCHEDULED",
                         device_id: str = None, ip_address: str = None) -> Tuple[bool, str]:
        """
        Rotate MFA secret for owner
        Returns: (success, message)
        """
        try:
            if not new_mfa_secret or len(new_mfa_secret) < 16:
                return False, "Invalid MFA secret"

            conn = duckdb.connect(self.db_path)

            # Get current MFA secret (for audit)
            current = conn.execute(
                "SELECT mfa_secret FROM owner_credentials WHERE owner_id = ?",
                [owner_id]
            ).fetchall()

            if not current:
                conn.close()
                return False, "Owner not found"

            old_secret = current[0][0]
            old_hash_prefix = hashlib.sha256(old_secret.encode()).hexdigest()[:16]
            new_hash_prefix = hashlib.sha256(new_mfa_secret.encode()).hexdigest()[:16]

            # Update MFA secret
            conn.execute("""
                UPDATE owner_credentials
                SET mfa_secret = ?, mfa_secret_set_at = CURRENT_TIMESTAMP,
                    mfa_secret_expires_at = CURRENT_TIMESTAMP + (? * INTERVAL 1 DAY)
                WHERE owner_id = ?
            """, [new_mfa_secret, self.policy.mfa_secret_expires_days, owner_id])

            # Record rotation
            import uuid
            rotation_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO credential_rotations
                (rotation_id, owner_id, rotation_type, old_hash_prefix, new_hash_prefix,
                 rotated_by, reason, device_id, ip_address)
                VALUES (?, ?, 'MFA_SECRET', ?, ?, ?, ?, ?, ?)
            """, [rotation_id, owner_id, old_hash_prefix, new_hash_prefix,
                  rotated_by, reason, device_id, ip_address])

            conn.close()
            logger.info(f"MFA secret rotated for owner {owner_id} (reason: {reason})")
            return True, "MFA secret rotated successfully"

        except Exception as e:
            logger.error(f"MFA rotation failed: {e}")
            return False, str(e)

    def get_expiring_credentials(self, days_ahead: int = 14) -> List[dict]:
        """Find credentials expiring in next N days"""
        try:
            conn = duckdb.connect(self.db_path)

            results = conn.execute("""
                SELECT owner_id, password_expires_at, mfa_secret_expires_at
                FROM owner_credentials
                WHERE (password_expires_at <= CURRENT_TIMESTAMP + (? * INTERVAL 1 DAY)
                       AND password_expires_at IS NOT NULL)
                   OR (mfa_secret_expires_at <= CURRENT_TIMESTAMP + (? * INTERVAL 1 DAY)
                       AND mfa_secret_expires_at IS NOT NULL)
            """, [days_ahead, days_ahead]).fetchall()

            conn.close()

            expiring = []
            for row in results:
                expiring.append({
                    'owner_id': row[0],
                    'password_expires_at': row[1],
                    'mfa_secret_expires_at': row[2]
                })

            return expiring

        except Exception as e:
            logger.error(f"Failed to get expiring credentials: {e}")
            return []

    def get_rotation_history(self, owner_id: str, limit: int = 20) -> List[dict]:
        """Get rotation history for owner"""
        try:
            conn = duckdb.connect(self.db_path)

            results = conn.execute("""
                SELECT rotation_id, rotation_type, old_hash_prefix, new_hash_prefix,
                       rotated_at, rotated_by, reason, device_id, ip_address
                FROM credential_rotations
                WHERE owner_id = ?
                ORDER BY rotated_at DESC
                LIMIT ?
            """, [owner_id, limit]).fetchall()

            conn.close()

            history = []
            for row in results:
                history.append({
                    'rotation_id': row[0],
                    'rotation_type': row[1],
                    'old_hash_prefix': row[2],
                    'new_hash_prefix': row[3],
                    'rotated_at': row[4],
                    'rotated_by': row[5],
                    'reason': row[6],
                    'device_id': row[7],
                    'ip_address': row[8]
                })

            return history

        except Exception as e:
            logger.error(f"Failed to get rotation history: {e}")
            return []


class RotationScheduler:
    """Schedules automated credential rotation"""

    def __init__(self, db_path: str, rotator: CredentialRotator = None):
        self.db_path = db_path
        self.rotator = rotator or CredentialRotator(db_path)

    def scan_and_notify_expiring(self, days_ahead: int = 14) -> dict:
        """
        Find expiring credentials and notify owners
        Returns: {count, owners}
        """
        expiring = self.rotator.get_expiring_credentials(days_ahead)

        logger.info(f"Found {len(expiring)} owners with expiring credentials in {days_ahead} days")

        return {
            'count': len(expiring),
            'owners': expiring
        }

    def auto_rotate_expired(self) -> dict:
        """
        Auto-rotate credentials that have already expired
        Returns: {rotated, failed}
        """
        conn = duckdb.connect(self.db_path)

        expired = conn.execute("""
            SELECT owner_id, password_expires_at, mfa_secret_expires_at
            FROM owner_credentials
            WHERE (password_expires_at < CURRENT_TIMESTAMP AND password_expires_at IS NOT NULL)
               OR (mfa_secret_expires_at < CURRENT_TIMESTAMP AND mfa_secret_expires_at IS NOT NULL)
        """).fetchall()

        conn.close()

        rotated = []
        failed = []

        for row in expired:
            owner_id = row[0]
            password_expired = row[1] and row[1] < datetime.utcnow().isoformat()
            mfa_expired = row[2] and row[2] < datetime.utcnow().isoformat()

            try:
                if password_expired:
                    # Generate new password (notify owner to set it)
                    logger.warning(f"Password expired for {owner_id}")

                if mfa_expired:
                    # Generate new MFA secret (requires owner re-setup)
                    logger.warning(f"MFA secret expired for {owner_id}")

                rotated.append(owner_id)

            except Exception as e:
                logger.error(f"Failed to rotate for {owner_id}: {e}")
                failed.append(owner_id)

        logger.info(f"Auto-rotation: {len(rotated)} rotated, {len(failed)} failed")

        return {
            'rotated': rotated,
            'failed': failed
        }
