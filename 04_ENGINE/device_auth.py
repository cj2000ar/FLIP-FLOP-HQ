"""
Device-Bound Authentication for FlipFlop HQ
Handles device registration, new-device challenge, and device-based auth
"""

import uuid
import logging
import duckdb
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta
from device_fingerprint import DeviceFingerprinter, HardwareIDGenerator, DeviceInfo

logger = logging.getLogger(__name__)


class DeviceAuthManager:
    """Manages device-bound authentication"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.fingerprinter = DeviceFingerprinter()
        self.hw_gen = HardwareIDGenerator()

    def register_device(self, owner_id: str, device_info: DeviceInfo,
                       is_primary: bool = False) -> Tuple[bool, str]:
        """
        Register new device for owner
        Returns: (success, device_id or error_message)
        """
        try:
            device_id = str(uuid.uuid4())
            fingerprint = self.fingerprinter.generate_fingerprint(device_info)

            conn = duckdb.connect(self.db_path)

            # Check if fingerprint already registered (for this owner or globally)
            existing = conn.execute(
                "SELECT device_id, owner_id FROM device_registrations WHERE device_fingerprint = ?",
                [fingerprint]
            ).fetchall()

            if existing:
                existing_device_id, existing_owner_id = existing[0]
                if existing_owner_id == owner_id:
                    conn.close()
                    return False, f"Device already registered (ID: {existing_device_id})"
                else:
                    # Fingerprint collision (different owner) - log as security event
                    logger.warning(f"Fingerprint collision: owner {owner_id} vs {existing_owner_id}")

            # Insert device
            conn.execute("""
                INSERT INTO device_registrations
                (device_id, owner_id, device_name, device_fingerprint, device_type,
                 os_name, browser_name, registered_at, is_primary, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, TRUE)
            """, [
                device_id,
                owner_id,
                f"{device_info.os_name} / {device_info.browser_name}",
                fingerprint,
                "desktop" if "windows" in device_info.os_name.lower() or "mac" in device_info.os_name.lower() else "mobile",
                device_info.os_name,
                device_info.browser_name,
                is_primary
            ])

            # If this is primary and owner has existing primary, demote old one
            if is_primary:
                conn.execute(
                    "UPDATE device_registrations SET is_primary = FALSE WHERE owner_id = ? AND device_id != ?",
                    [owner_id, device_id]
                )

            conn.close()
            logger.info(f"Device {device_id} registered for owner {owner_id}")
            return True, device_id

        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return False, str(e)

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device info"""
        try:
            conn = duckdb.connect(self.db_path)
            result = conn.execute("""
                SELECT device_id, owner_id, device_name, device_fingerprint, device_type,
                       os_name, browser_name, last_ip_address, last_seen_at, registered_at,
                       is_primary, is_active
                FROM device_registrations WHERE device_id = ?
            """, [device_id]).fetchall()

            conn.close()

            if result:
                row = result[0]
                return {
                    'device_id': row[0],
                    'owner_id': row[1],
                    'device_name': row[2],
                    'device_fingerprint': row[3],
                    'device_type': row[4],
                    'os_name': row[5],
                    'browser_name': row[6],
                    'last_ip_address': row[7],
                    'last_seen_at': row[8],
                    'registered_at': row[9],
                    'is_primary': row[10],
                    'is_active': row[11]
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get device: {e}")
            return None

    def list_owner_devices(self, owner_id: str) -> List[Dict[str, Any]]:
        """List all devices for owner"""
        try:
            conn = duckdb.connect(self.db_path)
            results = conn.execute("""
                SELECT device_id, device_name, os_name, browser_name, last_seen_at,
                       is_primary, is_active
                FROM device_registrations
                WHERE owner_id = ?
                ORDER BY last_seen_at DESC
            """, [owner_id]).fetchall()

            conn.close()

            devices = []
            for row in results:
                devices.append({
                    'device_id': row[0],
                    'device_name': row[1],
                    'os_name': row[2],
                    'browser_name': row[3],
                    'last_seen_at': row[4],
                    'is_primary': row[5],
                    'is_active': row[6]
                })

            return devices

        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    def challenge_new_device(self, owner_id: str, device_fingerprint: str) -> Tuple[bool, str]:
        """
        Create challenge for new device (requires recovery code or MFA)
        Returns: (is_known_device, challenge_id or error)
        """
        try:
            conn = duckdb.connect(self.db_path)

            # Check if device fingerprint is known for this owner
            existing = conn.execute(
                "SELECT device_id FROM device_registrations WHERE owner_id = ? AND device_fingerprint = ?",
                [owner_id, device_fingerprint]
            ).fetchall()

            conn.close()

            if existing:
                # Device is known and registered
                return True, existing[0][0]
            else:
                # New device - would require recovery code or re-auth with MFA
                challenge_id = str(uuid.uuid4())
                logger.info(f"New device challenge for owner {owner_id}: {challenge_id}")
                return False, challenge_id

        except Exception as e:
            logger.error(f"Failed to challenge device: {e}")
            return False, str(e)

    def update_device_activity(self, device_id: str, ip_address: str) -> bool:
        """Update last seen timestamp and IP"""
        try:
            conn = duckdb.connect(self.db_path)
            conn.execute("""
                UPDATE device_registrations
                SET last_seen_at = CURRENT_TIMESTAMP, last_ip_address = ?
                WHERE device_id = ?
            """, [ip_address, device_id])
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update device activity: {e}")
            return False

    def deactivate_device(self, device_id: str) -> bool:
        """Deactivate device (e.g., lost device)"""
        try:
            conn = duckdb.connect(self.db_path)
            conn.execute(
                "UPDATE device_registrations SET is_active = FALSE WHERE device_id = ?",
                [device_id]
            )
            conn.close()
            logger.info(f"Device {device_id} deactivated")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate device: {e}")
            return False

    def get_primary_device(self, owner_id: str) -> Optional[str]:
        """Get owner's primary device ID"""
        try:
            conn = duckdb.connect(self.db_path)
            result = conn.execute(
                "SELECT device_id FROM device_registrations WHERE owner_id = ? AND is_primary = TRUE",
                [owner_id]
            ).fetchall()
            conn.close()

            if result:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"Failed to get primary device: {e}")
            return None


class DeviceAuthFlow:
    """High-level device auth flow (registration + login)"""

    def __init__(self, db_path: str):
        self.manager = DeviceAuthManager(db_path)
        self.fingerprinter = DeviceFingerprinter()
        self.hw_gen = HardwareIDGenerator()

    def login_with_device(self, owner_id: str, user_agent: str,
                         hardware_id: str, ip_address: str) -> Tuple[bool, str]:
        """
        Login flow: check device, update activity
        Returns: (success, device_id or error)
        """
        try:
            device_info = self.fingerprinter.create_device_info(user_agent, hardware_id)
            fingerprint = self.fingerprinter.generate_fingerprint(device_info)

            is_known, result = self.manager.challenge_new_device(owner_id, fingerprint)

            if is_known:
                # Known device - update activity
                device_id = result
                self.manager.update_device_activity(device_id, ip_address)
                logger.info(f"Login on known device {device_id} for owner {owner_id}")
                return True, device_id
            else:
                # New device - requires recovery code or MFA re-auth
                logger.warning(f"New device challenge for owner {owner_id}")
                return False, f"New device detected. Challenge: {result}"

        except Exception as e:
            logger.error(f"Login flow failed: {e}")
            return False, str(e)
