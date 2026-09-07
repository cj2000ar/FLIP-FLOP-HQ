#!/bin/bash
# FlipFlop HQ Deployment Script - VPS/On-Prem Production Deployment

set -e

echo "=========================================="
echo "FlipFlop HQ - Production Deployment"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_USER=${DEPLOY_USER:-flipflop}
DEPLOY_GROUP=${DEPLOY_GROUP:-flipflop}
APP_HOME=/opt/flipflop
DB_NAME=flipflop_hq
DB_USER=${DB_USER:-flipflop}
API_PORT=8000
API_HOST=0.0.0.0

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Step 1: System Dependencies
log_info "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3.12 \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    curl \
    wget \
    git \
    supervisor \
    prometheus-node-exporter \
    || log_error "Failed to install system dependencies"

# Step 2: Create Application User
log_info "Creating application user..."
if ! id "$DEPLOY_USER" &>/dev/null; then
    sudo useradd -m -s /bin/bash "$DEPLOY_USER"
    log_info "User $DEPLOY_USER created"
else
    log_warn "User $DEPLOY_USER already exists"
fi

# Step 3: Create Application Directory
log_info "Creating application directory..."
sudo mkdir -p "$APP_HOME"
sudo chown -R "$DEPLOY_USER:$DEPLOY_GROUP" "$APP_HOME"

# Step 4: Clone/Update Repository
log_info "Setting up application code..."
cd "$APP_HOME"
if [ -d .git ]; then
    sudo -u "$DEPLOY_USER" git pull origin master
else
    sudo -u "$DEPLOY_USER" git clone https://github.com/flipflop-hq/flipflop-hq.git .
fi

# Step 5: Setup Python Environment
log_info "Setting up Python environment..."
cd "$APP_HOME/04_ENGINE"
sudo -u "$DEPLOY_USER" python3.12 -m venv venv
sudo -u "$DEPLOY_USER" ./venv/bin/pip install --upgrade pip
sudo -u "$DEPLOY_USER" ./venv/bin/pip install -r requirements.txt

# Step 6: Database Setup
log_info "Setting up PostgreSQL database..."
sudo -u postgres psql <<EOF
CREATE DATABASE IF NOT EXISTS $DB_NAME;
CREATE USER IF NOT EXISTS $DB_USER WITH PASSWORD '${DB_PASSWORD:-change_me}';
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET default_transaction_deferrable TO on;
ALTER ROLE $DB_USER SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

# Step 7: Database Migration
log_info "Running database migrations..."
cd "$APP_HOME/04_ENGINE"
sudo -u "$DEPLOY_USER" ./venv/bin/python -c "
from hp_infra import HPInfrastructure
hp = HPInfrastructure(db_path='postgresql://$DB_USER:${DB_PASSWORD:-change_me}@localhost:5432/$DB_NAME')
print('Database initialized')
"

# Step 8: Supervisor Configuration
log_info "Configuring supervisor for API service..."
sudo tee /etc/supervisor/conf.d/flipflop-api.conf > /dev/null <<EOF
[program:flipflop-api]
directory=$APP_HOME/04_ENGINE
command=$APP_HOME/04_ENGINE/venv/bin/python hp_api.py
user=$DEPLOY_USER
environment=API_PORT=$API_PORT,API_HOST=$API_HOST,DATABASE_URL=postgresql://$DB_USER:${DB_PASSWORD:-change_me}@localhost:5432/$DB_NAME,AUTHORITY=ZERO,LIVE_ENABLED=false,BROKER_ORDERS_ALLOWED=false
stdout_logfile=/var/log/flipflop/api.log
stderr_logfile=/var/log/flipflop/api_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=10
EOF

# Step 9: Nginx Configuration
log_info "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/flipflop-api > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/flipflop-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Step 10: Log Directories
log_info "Creating log directories..."
sudo mkdir -p /var/log/flipflop
sudo chown -R "$DEPLOY_USER:$DEPLOY_GROUP" /var/log/flipflop

# Step 11: Start Services
log_info "Starting services..."
sudo systemctl restart supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start flipflop-api

# Step 12: Verify Deployment
log_info "Verifying deployment..."
sleep 5

if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    log_info "API is responding"
else
    log_error "API is not responding"
fi

if curl -f http://localhost:8000/guardian/gates >/dev/null 2>&1; then
    log_info "Guardian endpoints are available"
else
    log_error "Guardian endpoints are not available"
fi

# Step 13: Build Dashboard
log_info "Building dashboard..."
cd "$APP_HOME/07_DASHBOARD"
sudo -u "$DEPLOY_USER" npm install
sudo -u "$DEPLOY_USER" npm run build

sudo mkdir -p /var/www/flipflop
sudo cp -r dist/* /var/www/flipflop/

# Step 14: Setup Monitoring
log_info "Configuring Prometheus monitoring..."
sudo mkdir -p /etc/prometheus
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'flipflop-api'
    static_configs:
      - targets: ['localhost:8000']
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
EOF

# Step 15: Setup Backup
log_info "Configuring automated backups..."
sudo tee /usr/local/bin/flipflop-backup.sh > /dev/null <<'EOF'
#!/bin/bash
BACKUP_DIR=/var/backups/flipflop
mkdir -p $BACKUP_DIR
pg_dump -U flipflop flipflop_hq | gzip > $BACKUP_DIR/flipflop_$(date +%Y%m%d_%H%M%S).sql.gz
find $BACKUP_DIR -mtime +7 -delete
EOF

sudo chmod +x /usr/local/bin/flipflop-backup.sh
(echo "0 3 * * * root /usr/local/bin/flipflop-backup.sh") | sudo tee /etc/cron.d/flipflop-backup

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "API URL: http://localhost:8000"
echo "Health: http://localhost:8000/health"
echo "Guardian: http://localhost:8000/guardian/gates"
echo "Shadow Lab: http://localhost:8000/shadow/strategies"
echo ""
echo "Logs:"
echo "  API: /var/log/flipflop/api.log"
echo "  Nginx: /var/log/nginx/access.log"
echo ""
echo "Configuration:"
echo "  App Home: $APP_HOME"
echo "  Database: $DB_NAME"
echo "  Authority: ZERO (locked)"
echo "  Live Orders: OFF"
echo ""
echo "Next Steps:"
echo "  1. Configure TLS certificates"
echo "  2. Setup monitoring dashboards"
echo "  3. Configure email alerts"
echo "  4. Run integration tests"
echo ""
