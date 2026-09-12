"""
Device Fingerprinting for FlipFlop HQ
Generates stable device identifiers from OS, hardware, and browser data
"""

import hashlib
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceInfo:
    """Immutable device information"""
    os_name: str  # "Windows 11", "macOS 14", "iOS 17"
    os_version: str
    browser_name: str  # "Chrome", "Safari", "Firefox"
    browser_version: str
    hardware_id: str  # Hashed machine/device ID
    user_agent: str = ""
    timestamp: str = None

    def __post_init__(self):
        if not self.os_name or not self.browser_name:
            raise ValueError("os_name and browser_name required")
        if not self.hardware_id:
            raise ValueError("hardware_id required (must be non-empty hash)")


class DeviceFingerprinter:
    """Generates stable device fingerprints"""

    def __init__(self):
        self.fingerprint_version = "1.0"

    def generate_fingerprint(self, device_info: DeviceInfo) -> str:
        """
        Generate stable device fingerprint from device info.
        Fingerprint = SHA256(hardware_id). OS/browser are stored as metadata only:
        binding is to the machine, so browser/OS updates do not trigger re-challenge.
        """
        data = device_info.hardware_id
        fingerprint = hashlib.sha256(data.encode()).hexdigest()
        logger.debug(f"Generated fingerprint: {fingerprint[:16]}... for {device_info.os_name} / {device_info.browser_name}")
        return fingerprint

    def parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """
        Extract browser and OS from user agent string
        Returns: {browser_name, browser_version, os_name, os_version}
        """
        # Simple parsing (production would use a library like user-agents)
        browser_name = "Unknown"
        browser_version = "Unknown"
        os_name = "Unknown"
        os_version = "Unknown"

        user_agent_lower = user_agent.lower()

        # Detect OS
        if "windows" in user_agent_lower:
            os_name = "Windows"
            if "windows nt 10.0" in user_agent_lower:
                os_version = "11"
            elif "windows nt 6.3" in user_agent_lower:
                os_version = "8.1"
            elif "windows nt 6.2" in user_agent_lower:
                os_version = "8"
        elif "macintosh" in user_agent_lower or "mac os" in user_agent_lower:
            os_name = "macOS"
            if "mac os x" in user_agent_lower:
                # Extract version number
                import re
                match = re.search(r'mac os x ([\d_]+)', user_agent_lower)
                if match:
                    os_version = match.group(1).replace('_', '.')
        elif "linux" in user_agent_lower:
            os_name = "Linux"
            os_version = "Linux"
        elif "iphone" in user_agent_lower:
            os_name = "iOS"
            import re
            match = re.search(r'os ([\d_]+)', user_agent_lower)
            if match:
                os_version = match.group(1).replace('_', '.')
        elif "android" in user_agent_lower:
            os_name = "Android"
            import re
            match = re.search(r'android ([\d.]+)', user_agent_lower)
            if match:
                os_version = match.group(1)

        # Detect Browser
        if "chrome" in user_agent_lower and "edg" not in user_agent_lower:
            browser_name = "Chrome"
            import re
            match = re.search(r'chrome/([\d.]+)', user_agent_lower)
            if match:
                browser_version = match.group(1)
        elif "safari" in user_agent_lower and "chrome" not in user_agent_lower:
            browser_name = "Safari"
            import re
            match = re.search(r'version/([\d.]+)', user_agent_lower)
            if match:
                browser_version = match.group(1)
        elif "firefox" in user_agent_lower:
            browser_name = "Firefox"
            import re
            match = re.search(r'firefox/([\d.]+)', user_agent_lower)
            if match:
                browser_version = match.group(1)
        elif "edg" in user_agent_lower:
            browser_name = "Edge"
            import re
            match = re.search(r'edg/([\d.]+)', user_agent_lower)
            if match:
                browser_version = match.group(1)

        return {
            'browser_name': browser_name,
            'browser_version': browser_version,
            'os_name': os_name,
            'os_version': os_version
        }

    def create_device_info(self, user_agent: str, hardware_id: str) -> DeviceInfo:
        """Create DeviceInfo from user agent and hardware ID"""
        parsed = self.parse_user_agent(user_agent)
        return DeviceInfo(
            os_name=parsed['os_name'],
            os_version=parsed['os_version'],
            browser_name=parsed['browser_name'],
            browser_version=parsed['browser_version'],
            hardware_id=hardware_id,
            user_agent=user_agent,
            timestamp=datetime.utcnow().isoformat()
        )


class HardwareIDGenerator:
    """Generates stable hardware IDs from various sources"""

    @staticmethod
    def generate_from_system() -> str:
        """
        Generate hardware ID from system identifiers
        SECURITY: This is a placeholder. Real implementation depends on:
        - Windows: UUID from WMI (Win32_ComputerSystemProduct.UUID)
        - macOS: system.uuid() or IOPlatformUUID
        - Linux: /etc/machine-id or /sys/class/dmi/id/product_uuid
        """
        import platform
        import uuid

        # Fallback: use MAC address (can change on network change)
        try:
            mac = uuid.getnode()
            machine_id = uuid.UUID(int=mac).hex
        except Exception:
            machine_id = str(uuid.uuid4())

        # Hash with hostname for extra entropy
        data = f"{platform.node()}|{machine_id}|{platform.machine()}"
        hw_id = hashlib.sha256(data.encode()).hexdigest()

        logger.debug(f"Generated hardware ID: {hw_id[:16]}...")
        return hw_id


def main():
    """CLI for fingerprinting"""
    import sys

    logging.basicConfig(level=logging.INFO)

    fingerprinter = DeviceFingerprinter()
    hw_gen = HardwareIDGenerator()

    if len(sys.argv) > 1:
        user_agent = sys.argv[1]
    else:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    hardware_id = hw_gen.generate_from_system()
    device_info = fingerprinter.create_device_info(user_agent, hardware_id)
    fingerprint = fingerprinter.generate_fingerprint(device_info)

    print(json.dumps({
        'fingerprint': fingerprint,
        'device_info': {
            'os_name': device_info.os_name,
            'os_version': device_info.os_version,
            'browser_name': device_info.browser_name,
            'browser_version': device_info.browser_version,
            'hardware_id': hardware_id[:16] + '...',
            'timestamp': device_info.timestamp
        }
    }, indent=2))


if __name__ == '__main__':
    main()
