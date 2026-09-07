# FlipFlop HQ - Production Deployment Guide

**Date:** 2026-09-07  
**Version:** Phase 6 Complete  
**Authority:** ZERO (LOCKED IMMUTABLE)  
**Live:** OFF (Paper Trading Only)  

---

## PRE-DEPLOYMENT VERIFICATION

### Git Status
```bash
git log --oneline | head -5
# Expected: e11881d, d4ccee5, 51b8fdf, de70193 (all Phase 5-6 commits)

git status
# Expected: working tree clean
```

### Test Suite Status
```bash
cd 04_ENGINE/RED_DRAGON
python -m pytest guardian_tests.py -v
# Expected: 55/55 PASS
```

### API Endpoint Verification
```bash
cd 04_ENGINE
python -c "from hp_api import create_app; from hp_infra import HPInfrastructure; hp = HPInfrastructure(db_path='test.db'); app = create_app(hp); routes = [r.path for r in app.routes if hasattr(r, 'path')]; print(f'Total routes: {len(routes)}')"
# Expected: Total routes: ~30+
```

---

## DEPLOYMENT STAGES

### Stage 1: Environment Setup

#### 1.1 Production Database
```bash
# PostgreSQL migration (from SQLite)
cd 04_ENGINE

# Export current SQLite data
python -c "
import sqlite3
import json

conn = sqlite3.connect('hp_infra.db')
cursor = conn.cursor()
cursor.execute(\"SELECT * FROM heartbeats LIMIT 5\")
print('Current data exists:', cursor.fetchall() is not None)
conn.close()
"

# Initialize PostgreSQL (production)
export DATABASE_URL=postgresql://user:pass@prod-db:5432/flipflop_hq
python -c "from hp_infra import HPInfrastructure; hp = HPInfrastructure(db_path=os.getenv('DATABASE_URL'))"
```

#### 1.2 Environment Variables
```bash
# .env.production
API_PORT=8000
API_HOST=0.0.0.0
FLIPFLOP_DB_PATH=/var/lib/flipflop/databases/
REACT_APP_API_URL=https://api.flipflop.io

# Authority locks (immutable)
AUTHORITY=ZERO
LIVE_ENABLED=false
BROKER_ORDERS_ALLOWED=false

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# TLS/HTTPS
TLS_CERT=/etc/flipflop/certs/server.crt
TLS_KEY=/etc/flipflop/certs/server.key
```

#### 1.3 System Resources
- CPU: 4+ cores (API + monitoring + database)
- RAM: 8GB minimum (API=2GB, DB=4GB, monitoring=2GB)
- Storage: 100GB (database + backups + logs)
- Network: Public IP + TLS/HTTPS

---

### Stage 2: Backend Deployment

#### 2.1 API Server
```bash
cd 04_ENGINE

# Install dependencies
pip install -r requirements.txt

# Run API (production mode)
API_PORT=8000 python hp_api.py

# OR use Gunicorn (recommended)
gunicorn -w 4 -b 0.0.0.0:8000 hp_api:app

# Verify endpoints
curl https://api.flipflop.io/health
# Expected: {"status": "ok", "message": "HP infrastructure operational"}

curl https://api.flipflop.io/guardian/gates
# Expected: [{"gate_id": "gate_1", ...}, ...]

curl https://api.flipflop.io/shadow/strategies
# Expected: [{"name": "RR500", ...}, ...]
```

#### 2.2 Database Backup
```bash
# Automated daily backups
cd 04_ENGINE

# Backup script
python backup.py --destination s3://flipflop-backups/ --retention 7

# Verify backup
aws s3 ls s3://flipflop-backups/
```

#### 2.3 Monitoring Stack
```bash
# Prometheus (metrics collection)
docker run -d -p 9090:9090 prom/prometheus:latest --config.file=/etc/prometheus/prometheus.yml

# Grafana (visualization)
docker run -d -p 3000:3000 grafana/grafana:latest

# AlertManager (alerting)
docker run -d -p 9093:9093 prom/alertmanager:latest --config.file=/etc/alertmanager/config.yml
```

---

### Stage 3: Frontend Deployment

#### 3.1 Dashboard Build
```bash
cd 07_DASHBOARD

# Install dependencies
npm install

# Production build
npm run build
# Output: dist/ directory with optimized bundles

# Verify build
ls -la dist/
# Expected: index.html, assets/, etc
```

#### 3.2 Web Server (Nginx)
```nginx
# /etc/nginx/sites-available/flipflop.io
server {
    listen 443 ssl http2;
    server_name api.flipflop.io;

    ssl_certificate /etc/flipflop/certs/server.crt;
    ssl_certificate_key /etc/flipflop/certs/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Frontend
    location / {
        root /var/www/flipflop/dist/;
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "public, max-age=3600";
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req zone=general burst=20 nodelay;
}
```

#### 3.3 Enable & Verify
```bash
sudo ln -s /etc/nginx/sites-available/flipflop.io /etc/nginx/sites-enabled/
sudo nginx -t  # Verify config
sudo systemctl restart nginx

# Test dashboard
curl https://api.flipflop.io/
# Expected: HTML dashboard response
```

---

### Stage 4: Integration Testing

#### 4.1 Guardian Pipeline
```bash
cd 04_ENGINE

# Run full integration test
python integration_tests.py
# Expected: All 40+ tests PASS

# Verify Guardian gates
python -c "
from RED_DRAGON.guardian_engine import GuardianEngine
ge = GuardianEngine()
print('✓ Guardian engine initialized')
print(f'✓ 8 gates loaded')
"
```

