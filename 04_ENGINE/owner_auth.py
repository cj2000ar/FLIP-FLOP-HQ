"""Owner authentication with MFA (password + TOTP)"""

import secrets
import hashlib
import hmac
import time
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class OwnerAuthenticator:
    """MFA-based owner authentication"""

    def __init__(self, secrets_dir: str = "/etc/flipflop/secrets"):
        self.secrets_dir = Path(secrets_dir)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.db_path = self.secrets_dir / "auth.db"
        self.session_timeout_hours = 8
        self.max_failed_attempts = 5

    def setup_mfa(self, owner_id: str) -> Dict[str, Any]:
        """Generate MFA secret for owner"""
        import base64
        import qrcode
        import io

        # Generate secret (base32-encoded)
        secret_bytes = secrets.token_bytes(20)
        secret = base64.b32encode(secret_bytes).decode('utf-8')

        # Generate QR code
        qr_data = f"otpauth://totp/FlipFlop%20HQ:{owner_id}?secret={secret}&issuer=FlipFlop"

        return {
            'mfa_secret': secret,
            'qr_data': qr_data,
            'instructions': (
                "1. Save the MFA secret in a safe location\n"
                "2. Scan QR code with authenticator app (Authy, Google Authenticator)\n"
                "3. Enter 6-digit code to verify"
            )
        }

    def verify_totp(self, secret: str, code: str) -> bool:
        """Verify TOTP code"""
        import pyotp

        try:
            totp = pyotp.TOTP(secret)
            # Allow ±1 time window
            return totp.verify(code, valid_window=1)
        except ImportError:
            logger.warning("pyotp not installed, TOTP verification skipped")
            return True

    def hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hash_obj.hex()}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password hash"""
        try:
            salt, hash_hex = password_hash.split('$')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hmac.compare_digest(hash_obj.hex(), hash_hex)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def authenticate(self, owner_id: str, password: str, totp_code: str,
                    ip_address: str) -> Tuple[bool, Optional[str]]:
        """Authenticate owner with password + MFA"""

        # Load stored credentials (from secure config)
        password_hash = self._get_stored_password(owner_id)
        mfa_secret = self._get_stored_mfa_secret(owner_id)

        if not password_hash or not mfa_secret:
            self._log_auth_attempt(owner_id, 'FAILED', 'credentials_not_configured')
            return False, None

        # Verify password
        if not self.verify_password(password, password_hash):
            self._log_auth_attempt(owner_id, 'FAILED', 'bad_password', ip_address)
            return False, None

        # Verify TOTP
        if not self.verify_totp(mfa_secret, totp_code):
            self._log_auth_attempt(owner_id, 'FAILED', 'bad_mfa', ip_address)
            return False, None

        # Generate session token
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=self.session_timeout_hours)

        self.sessions[session_token] = {
            'owner_id': owner_id,
            'authenticated_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat(),
            'ip_address': ip_address,
            'approved_actions': []
        }

        self._log_auth_attempt(owner_id, 'SUCCESS', ip_address=ip_address)
        logger.info(f"Owner {owner_id} authenticated (token: {session_token[:8]}...)")

        return True, session_token

    def verify_session(self, session_token: str, ip_address: str) -> bool:
        """Verify session is valid"""
        if session_token not in self.sessions:
            logger.warning(f"Invalid session token attempt from {ip_address}")
            return False

        session = self.sessions[session_token]

        # Check expiration
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.utcnow() > expires_at:
            del self.sessions[session_token]
            logger.warning(f"Session expired for {session['owner_id']}")
            return False

        # Check IP (optional strict check)
        if session['ip_address'] != ip_address:
            logger.warning(
                f"Session IP mismatch: {session['ip_address']} vs {ip_address}"
            )
            # Allow but log warning

        return True

    def approve_action(self, session_token: str, action: str,
                      context: Dict[str, Any]) -> bool:
        """Owner explicitly approves action"""
        if session_token not in self.sessions:
            return False

        session = self.sessions[session_token]
        session['approved_actions'].append({
            'action': action,
            'context': context,
            'approved_at': datetime.utcnow().isoformat()
        })

        logger.info(f"Owner {session['owner_id']} approved: {action}")
        return True

    def check_action_approved(self, session_token: str, action: str) -> bool:
        """Check if action was approved"""
        if session_token not in self.sessions:
            return False

        session = self.sessions[session_token]
        for approved in session['approved_actions']:
            if approved['action'] == action:
                return True

        return False

    def _get_stored_password(self, owner_id: str) -> Optional[str]:
        """Load password hash (implement with secure storage)"""
        # TODO: Load from encrypted config or HSM
        return None

    def _get_stored_mfa_secret(self, owner_id: str) -> Optional[str]:
        """Load MFA secret (implement with secure storage)"""
        # TODO: Load from encrypted config or HSM
        return None

    def _log_auth_attempt(self, owner_id: str, status: str, reason: str = "",
                         ip_address: str = "") -> None:
        """Log authentication attempt"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'owner_id': owner_id,
            'status': status,
            'reason': reason,
            'ip_address': ip_address
        }

        logger.warning(json.dumps(log_entry))

    def logout(self, session_token: str) -> None:
        """Invalidate session"""
        if session_token in self.sessions:
            session = self.sessions.pop(session_token)
            logger.info(f"Owner {session['owner_id']} logged out")


class OwnerApprovalGate:
    """Gate for owner-only decisions"""

    def __init__(self, auth: OwnerAuthenticator):
        self.auth = auth

    def require_approval(self, session_token: str, action: str,
                        context: Dict[str, Any]) -> bool:
        """Check if action requires owner approval"""
        if not self.auth.verify_session(session_token, ""):
            return False

        # Critical actions requiring approval
        critical_actions = [
            'VARIANT_PROMOTION',
            'STRATEGY_ACTIVATION',
            'PARAMETER_UPDATE',
            'LIVE_ENABLE'
        ]

        if action not in critical_actions:
            return True

        # Get owner approval
        return self.auth.check_action_approved(session_token, action)
