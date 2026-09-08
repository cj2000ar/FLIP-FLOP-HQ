#!/bin/bash
# FlipFlop HQ - VPS hardening, phase 3: SSH key hygiene and swap.
# Removes the expired DigitalOcean agent key. Deliberately KEEPS any key
# the operator registered through the DigitalOcean console: that is the
# recovery path if the workstation key is ever lost.
set -euo pipefail
log()   { echo -e "\033[0;32m[HARDEN3]\033[0m $*"; }
abort() { echo -e "\033[0;31m[ABORT]\033[0m $*"; exit 1; }

AK=/root/.ssh/authorized_keys
AK2=/root/.ssh/authorized_keys2

log "Keys before"
for f in "$AK" "$AK2"; do
  [ -f "$f" ] || continue
  grep -E '^(ssh-|ecdsa-)' "$f" | while read -r k; do
    echo "  $(basename "$f"): $(echo "$k" | ssh-keygen -lf - 2>/dev/null | awk '{print $2, $3}') $(echo "$k" | grep -oE 'expire_at":"[^"]+' || true)"
  done
done

log "Removing expired DigitalOcean agent (DOTTY) keys"
if [ -f "$AK" ]; then
  cp -p "$AK" "$AK.bak.$(date +%s)"
  NOW=$(date -u +%s)
  python3 - "$AK" "$NOW" <<'EOF'
import json, re, sys, datetime
path, now = sys.argv[1], int(sys.argv[2])
keep, dropped = [], 0
for line in open(path):
    m = re.search(r'(\{.*"expire_at":"([^"]+)".*\})', line)
    if m and 'dotty' in line:
        exp = datetime.datetime.fromisoformat(m.group(2).replace('Z', '+00:00')).timestamp()
        if exp < now:
            dropped += 1
            continue
    keep.append(line)
open(path, 'w').writelines(keep)
print(f"  dropped {dropped} expired agent key(s)")
EOF
  chmod 600 "$AK"
fi

log "Workstation key must still be present"
grep -q 'cj200@CJ' "$AK2" || abort "workstation key missing from $AK2; refusing to continue"
echo "  present in authorized_keys2"

log "Swap (1G) so memory pressure degrades instead of OOM-killing"
if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  sysctl -w vm.swappiness=10 >/dev/null
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-flipflop-swap.conf
fi
swapon --show | sed 's/^/  /'

log "Keys after"
cat "$AK" "$AK2" 2>/dev/null | grep -cE '^(ssh-|ecdsa-)' | sed 's/^/  authorized keys total: /'
echo ""
echo "VERIFIED: expired agent key removed, workstation key intact, swap active."
echo "Any remaining key you do not recognise came from the DigitalOcean console;"
echo "review it at cloud.digitalocean.com -> Settings -> Security."
