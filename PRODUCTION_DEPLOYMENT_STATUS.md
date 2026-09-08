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

- fail2ban installed and enabled. The droplet was taking sustained SSH
  brute-force traffic against root (observed from 91.92.40.37) within
  hours of creation.
- Root login over password is still enabled. Recommended next: add an
  SSH key, then set `PermitRootLogin prohibit-password` and
  `PasswordAuthentication no`.
- No TLS yet. The dashboard and API are served over plain HTTP.

## Not Yet Done

- TLS certificate (Let's Encrypt / certbot) and a domain name
- PostgreSQL (currently the app's default local storage)
- Prometheus / Grafana / AlertManager on the droplet
- Automated backups
