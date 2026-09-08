#!/bin/bash
# FlipFlop HQ - VPS installer v2. Run as root on Ubuntu 24.04 after
# uploading app.tar.gz to /root. Idempotent: safe to rerun on updates.
#
# Layout after install:
#   /opt/flipflop        code, root-owned, read-only to the service
#   $DATA_DIR            databases + backups, owned by the service user,
#                        on the attached block volume if one is mounted
#   /etc/flipflop/env    secrets, root:flipflop 0640
#   /opt/ffvenv          Python virtualenv
set -euo pipefail

APP=/opt/flipflop
VENV=/opt/ffvenv
SVC_USER=flipflop
ENV_FILE=/etc/flipflop/env
DEPLOY_SHA="${DEPLOY_SHA:-unknown}"

log()   { echo -e "\033[0;32m[INSTALL]\033[0m $*"; }
abort() { echo -e "\033[0;31m[ABORT]\033[0m $*"; exit 1; }

# ── Data location: prefer the attached volume ────────────────────────────
DATA_DIR=/var/lib/flipflop
VOL_MOUNT="$(findmnt -rn -o TARGET -S "$(ls /dev/disk/by-id/scsi-0DO_Volume_* 2>/dev/null | head -n1)" 2>/dev/null || true)"
if [ -n "$VOL_MOUNT" ]; then
  DATA_DIR="$VOL_MOUNT/flipflop"
  log "Block volume mounted at $VOL_MOUNT; data goes to $DATA_DIR"
else
  log "No block volume detected; data goes to $DATA_DIR on the root disk"
fi

log "System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3.12-venv nginx fail2ban sqlite3 >/dev/null

log "Service user"
id -u "$SVC_USER" >/dev/null 2>&1 || useradd --system --home-dir "$DATA_DIR" --shell /usr/sbin/nologin "$SVC_USER"

log "Stopping service for code swap"
systemctl stop flipflop-api 2>/dev/null || true
pkill -f "/opt/api.py" 2>/dev/null || true

log "Code tree (root-owned, read-only to service)"
rm -rf "$APP.new"
mkdir -p "$APP.new"
tar -xzf /root/app.tar.gz -C "$APP.new"
echo "$DEPLOY_SHA" > "$APP.new/VERSION"
find "$APP.new" -type d -exec chmod 755 {} +
find "$APP.new" -type f -exec chmod 644 {} +
chown -R root:root "$APP.new"
# Keep the old tree until the new one is in place, then swap atomically.
[ -d "$APP" ] && mv "$APP" "$APP.prev"
mv "$APP.new" "$APP"

