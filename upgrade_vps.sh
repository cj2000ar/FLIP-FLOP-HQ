#!/bin/bash
# FlipFlop HQ - apply all pending OS updates including kernel, then reboot.
# The reboot doubles as the first real test that services come back on
# their own. Run as root. The caller should poll /api/health afterwards.
set -euo pipefail
log() { echo -e "\033[0;32m[UPGRADE]\033[0m $*"; }

export DEBIAN_FRONTEND=noninteractive
log "Pending before"
apt list --upgradable 2>/dev/null | grep -c upgradable | sed 's/^/  packages: /'

log "Full upgrade (dist-upgrade pulls the held-back kernel)"
apt-get update -qq
apt-get -y -qq -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" dist-upgrade >/dev/null
apt-get -y -qq autoremove >/dev/null

log "Pending after"
apt list --upgradable 2>/dev/null | grep -c upgradable | sed 's/^/  packages: /'
dpkg -l 'linux-image-*' | awk '/^ii/ {print "  installed kernel: " $2}' | tail -n 2
echo "  running kernel:   $(uname -r)"

log "Make unattended-upgrades actually run, and reboot for kernels on its own"
cat > /etc/apt/apt.conf.d/52flipflop-unattended <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:30";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF
systemctl enable --now unattended-upgrades apt-daily.timer apt-daily-upgrade.timer >/dev/null 2>&1
systemctl list-timers apt-daily-upgrade.timer --no-pager | sed -n '2p' | sed 's/^/  next unattended run: /'

if [ -f /var/run/reboot-required ]; then
  log "Kernel changed; rebooting in 5s. Services are enabled and should return on their own."
  sleep 5
  systemctl reboot
else
  log "No reboot required."
fi
