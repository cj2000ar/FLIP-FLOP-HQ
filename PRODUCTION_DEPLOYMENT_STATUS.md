# FlipFlop HQ Production Deployment Status

## Status: LIVE

**Deployed:** 2026-09-07
**Host:** DigitalOcean droplet `flipflop-hq`
**IP:** 208.68.36.209
**Region:** NYC1
**OS:** Ubuntu 24.04.4 LTS (1 vCPU, 1 GB RAM, 25 GB SSD)

## Live URLs

| Surface | URL | Status |
|---|---|---|
| Dashboard | http://208.68.36.209/ | 200 |
| API health | http://208.68.36.209/api/health | 200 |
| Guardian gates | http://208.68.36.209/api/guardian/gates | 200 (8 gates) |
| Shadow Lab | http://208.68.36.209/api/shadow/strategies | 200 |
| Swagger UI | http://208.68.36.209/api/docs | 200 |
| OpenAPI schema | http://208.68.36.209/api/openapi.json | 200 |

The API binds to loopback only. Port 8000 is not reachable from the
public internet; all access goes through nginx on port 80.

## Authority Invariants (verified live in dashboard header)

- Authority: ZERO
- Live: OFF
- Broker: NONE
- Control: NONE

## Architecture

```
internet :80 -> nginx -> /            static dashboard (/opt/flipflop/dashboard)
                      -> /api/        127.0.0.1:8000 (uvicorn, hp_api.py)
```

- App root: `/opt/flipflop`
- Virtualenv: `/opt/ffvenv` (isolated; Ubuntu 24.04 blocks system-wide
  pip under PEP 668)
- Service: `flipflop-api.service`, systemd, `Restart=always`
- Logs: `/var/log/flipflop-api.log`, `journalctl -u flipflop-api`

## Operations

```bash
systemctl status flipflop-api
systemctl restart flipflop-api
journalctl -u flipflop-api -n 50 --no-pager
```

Redeploy after code changes (from the Windows workstation):

```bash
scp -o PubkeyAuthentication=no app.tar.gz install_vps.sh root@208.68.36.209:/root/
ssh -o PubkeyAuthentication=no root@208.68.36.209 "bash /root/install_vps.sh"
```

## Security

Hardened 2026-09-07. Verified effective config, not just written config:

```
passwordauthentication no
kbdinteractiveauthentication no
permitrootlogin without-password
pubkeyauthentication yes
```

- SSH is key-only. Password auth is refused outright — a password
  attempt now returns `Permission denied (publickey)`.
- ufw active, ingress limited to 22/80/443.
- fail2ban on sshd: 3 retries, 10m window, 24h ban.
- The droplet took sustained root brute-force within hours of creation
  (354 failed password attempts logged; 91.92.40.37, 193.47.62.69).
  That traffic can no longer succeed.

Two gotchas worth remembering for this host:

1. sshd resolves options **first-value-wins**, and DigitalOcean images
   ship both `50-cloud-init.conf` and `60-cloudimg-settings.conf` with
   `PasswordAuthentication yes`. A `99-` drop-in silently loses to them.
   Hardening lives in `00-hardening.conf` so it sorts first.
2. The DigitalOcean agent (DOTTY) rewrites `authorized_keys`. Keys that
   must persist go in `authorized_keys2`, which sshd also reads.

Backups from the hardening run: `/etc/ssh/sshd_config.bak.*` and
`/etc/ssh/sshd_config.d.bak.*`. Rollback if ever locked out (via the
DigitalOcean web console):

```bash
rm /etc/ssh/sshd_config.d/00-hardening.conf && systemctl restart ssh
```

## Not Yet Done

- **TLS.** Dashboard and API are still plain HTTP. Blocked on
  registering a domain; once DNS points at 208.68.36.209, certbot can
  issue and nginx gets a 443 server block plus an 80 redirect.
- PostgreSQL (currently the app's default local storage)
- Prometheus / Grafana / AlertManager on the droplet
- Automated backups