log "Data directory (service-owned, survives redeploys)"
mkdir -p "$DATA_DIR/db" "$DATA_DIR/backups"
# One-time migration from the v1 layout, where DBs lived inside the code tree.
for old in "$APP.prev"/04_ENGINE/hp_infra.db "$APP.prev"/04_ENGINE/databases/*.db; do
  [ -f "$old" ] && [ ! -f "$DATA_DIR/db/$(basename "$old")" ] && cp -p "$old" "$DATA_DIR/db/" && echo "  migrated $(basename "$old")"
done
rm -rf "$APP.prev"
chown -R "$SVC_USER:$SVC_USER" "$DATA_DIR"
chmod 750 "$DATA_DIR" "$DATA_DIR/db" "$DATA_DIR/backups"

log "Secrets"
mkdir -p /etc/flipflop
if [ ! -f "$ENV_FILE" ] || ! grep -q '^HP_HMAC_SECRET=' "$ENV_FILE"; then
  SECRET="$(openssl rand -hex 32)"
  {
    echo "HP_HMAC_SECRET=$SECRET"
  } >> "$ENV_FILE"
  echo "  generated HP_HMAC_SECRET"
fi
# Non-secret settings are rewritten every run so they track this script.
grep -v -E '^(API_HOST|API_PORT|FLIPFLOP_DB_PATH|CORS_ORIGINS|AUTHORITY|LIVE_ENABLED|BROKER_ORDERS_ALLOWED|PYTHONPATH)=' "$ENV_FILE" > "$ENV_FILE.tmp" || true
cat >> "$ENV_FILE.tmp" <<EOF
API_HOST=127.0.0.1
API_PORT=8000
FLIPFLOP_DB_PATH=$DATA_DIR/db
CORS_ORIGINS=
AUTHORITY=ZERO
LIVE_ENABLED=false
BROKER_ORDERS_ALLOWED=false
PYTHONPATH=$APP/04_ENGINE:$APP/04_ENGINE/RED_DRAGON
EOF
mv "$ENV_FILE.tmp" "$ENV_FILE"
chown root:"$SVC_USER" "$ENV_FILE"
chmod 640 "$ENV_FILE"

log "Virtualenv"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q fastapi uvicorn pydantic python-multipart python-json-logger pytest

log "Running test suites on this host (install aborts if red)"
cd "$APP/04_ENGINE"
set +e
sudo -u "$SVC_USER" env "PYTHONPATH=$APP/04_ENGINE:$APP/04_ENGINE/RED_DRAGON" FLIPFLOP_DB_PATH=/tmp/fftest-$$ \
  "$VENV/bin/python" -m pytest -q -p no:cacheprovider -p no:warnings \
  hp_tests.py test_api_config.py RED_DRAGON/guardian_tests.py 2>&1 | tail -n 3
RC=${PIPESTATUS[0]}
set -e
rm -rf "/tmp/fftest-$$"
[ "$RC" -eq 0 ] || abort "tests failed on host (exit $RC); service left stopped"

log "systemd unit"
cat > /etc/systemd/system/flipflop-api.service <<EOF
[Unit]
Description=FlipFlop HQ API
After=network-online.target
Wants=network-online.target
RequiresMountsFor=$DATA_DIR
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=$SVC_USER
Group=$SVC_USER
WorkingDirectory=$APP/04_ENGINE
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/python $APP/04_ENGINE/hp_api.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=flipflop-api

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
ReadWritePaths=$DATA_DIR

[Install]
WantedBy=multi-user.target
EOF

log "nginx: keep it up, and only allow reads through /api/ until auth exists"
mkdir -p /etc/systemd/system/nginx.service.d
cat > /etc/systemd/system/nginx.service.d/restart.conf <<'EOF'
[Service]
Restart=on-failure
RestartSec=3
EOF
cat > /etc/nginx/sites-available/flipflop <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    root /opt/flipflop/dashboard;
    index index.html;

    # Dashboard source maps expose the full TypeScript source.
    location ~ \.map$ { return 404; }

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        # The API has no authentication yet. Until it does, the internet
        # may read but not write. To re-enable writes, delete the
        # limit_except block below and reload nginx.
        limit_except GET HEAD { deny all; }
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

log "Backups: all databases, nightly, 14-day retention"
cat > /usr/local/bin/flipflop-backup <<EOF
#!/bin/bash
set -euo pipefail
DB=$DATA_DIR/db
OUT=$DATA_DIR/backups
STAMP=\$(date -u +%Y%m%dT%H%M%SZ)
for f in "\$DB"/*.db; do
  [ -f "\$f" ] || continue
  n=\$(basename "\$f" .db)
  sqlite3 "\$f" ".backup '\$OUT/\$n-\$STAMP.db'"
  gzip -f "\$OUT/\$n-\$STAMP.db"
done
find "\$OUT" -name '*.db.gz' -mtime +14 -delete
ls -1 "\$OUT" | wc -l | sed 's/^/backups on disk: /'
EOF
chmod 755 /usr/local/bin/flipflop-backup
cat > /etc/systemd/system/flipflop-backup.service <<EOF
[Unit]
Description=FlipFlop HQ database backup
[Service]
Type=oneshot
User=$SVC_USER
ExecStart=/usr/local/bin/flipflop-backup
EOF
cat > /etc/systemd/system/flipflop-backup.timer <<'EOF'
[Unit]
Description=Nightly FlipFlop HQ backup
[Timer]
OnCalendar=*-*-* 03:15:00 UTC
RandomizedDelaySec=10m
Persistent=true
[Install]
WantedBy=timers.target
EOF

log "fail2ban"
systemctl enable --now fail2ban >/dev/null 2>&1 || true

log "Start"
systemctl daemon-reload
systemctl enable --now flipflop-api flipflop-backup.timer >/dev/null
systemctl restart nginx
sleep 4

log "First backup (proves the pipeline)"
systemctl start flipflop-backup.service && sleep 1
journalctl -u flipflop-backup -n 1 --no-pager -o cat | sed 's/^/  /'

log "Verify"
systemctl is-active --quiet flipflop-api && echo "  flipflop-api: active" || abort "flipflop-api not active: journalctl -u flipflop-api -n 30"
systemctl is-active --quiet nginx        && echo "  nginx: active"        || abort "nginx not active"
ss -tlnp | grep -q '127.0.0.1:8000' && echo "  api bound to loopback only" || abort "api not on 127.0.0.1:8000"
ss -tlnp | grep -q '0.0.0.0:8000'   && abort "api is listening on 0.0.0.0:8000" || true
curl -sf http://127.0.0.1:8000/health >/dev/null && echo "  api health: ok" || abort "api health failed"
curl -sf -o /dev/null -w "  dashboard: %{http_code}\n" http://localhost/
curl -sf -o /dev/null -w "  api via nginx (GET): %{http_code}\n" http://localhost/api/health
curl -s  -o /dev/null -w "  api via nginx (POST): %{http_code} (expect 403)\n" -X POST http://localhost/api/shadow/session/create
ps -o user= -p "$(systemctl show -p MainPID --value flipflop-api)" | sed 's/^/  api runs as: /'
stat -c '  %a %U:%G %n' "$DATA_DIR/db" "$ENV_FILE" "$APP"
systemctl list-timers flipflop-backup.timer --no-pager | sed -n '2p' | sed 's/^/  next backup: /'
echo "  deployed: $(cat "$APP/VERSION")"
echo ""
echo "Install verified."