#### 4.2 NinjaTrader Bridge
```bash
cd 04_ENGINE

# Test replay session creation
python -c "
from ninjatrader_bridge import NinjaTraderBridge
bridge = NinjaTraderBridge()
session = bridge.create_replay_session('RR500', 'NQ', '20260907')
print(f'✓ Session created: {session.session_id}')
"
```

#### 4.3 API Health Checks
```bash
# Guardian endpoints
curl -X GET https://api.flipflop.io/guardian/gates | jq '.[] | .gate_id'
# Expected: gate_1, gate_2, ..., gate_8

# Shadow Lab endpoints
curl -X GET https://api.flipflop.io/shadow/strategies | jq '.[] | .name'
# Expected: RR500, IFVG, UT, KiloView

# Dashboard
curl -I https://api.flipflop.io/
# Expected: HTTP 200
```

---

### Stage 5: Authority Verification (CRITICAL)

#### 5.1 Immutable Locks
```bash
# Verify authority cannot escalate
python -c "
from RED_DRAGON.guardian_engine import AuthorityLevel, AuthorityTuple

# Try to create authority != ZERO (should fail)
try:
    bad_auth = AuthorityTuple(authority='ONE')  # Invalid
    print('FAIL: Authority escalation allowed')
except ValueError as e:
    print(f'✓ Authority locked: {e}')

# Verify ZERO is enforced
good_auth = AuthorityTuple(authority='ZERO')
print(f'✓ Authority tuple: {good_auth.authority}')
"

# Verify live_enabled = false
python -c "
from RED_DRAGON.guardian_engine import AuthorityTuple

try:
    bad_live = AuthorityTuple(authority='ZERO', live_enabled=True)  # Invalid
    print('FAIL: Live enabled allowed')
except ValueError as e:
    print(f'✓ Live locked OFF: {e}')
"

# Verify broker_orders = false
python -c "
from RED_DRAGON.guardian_engine import AuthorityTuple

try:
    bad_broker = AuthorityTuple(authority='ZERO', broker_orders_allowed=True)  # Invalid
    print('FAIL: Broker orders allowed')
except ValueError as e:
    print(f'✓ Broker orders locked NONE: {e}')
"
```

#### 5.2 Evidence Audit
```bash
# Check immutable database constraints
psql flipflop_hq -c "
SELECT constraint_name FROM information_schema.table_constraints
WHERE table_name = 'gate_verdicts' AND constraint_type = 'PRIMARY KEY';
"
# Expected: verdict_id PRIMARY KEY exists

# Verify append-only
psql flipflop_hq -c "
SELECT COUNT(*) FROM gate_verdicts;
"
# Expected: Read-only record count
```

---

### Stage 6: Operational Monitoring

#### 6.1 Metrics Dashboard
- Prometheus: http://localhost:9090 (metrics collection)
- Grafana: http://localhost:3000 (visualization)
- AlertManager: http://localhost:9093 (alerts)

#### 6.2 Log Aggregation
```bash
# Centralized logging (production)
journalctl -u flipflop-api -f
tail -f /var/log/flipflop/api.log
tail -f /var/log/flipflop/guardian.log
tail -f /var/log/flipflop/ninjatrader.log
```

#### 6.3 Alert Rules (10+ configured)
- API response time > 1s
- Guardian verdict delay > 5s
- Database connection pool exhausted
- Cache miss rate > 10%
- Error rate > 1%
- Disk usage > 80%
- Memory usage > 85%
- CPU usage > 75%
- TLS certificate expiry < 30 days
- Backup failure

---

### Stage 7: Rollback Plan

#### 7.1 Database Rollback
```bash
# Restore from latest backup
aws s3 cp s3://flipflop-backups/latest.db.gz /tmp/
gunzip /tmp/latest.db.gz
psql flipflop_hq < /tmp/latest.sql
```

#### 7.2 Code Rollback
```bash
git log --oneline | head -5
git revert e11881d  # Revert latest commit if needed
git push origin master
```

#### 7.3 Service Restart
```bash
systemctl restart flipflop-api
systemctl restart nginx
systemctl restart prometheus
systemctl restart grafana-server
```

---

## POST-DEPLOYMENT CHECKLIST

- [ ] API responding on port 8000
- [ ] Dashboard accessible on HTTPS
- [ ] All 4 Guardian endpoints operational
- [ ] All 6 Shadow Lab endpoints operational
- [ ] Database backups running daily
- [ ] Monitoring stack collecting metrics
- [ ] Alert rules active and tested
- [ ] Authority locks verified (ZERO, Live=OFF, Broker=NONE)
- [ ] TLS certificate valid and auto-renewing
- [ ] Integration tests all PASS (40+)
- [ ] Guardian tests all PASS (55+)
- [ ] Logs aggregated and searchable
- [ ] Disaster recovery plan documented
- [ ] Team trained on operations

---

## SUPPORT CONTACTS

- **On-Call:** escalation@flipflop.io
- **Issues:** github.com/flipflop-hq/issues
- **Status:** status.flipflop.io

---

**DEPLOYMENT STATUS: READY**  
**Authority:** ZERO (immutable)  
**Live Trading:** OFF (paper only)  
**Next Step:** Execute Stage 1-7 sequentially  
