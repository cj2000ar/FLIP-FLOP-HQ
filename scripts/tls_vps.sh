#!/usr/bin/env bash
# TLS certificate setup for FlipFlop HQ via Let's Encrypt
# Reads FLIPFLOP_DOMAIN and LETSENCRYPT_EMAIL from .env, issues cert, configures nginx HTTPS

set -euo pipefail

BOLD=$(tput bold 2>/dev/null || echo ''); RESET=$(tput sgr0 2>/dev/null || echo '')
GREEN=$(tput setaf 2 2>/dev/null || echo ''); YELLOW=$(tput setaf 3 2>/dev/null || echo '')

log() { echo "${BOLD}${GREEN}[TLS]${RESET} $*"; }
warn() { echo "${YELLOW}⚠ $*${RESET}"; }
err() { echo "${BOLD}${GREEN}[TLS]${RESET} ERROR: $*" >&2; exit 1; }

# Read .env
ENV_FILE="${1:-.env}"
[[ -f "$ENV_FILE" ]] || err ".env not found at $ENV_FILE"

FLIPFLOP_DOMAIN=$(grep -E '^FLIPFLOP_DOMAIN=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d ' ')
LETSENCRYPT_EMAIL=$(grep -E '^LETSENCRYPT_EMAIL=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d ' ')
LETSENCRYPT_TOS=$(grep -E '^LETSENCRYPT_TOS_AGREED=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d ' ')

[[ -n "$FLIPFLOP_DOMAIN" ]] || err "FLIPFLOP_DOMAIN not set in $ENV_FILE"
[[ -n "$LETSENCRYPT_EMAIL" ]] || err "LETSENCRYPT_EMAIL not set in $ENV_FILE"
[[ "$LETSENCRYPT_TOS" == "yes" ]] || err "LETSENCRYPT_TOS_AGREED must be 'yes'"

log "Domain: $FLIPFLOP_DOMAIN"
log "Email: $LETSENCRYPT_EMAIL"

# Verify domain resolves to droplet
log "Verifying DNS resolution..."
RESOLVED=$(dig +short "$FLIPFLOP_DOMAIN" A 2>/dev/null | tail -1)
[[ "$RESOLVED" == "208.68.36.209" ]] || err "Domain $FLIPFLOP_DOMAIN does not resolve to 208.68.36.209 (got: $RESOLVED)"
log "DNS verified: $FLIPFLOP_DOMAIN → $RESOLVED"

# Install certbot if needed
log "Checking certbot..."
if ! command -v certbot >/dev/null 2>&1; then
  log "Installing certbot..."
  apt-get update -qq && apt-get install -y certbot python3-certbot-nginx >/dev/null
fi

# Stop nginx temporarily for certbot standalone
log "Stopping nginx for certificate issuance..."
systemctl stop nginx

# Issue certificate
log "Requesting certificate from Let's Encrypt..."
certbot certonly \
  --standalone \
  --non-interactive \
  --agree-tos \
  --email "$LETSENCRYPT_EMAIL" \
  --domain "$FLIPFLOP_DOMAIN" \
  --key-type ecdsa \
  --elliptic-curve secp384r1 \
  || err "certbot failed"

CERT_DIR="/etc/letsencrypt/live/$FLIPFLOP_DOMAIN"
[[ -f "$CERT_DIR/fullchain.pem" ]] || err "Certificate file not found"
log "Certificate issued: $CERT_DIR"

# Update nginx config for HTTPS
log "Configuring nginx for HTTPS..."
cat > /etc/nginx/sites-enabled/default <<'EOF'
server {
  listen 80;
  listen [::]:80;
  server_name _;
  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl http2;
  listen [::]:443 ssl http2;
  server_name _;

  ssl_certificate /etc/letsencrypt/live/FLIPFLOP_DOMAIN/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/FLIPFLOP_DOMAIN/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers HIGH:!aNULL:!MD5;
  ssl_prefer_server_ciphers on;
  ssl_session_timeout 1d;
  ssl_session_cache shared:SSL:50m;
  ssl_stapling on;
  ssl_stapling_verify on;

  root /opt/flipflop/08_WEBSITE/flipflop-website-FULL/dist;
  index index.html;

  location / {
    try_files $uri $uri/ /index.html;
  }

  location /api/ {
    limit_except GET HEAD {
      deny all;
    }
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  error_page 404 =200 /index.html;
}
EOF

# Replace placeholder with actual domain
sed -i "s|FLIPFLOP_DOMAIN|$FLIPFLOP_DOMAIN|g" /etc/nginx/sites-enabled/default

# Test nginx config
log "Testing nginx configuration..."
nginx -t || err "nginx config test failed"

# Start nginx
log "Starting nginx..."
systemctl start nginx
systemctl enable nginx >/dev/null

# Verify HTTPS works
log "Verifying HTTPS..."
sleep 2
curl -s --insecure https://127.0.0.1/ -I >/dev/null || err "HTTPS verification failed"

# Set up certbot renewal timer
log "Configuring auto-renewal..."
systemctl enable certbot.timer >/dev/null 2>&1 || true
systemctl start certbot.timer >/dev/null 2>&1 || true

log "✓ TLS setup complete"
log "Domain: https://$FLIPFLOP_DOMAIN"
log "Certificate renews automatically 30 days before expiry"
echo ""
