#!/bin/bash
# Bootstrap FlipFlop HQ Production (Linux/macOS)
# Run as: sudo bash bootstrap_production.sh

set -e

FLIPFLOP_USER="flipflop"
FLIPFLOP_HOME="/opt/flipflop"
FLIPFLOP_DATA="${FLIPFLOP_HOME}/data"
FLIPFLOP_DB="${FLIPFLOP_HOME}/databases"
FLIPFLOP_LOGS="/var/log/flipflop"
SECRETS_DIR="/etc/flipflop/secrets"

echo "🚀 FlipFlop HQ Production Bootstrap"
echo "=========================================="

# 1. Create flipflop user
echo "[1/8] Creating flipflop user..."
if ! id "$FLIPFLOP_USER" &>/dev/null; then
    useradd --system --home "$FLIPFLOP_HOME" --shell /bin/false "$FLIPFLOP_USER"
    echo "✓ User '$FLIPFLOP_USER' created"
else
    echo "✓ User '$FLIPFLOP_USER' already exists"
fi

# 2. Create directories
echo "[2/8] Creating directories..."
mkdir -p "$FLIPFLOP_DATA" "$FLIPFLOP_DB" "$FLIPFLOP_LOGS" "$SECRETS_DIR"
chown -R "$FLIPFLOP_USER:$FLIPFLOP_USER" "$FLIPFLOP_HOME" "$FLIPFLOP_LOGS"
chmod 700 "$SECRETS_DIR"
echo "✓ Directories created"

# 3. Install Python dependencies
echo "[3/8] Installing Python dependencies..."
python3 -m pip install -q alpaca-trade-api psutil requests python-dotenv
echo "✓ Dependencies installed"

# 4. Setup credentials
echo "[4/8] Setting up credentials..."
if [ ! -f "$SECRETS_DIR/market-api.env" ]; then
    cat > "$SECRETS_DIR/market-api.env" << 'EOF'
# Set these environment variables
ALPACA_API_KEY=
ALPACA_API_SECRET=
EOF
    chmod 600 "$SECRETS_DIR/market-api.env"
    echo "⚠ Created $SECRETS_DIR/market-api.env - UPDATE WITH YOUR CREDENTIALS"
else
    echo "✓ Credentials file exists"
fi

# 5. Copy systemd service
echo "[5/8] Installing systemd service..."
cp flipflop-scheduler.service /etc/systemd/system/
systemctl daemon-reload
echo "✓ Service installed"

# 6. Enable service
echo "[6/8] Enabling auto-start..."
systemctl enable flipflop-scheduler.service
echo "✓ Service enabled"

# 7. Start scheduler
echo "[7/8] Starting scheduler..."
systemctl start flipflop-scheduler.service
sleep 3
if systemctl is-active --quiet flipflop-scheduler.service; then
    echo "✓ Scheduler running"
else
    echo "✗ Scheduler failed to start"
    systemctl status flipflop-scheduler.service
    exit 1
fi

# 8. Verify health
echo "[8/8] Verifying health..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/flipflop')
from health_check import HealthChecker
hc = HealthChecker()
result = hc.check_all()
print(f"Status: {result['status']}")
if result['status'] != 'HEALTHY':
    print(f"Warnings: {result['failed_checks']}")
PYEOF

echo ""
echo "=========================================="
echo "✅ FlipFlop Bootstrap Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update credentials: /etc/flipflop/secrets/market-api.env"
echo "2. Monitor logs: journalctl -u flipflop-scheduler -f"
echo "3. Check status: systemctl status flipflop-scheduler"
echo ""
echo "Authority: ZERO"
echo "Live: OFF"
