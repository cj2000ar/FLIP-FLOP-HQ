"""
Root Recovery for FlipFlop HQ
Handles recovery code generation and one-time use validation
"""

import secrets
import hashlib
import logging
import duckdb
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class RecoveryCodeManager:
    """Manages recovery codes for account recovery"""

    RECOVERY_CODE_LENGTH = 8  # 8 alphanumeric per code
    RECOVERY_CODES_PER_OWNER = 10  # Generate 10 codes at setup

    def __init__(self, db_path: str):
        self.db_path = db_path

    def generate_recovery_codes(self, owner_id: str, count: int = None) -> List[str]:
        """
        Generate recovery codes for owner
        Returns: list of codes (owner stores these securely)
        """
        if count is None:
            count = self.RECOVERY_CODES_PER_OWNER

        codes = []
        conn = duckdb.connect(self.db_path)

        try:
            # Delete any existing unused codes for owner (reset)
            conn.execute(
                "DELETE FROM recovery_codes WHERE owner_id = ? AND used_at IS NULL",
                [owner_id]
            )

            # Generate and insert new codes
            for sequence in range(1, count + 1):
                code = self._generate_code()
                code_hash = self._hash_code(code)
                recovery_code_id = str(uuid.uuid4())

                conn.execute("""
                    INSERT INTO recovery_codes
                    (recovery_code_id, owner_id, code_hash, code_sequence,
                     generated_at, expires_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP,
                            DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 365 DAY))
                """, [recovery_code_id, owner_id, code_hash, sequence])

                codes.append(code)

            conn.close()
            logger.info(f"Generated {count} recovery codes for owner {owner_id}")
            return codes

        except Exception as e:
            logger.error(f"Failed to generate recovery codes: {e}")
            conn.close()
            raise

    def validate_recovery_code(self, owner_id: str, code: str,
                               device_id: str = None, ip_address: str = None) -> Tuple[bool, str]:
        """
        Validate recovery code (one-time use)
        Returns: (success, message)
        """
        try:
            code_hash = self._hash_code(code)

            conn = duckdb.connect(self.db_path)

            # Find matching code
            result = conn.execute("""
                SELECT recovery_code_id, used_at, expires_at
                FROM recovery_codes
                WHERE owner_id = ? AND code_hash = ?
            """, [owner_id, code_hash]).fetchall()

            if not result:
                logger.warning(f"Invalid recovery code attempt for owner {owner_id}")
                conn.close()
                return False, "Invalid recovery code"

            recovery_code_id, used_at, expires_at = result[0]

            # Check if already used
            if used_at:
                logger.warning(f"Recovery code {recovery_code_id} already used")
                conn.close()
                return False, "Recovery code already used"

            # Check if expired
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at and expires_at < datetime.utcnow():
                logger.warning(f"Recovery code {recovery_code_id} expired")
                conn.close()
                return False, "Recovery code expired"

            # Mark as used
            conn.execute("""
                UPDATE recovery_codes
                SET used_at = CURRENT_TIMESTAMP, used_by_device_id = ?, used_by_ip_address = ?
                WHERE recovery_code_id = ?
            """, [device_id, ip_address, recovery_code_id])

            conn.close()
            logger.info(f"Recovery code {recovery_code_id} used for owner {owner_id}")
            return True, "Recovery code valid"

        except Exception as e:
            logger.error(f"Recovery code validation failed: {e}")
            return False, str(e)

    def get_recovery_status(self, owner_id: str) -> dict:
        """Get recovery code status for owner"""
        try:
            conn = duckdb.connect(self.db_path)

            result = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN used_at IS NULL THEN 1 ELSE 0 END) as unused,
                       MAX(generated_at) as last_generated
                FROM recovery_codes
                WHERE owner_id = ?
            """, [owner_id]).fetchall()

            conn.close()

            if result:
                row = result[0]
                return {
                    'total_codes': row[0] or 0,
                    'unused_codes': row[1] or 0,
                    'last_generated': row[2]
                }

            return {
                'total_codes': 0,
                'unused_codes': 0,
                'last_generated': None
            }

        except Exception as e:
            logger.error(f"Failed to get recovery status: {e}")
            return {}

    def list_recovery_codes(self, owner_id: str) -> List[dict]:
        """List recovery codes for owner (doesn't return actual codes)"""
        try:
            conn = duckdb.connect(self.db_path)

            results = conn.execute("""
                SELECT recovery_code_id, code_sequence, generated_at, used_at,
                       used_by_device_id, used_by_ip_address, expires_at
                FROM recovery_codes
                WHERE owner_id = ?
                ORDER BY code_sequence
            """, [owner_id]).fetchall()

            conn.close()

            codes = []
            for row in results:
                codes.append({
                    'sequence': row[1],
                    'generated_at': row[2],
                    'used_at': row[3],
                    'used_by_device_id': row[4],
                    'used_by_ip_address': row[5],
                    'is_used': row[3] is not None,
                    'expires_at': row[6]
                })

            return codes

        except Exception as e:
            logger.error(f"Failed to list recovery codes: {e}")
            return []

    def _generate_code(self) -> str:
        """Generate single recovery code"""
        # Format: XXXX-XXXX (8 alphanumeric characters split into 2 groups)
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        code = ''.join(secrets.choice(chars) for _ in range(self.RECOVERY_CODE_LENGTH))
        return f"{code[:4]}-{code[4:]}"

    def _hash_code(self, code: str) -> str:
        """Hash recovery code for storage (never store plaintext)"""
        # Remove dashes for hashing
        code_clean = code.replace('-', '')
        return hashlib.sha256(code_clean.encode()).hexdigest()


class RecoveryFlow:
    """High-level recovery flow"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.recovery_manager = RecoveryCodeManager(db_path)

    def setup_recovery(self, owner_id: str) -> List[str]:
        """Setup recovery codes for owner (called after password+MFA setup)"""
        codes = self.recovery_manager.generate_recovery_codes(owner_id)
        logger.info(f"Recovery setup for owner {owner_id}: {len(codes)} codes generated")
        return codes

    def recover_account(self, owner_id: str, recovery_code: str,
                        device_id: str = None, ip_address: str = None) -> Tuple[bool, str]:
        """
        Recover account using recovery code
        After validation, owner can:
        1. Reset password
        2. Re-setup MFA
        3. Re-register devices
        """
        success, message = self.recovery_manager.validate_recovery_code(
            owner_id, recovery_code, device_id, ip_address
        )

        if success:
            logger.info(f"Account recovery initiated for owner {owner_id}")
            return True, "Recovery code valid. Proceed to reset credentials."
        else:
            return False, message

    def get_recovery_info(self, owner_id: str) -> dict:
        """Get recovery status and code summary for owner"""
        status = self.recovery_manager.get_recovery_status(owner_id)
        codes = self.recovery_manager.list_recovery_codes(owner_id)

        return {
            'status': status,
            'codes': codes
        }
