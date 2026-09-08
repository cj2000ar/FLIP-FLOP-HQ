#!/bin/bash
# FlipFlop HQ - issue a Let's Encrypt certificate and switch nginx to HTTPS.
# Usage (on the droplet, as root):  bash tls_vps.sh <domain> <email>
# Run scripts/domain_wizard.sh on the workstation first; it produces both
# values and records the operator's agreement to the Let's Encrypt terms.
set -euo pipefail

DOMAIN="${1:?usage: tls_vps.sh <domain> <email>}"
EMAIL="${2:?usage: tls_vps.sh <domain> <email>}"
DROPLET_IP="$(curl -4 -s --max-time 5 https://api.ipify.org || hostname -I | awk '{print $1}')"
SITE=/etc/nginx/sites-available/flipflop

log()   { echo -e "\033[0;32m[TLS]\033[0m $*"; }
abort() { echo -e "\033[0;31m[ABORT]\033[0m $*"; exit 1; }

log "Preflight: $DOMAIN must resolve to this host ($DROPLET_IP)"
RESOLVED="$(dig +short "$DOMAIN" A 2>/dev/null | tail -n1 || true)"
[ -n "$RESOLVED" ] || abort "$DOMAIN does not resolve. Fix DNS first."
[ "$RESOLVED" = "$DROPLET_IP" ] || abort "$DOMAIN resolves to $RESOLVED, not $DROPLET_IP. Let's Encrypt validation would fail."
echo "  resolves correctly"

log "Preflight: port 80 open to the internet for ACME validation"
ufw status | grep -qE "^80/tcp\s+ALLOW" || abort "ufw is not allowing 80/tcp; certbot's HTTP challenge needs it."
ufw status | grep -qE "^443/tcp\s+ALLOW" || abort "ufw is not allowing 443/tcp."
echo "  ufw allows 80 and 443"

log "Installing certbot"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq certbot python3-certbot-nginx dnsutils >/dev/null

log "Setting nginx server_name to $DOMAIN"
[ -f "$SITE" ] || abort "$SITE missing; run install_vps.sh first."
cp "$SITE" "$SITE.bak.$(date +%s)"
sed -i -E "s/^(\s*server_name)\s+.*;/\1 $DOMAIN www.$DOMAIN;/" "$SITE"
nginx -t
systemctl reload nginx

log "Issuing certificate (also covers www.$DOMAIN if it resolves)"
DOMAINS=(-d "$DOMAIN")
if [ "$(dig +short "www.$DOMAIN" A 2>/dev/null | tail -n1 || true)" = "$DROPLET_IP" ]; then
  DOMAINS+=(-d "www.$DOMAIN")
else
  echo "  www.$DOMAIN not pointed at this host; issuing for apex only"
  sed -i -E "s/^(\s*server_name)\s+.*;/\1 $DOMAIN;/" "$SITE"
  nginx -t && systemctl reload nginx
fi
certbot --nginx "${DOMAINS[@]}" \
  --non-interactive --agree-tos --email "$EMAIL" \
  --redirect --hsts --no-eff-email

log "Hardening TLS settings"
# certbot writes a sane modern config; add OCSP stapling if not present.
if ! grep -q "ssl_stapling on" "$SITE"; then
  sed -i "/ssl_certificate_key/a\    ssl_stapling on;\n    ssl_stapling_verify on;" "$SITE"
  nginx -t && systemctl reload nginx
fi

log "Verifying"
HTTPS_CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$DOMAIN/" || echo 000)"
HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://$DOMAIN/" || echo 000)"
API_CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$DOMAIN/api/health" || echo 000)"
echo "  https://$DOMAIN/            -> $HTTP_CODE"    | sed "s/-> $HTTP_CODE/-> $HTTPS_CODE/"
echo "  http://$DOMAIN/  (redirect) -> $HTTP_CODE"
echo "  https://$DOMAIN/api/health  -> $API_CODE"
[ "$HTTPS_CODE" = "200" ] || abort "HTTPS dashboard returned $HTTPS_CODE"
[ "$HTTP_CODE" = "301" ]  || abort "HTTP did not redirect (got $HTTP_CODE)"
[ "$API_CODE" = "200" ]   || abort "HTTPS API returned $API_CODE"

log "Auto-renewal"
systemctl list-timers certbot.timer --no-pager | sed -n '2p' | sed 's/^/  /'
certbot renew --dry-run --quiet && echo "  dry-run renewal OK" || abort "renewal dry-run failed"

log "Certificate"
certbot certificates 2>/dev/null | grep -E "Domains|Expiry" | sed 's/^/  /'

echo ""
echo "VERIFIED: https://$DOMAIN/ is live, HTTP redirects, renewal timer armed."
