"""
Guardian V2 Launcher - Staged Browser Launch + Package Verification
Secure launch sequence with Guardian package verification before browser startup.

Authority: ZERO
Exit Code: 78 on Guardian verification failure
Date: 2026-09-07
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from guardian_package_verifier import (
    GuardianPackageVerifier,
    ArtifactManifest,
    VerificationStatus
)


class GuardianV2Launcher:
    """Secure V2 launcher with staged browser launch"""

    GUARDIAN_EXIT_CODE = 78

    def __init__(self, manifest_path: str):
        """Initialize launcher with artifact manifest"""
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest()
        self.verifier = GuardianPackageVerifier()
        self.correlation_id = str(uuid4())

    def _load_manifest(self) -> ArtifactManifest:
        """Load and parse artifact manifest"""
        with open(self.manifest_path, 'r') as f:
            data = json.load(f)

        return ArtifactManifest(
            strategy_hash=data['strategy_hash'],
            engine_hash=data['engine_hash'],
            ui_hash=data['ui_hash'],
            passport_hash=data['passport_hash'],
            created_at=data.get('created_at', datetime.utcnow().isoformat())
        )

    def verify_and_launch(
        self,
        artifact_paths: Dict[str, str],
        browser_url: str = "http://localhost:3000"
    ) -> Tuple[bool, str]:
        """
        Staged launch: verify package, then launch browser.
        Returns (success, message).
        Exits with code 78 on verification failure.
        """
        print(f"[Guardian V2] Correlation ID: {self.correlation_id}")
        print(f"[Guardian V2] Starting package verification...")

        # Stage 1: Verify package
        overall_status, events = self.verifier.verify_package(
            self.manifest,
            artifact_paths,
            self.correlation_id
        )

        # Log verification results
        for event in events:
            print(f"  [{event.artifact_type}] {event.status.value}")

        # Fail-fast: exit 78 if verification failed
        if overall_status != VerificationStatus.PASS:
            print(f"\n[Guardian V2] VERIFICATION FAILED: {overall_status.value}")
            print(f"[Guardian V2] Exit code: {self.GUARDIAN_EXIT_CODE}")
            sys.exit(self.GUARDIAN_EXIT_CODE)

        print(f"[Guardian V2] Package verification PASSED")

        # Stage 2: Launch browser
        print(f"[Guardian V2] Launching browser stage...")
        success = self._launch_browser(browser_url)

        if not success:
            print(f"[Guardian V2] Browser launch failed")
            return False, "Browser launch failed"

        return True, f"Launched at {browser_url}"

    def _launch_browser(self, url: str) -> bool:
        """Launch browser to URL (cross-platform)"""
        try:
            import webbrowser
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"[Guardian V2] Browser error: {e}")
            return False

    def get_verification_events(self) -> list:
        """Get all verification events for this launch"""
        return self.verifier.get_verification_events(self.correlation_id)


def main():
    """CLI entry point for V2 launcher"""
    if len(sys.argv) < 2:
        print("Usage: python guardian_v2_launcher.py <manifest_path> [browser_url]")
        sys.exit(1)

    manifest_path = sys.argv[1]
    browser_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3000"

    # Infer artifact paths from manifest location
    base_dir = Path(manifest_path).parent
    artifact_paths = {
        "strategy": str(base_dir / "strategy.py"),
        "engine": str(base_dir / "engine.py"),
        "ui": str(base_dir / "ui.js"),
        "passport": str(base_dir / "passport.json"),
    }

    launcher = GuardianV2Launcher(manifest_path)
    success, message = launcher.verify_and_launch(artifact_paths, browser_url)

    if success:
        print(f"[Guardian V2] {message}")
        sys.exit(0)
    else:
        print(f"[Guardian V2] {message}")
        sys.exit(launcher.GUARDIAN_EXIT_CODE)


if __name__ == "__main__":
    main()
