#!/bin/bash
# Guardian V2 Bootstrap - Linux/macOS
# Stages and verifies package before launching V2 application
# Authority: ZERO
# Exit Code: 78 on Guardian verification failure
# Date: 2026-09-07

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <manifest_path> [browser_url]"
    echo "  manifest_path: Path to artifact manifest JSON"
    echo "  browser_url: Optional browser URL (default: http://localhost:3000)"
    exit 78
fi

MANIFEST_PATH="$1"
BROWSER_URL="${2:-http://localhost:3000}"

echo "[Guardian V2] Bootstrap starting..."
echo "[Guardian V2] Manifest: $MANIFEST_PATH"
echo "[Guardian V2] Browser URL: $BROWSER_URL"

# Verify manifest exists
if [ ! -f "$MANIFEST_PATH" ]; then
    echo "[Guardian V2] Manifest not found: $MANIFEST_PATH"
    exit 78
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="$(dirname "$SCRIPT_DIR")"

# Change to engine directory
cd "$ENGINE_DIR"

# Activate Python venv if it exists
if [ -f "venv/bin/activate" ]; then
    echo "[Guardian V2] Activating Python venv..."
    source venv/bin/activate
fi

# Launch V2 launcher
echo "[Guardian V2] Invoking V2 launcher..."
LAUNCHER_SCRIPT="$SCRIPT_DIR/guardian_v2_launcher.py"

python3 "$LAUNCHER_SCRIPT" "$MANIFEST_PATH" "$BROWSER_URL"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 78 ]; then
    echo "[Guardian V2] Verification failed. Exit code: 78"
    exit 78
elif [ $EXIT_CODE -eq 0 ]; then
    echo "[Guardian V2] Bootstrap successful."
    exit 0
else
    echo "[Guardian V2] Unexpected exit code: $EXIT_CODE"
    exit $EXIT_CODE
fi
