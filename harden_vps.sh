#!/bin/bash
# FlipFlop HQ - VPS hardening, phase 1.
# Adds the workstation SSH key, enables a firewall, tightens fail2ban.
# Deliberately does NOT disable password auth yet - that happens in
# phase 2, only after key login is confirmed working.
set -euo pipefail

PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGuIADyrZbfn+o28dIZjv4iM6xLfg+Wm9RDTW6EeIRVq cj200@CJ"
log() { echo -e "\033[0;32m[HARDEN]\033[0m $*"; }

log "Installing workstation key"
mkdir -p /root/.ssh
chmod 700 /root/.ssh
# authorized_keys is rewritten by the DigitalOcean agent, so keep ours
# in authorized_keys2, which sshd also reads and the agent ignores.
grep -qF "$PUBKEY" /root/.ssh/authorized_keys2 2>/dev/null || echo "$PUBKEY" >> /root/.ssh/authorized_keys2
chmod 600 /root/.ssh/authorized_keys2
echo "  keys present: $(wc -l < /root/.ssh/authorized_keys2)"

log "Configuring firewall (SSH, HTTP, HTTPS only)"
apt-get install -y -qq ufw >/dev/null
ufw allow 22/tcp   >/dev/null
ufw allow 80/tcp   >/dev/null
ufw allow 443/tcp  >/dev/null
ufw --force enable >/dev/null
ufw status numbered | sed 's/^/  /'

log "Tightening fail2ban on sshd"
cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled  = true
port     = ssh
backend  = systemd
maxretry = 3
findtime = 10m
bantime  = 24h
EOF
systemctl restart fail2ban
sleep 2
fail2ban-client status sshd 2>/dev/null | sed 's/^/  /' || echo "  (jail warming up)"

log "Current attacker traffic"
grep -c "Failed password" /var/log/auth.log 2>/dev/null | sed 's/^/  failed password attempts in log: /' || true

echo ""
echo "Phase 1 done. Password login is STILL ENABLED on purpose."
echo "Next: confirm key login works, then run harden_phase2.sh."
