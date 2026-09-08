#!/bin/bash
# FlipFlop HQ - VPS hardening, phase 2: disable password authentication.
# Run ONLY after key-based login is confirmed working. It refuses to
# proceed if no key is installed, and keeps a rollback copy of sshd_config.
set -euo pipefail

log() { echo -e "\033[0;32m[HARDEN2]\033[0m $*"; }
abort() { echo -e "\033[0;31m[ABORT]\033[0m $*"; exit 1; }

log "Safety check: keys present?"
KEYS=$(cat /root/.ssh/authorized_keys /root/.ssh/authorized_keys2 2>/dev/null | grep -c "^ssh-\|^ecdsa-" || true)
[ "$KEYS" -ge 1 ] || abort "No SSH keys installed. Disabling passwords would lock you out."
echo "  $KEYS key(s) found"

log "Safety check: has key auth actually succeeded before?"
grep -q "Accepted publickey" /var/log/auth.log 2>/dev/null \
  || abort "No successful key login in auth.log. Log in with your key once, then rerun."
echo "  confirmed in auth.log"

log "Backing up sshd_config"
cp /etc/ssh/sshd_config "/etc/ssh/sshd_config.bak.$(date +%s)"

log "Disabling password authentication"
cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
EOF

sshd -t || abort "sshd config invalid; nothing restarted, system unchanged."
systemctl restart ssh

log "Effective settings"
sshd -T | grep -iE "^passwordauthentication|^permitrootlogin|^pubkeyauthentication" | sed 's/^/  /'

echo ""
echo "Password login is now OFF. Keep this session open and verify a NEW"
echo "key-based login works before closing it."
echo "Rollback if needed (via DigitalOcean web console):"
echo "  rm /etc/ssh/sshd_config.d/99-hardening.conf && systemctl restart ssh"
