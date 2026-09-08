#!/bin/bash
# FlipFlop HQ - VPS installer. Run as root on Ubuntu 24.04 after uploading app.tar.gz to /root.
set -euo pipefail

APP=/opt/flipflop
VENV=/opt/ffvenv
log() { echo -e "\033[0;32m[INSTALL]\033[0m $*"; }

log "Stopping stub API"
pkill -f "/opt/api.py" 2>/dev/null || true

log "Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3.12-venv nginx fail2ban >/dev/null

log "Unpacking application"
rm -rf "$APP"
mkdir -p "$APP"
tar -xzf /root/app.tar.gz -C "$APP"

log "Building venv"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q fastapi uvicorn pydantic python-multipart python-json-logger

log "Creating systemd service"
cat > /etc/systemd/system/flipflop-api.service <<EOF
[Unit]
Description=FlipFlop HQ API
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP/04_ENGINE
Environment=API_PORT=8000
Environment=API_HOST=0.0.0.0
Environment=PYTHONPATH=$APP/04_ENGINE:$APP/04_ENGINE/RED_DRAGON
Environment=AUTHORITY=ZERO
Environment=LIVE_ENABLED=false
Environment=BROKER_ORDERS_ALLOWED=false
ExecStart=$VENV/bin/python $APP/04_ENGINE/hp_api.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/flipflop-api.log
StandardError=append:/var/log/flipflop-api.log

[Install]
WantedBy=multi-user.target
EOF

log "Configuring nginx for dashboard"
cat > /etc/nginx/sites-available/flipflop <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    root /opt/flipflop/dashboard;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/flipflop /etc/nginx/sites-enabled/flipflop
nginx -t

log "Enabling fail2ban (SSH brute-force protection)"
systemctl enable --now fail2ban >/dev/null 2>&1 || true

log "Starting services"
systemctl daemon-reload
systemctl enable --now flipflop-api
systemctl restart nginx
sleep 4

log "Verifying"
systemctl is-active --quiet flipflop-api && echo "  api service: active" || echo "  api service: FAILED"
curl -sf http://localhost:8000/health && echo "" || echo "  health: no response (see /var/log/flipflop-api.log)"
curl -sf -o /dev/null -w "  dashboard http: %{http_code}\n" http://localhost/ || true

echo ""
echo "Done. Dashboard: http://208.68.36.209/   API: http://208.68.36.209:8000/health"
echo "Logs: journalctl -u flipflop-api -n 50 --no-pager"
