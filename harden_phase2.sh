#!/bin/bash
# FlipFlop HQ - VPS hardening, phase 2: disable password authentication.
# Run ONLY after key-based login is confirmed working.
#
# sshd uses FIRST-value-wins. Ubuntu's sshd_config includes
# /etc/ssh/sshd_config.d/*.conf near the top, and DigitalOcean ships
# 50-cloud-init.conf with "PasswordAuthentication yes" - which beats any
# higher-numbered drop-in. So this writes 00-hardening.conf (sorts first)
# and also neutralises competing directives, then verifies the effective
# config rather than assuming the write took.
set -euo pipefail

log()   { echo -e "\033[0;32m[HARDEN2]\033[0m $*"; }
abort() { echo -e "\033[0;31m[ABORT]\033[0m $*"; exit 1; }

log "Safety check: keys present?"
KEYS=$(cat /root/.ssh/authorized_keys /root/.ssh/authorized_keys2 2>/dev/null | grep -c "^ssh-\|^ecdsa-" || true)
[ "$KEYS" -ge 1 ] || abort "No SSH keys installed. Disabling passwords would lock you out."
echo "  $KEYS key(s) found"

log "Safety check: has key auth actually succeeded?"
grep -q "Accepted publickey" /var/log/auth.log 2>/dev/null \
  || abort "No successful key login in auth.log. Log in with your key once, then rerun."
echo "  confirmed in auth.log"

log "Existing drop-ins"
ls -1 /etc/ssh/sshd_config.d/ 2>/dev/null | sed 's/^/  /' || echo "  (none)"

log "Backing up config"
STAMP=$(date +%s)
cp /etc/ssh/sshd_config "/etc/ssh/sshd_config.bak.$STAMP"
[ -d /etc/ssh/sshd_config.d ] && cp -r /etc/ssh/sshd_config.d "/etc/ssh/sshd_config.d.bak.$STAMP"

log "Neutralising competing PasswordAuthentication directives"
for f in /etc/ssh/sshd_config.d/*.conf; do
  [ -e "$f" ] || continue
  case "$f" in */00-hardening.conf) continue ;; esac
  if grep -qiE "^[[:space:]]*(PasswordAuthentication|PermitRootLogin)" "$f"; then
    sed -i -E 's/^[[:space:]]*(PasswordAuthentication|PermitRootLogin)/#&/I' "$f"
    echo "  commented out in $(basename "$f")"
  fi
done
sed -i -E 's/^[[:space:]]*PasswordAuthentication[[:space:]]+yes/#&/I' /etc/ssh/sshd_config

log "Writing 00-hardening.conf (sorts first, wins precedence)"
cat > /etc/ssh/sshd_config.d/00-hardening.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
KbdInteractiveAuthentication no
PubkeyAuthentication yes
EOF
rm -f /etc/ssh/sshd_config.d/99-hardening.conf

sshd -t || abort "sshd config invalid; nothing restarted, system unchanged."
systemctl restart ssh

log "Effective settings (authoritative)"
sshd -T | grep -iE "^passwordauthentication|^permitrootlogin|^pubkeyauthentication|^kbdinteractive" | sed 's/^/  /'

PW=$(sshd -T | grep -i "^passwordauthentication" | awk '{print $2}')
KB=$(sshd -T | grep -i "^kbdinteractiveauthentication" | awk '{print $2}')
if [ "$PW" = "no" ] && [ "$KB" = "no" ]; then
  echo ""
  echo "VERIFIED: password authentication is OFF."
  echo "Keep this session open. Confirm a NEW key login in a second window."
else
  echo ""
  abort "Password auth is STILL '$PW' (kbdinteractive '$KB'). Config did not take. Nothing to trust here - investigate before closing your session."
fi

echo "Rollback (via DigitalOcean web console if locked out):"
echo "  rm /etc/ssh/sshd_config.d/00-hardening.conf && systemctl restart ssh"
