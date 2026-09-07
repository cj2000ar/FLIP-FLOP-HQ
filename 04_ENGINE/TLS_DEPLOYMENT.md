# FlipFlop API - TLS/HTTPS Deployment Guide

## Overview

Nginx reverse proxy with TLS termination for production-grade HTTPS security.

**Security Features:**
- TLS 1.2+ only (no SSL 3.0 or TLS 1.0/1.1)
- HSTS (HTTP Strict-Transport-Security) - force HTTPS
- CSP headers, X-Frame-Options, X-Content-Type-Options
- Rate limiting: 100 req/sec general, 10 req/min for token endpoint
- Gzip compression for performance

## Quick Start (Dev/Test)

### 1. Generate Self-Signed Certificate

```bash
bash generate-certs.sh
# Creates: certs/flipflop-api.key, certs/flipflop-api.crt
```

### 2. Start with Docker Compose

```bash
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 3. Test HTTPS Connection

```bash
# With self-signed cert warning suppression
curl -k https://localhost/health
# Returns: {"status":"healthy",...}

# Test API endpoint
curl -k \
  -H "Machine-ID: test-machine" \
  -H "Fencing-Token: <token>" \
  https://localhost/experiments
```

## Production Setup (Let's Encrypt)

### 1. Install Certbot

```bash
sudo apt-get install certbot python3-certbot-nginx
```

### 2. Obtain Certificate

```bash
# Replace flipflop-api.example.com with your domain
sudo certbot certonly --standalone \
  -d flipflop-api.example.com \
  --email admin@example.com \
  --agree-tos

# Certificates stored in: /etc/letsencrypt/live/flipflop-api.example.com/
```

### 3. Update Nginx Config

Edit nginx.conf:
```nginx
ssl_certificate /etc/letsencrypt/live/flipflop-api.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/flipflop-api.example.com/privkey.pem;

# Add auto-renewal
server_name flipflop-api.example.com;
```

### 4. Setup Auto-Renewal

```bash
# Certbot creates renewal timer by default
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Verify renewal works
sudo certbot renew --dry-run
```

### 5. Deploy

```bash
# Copy certificates to Docker volume
sudo cp /etc/letsencrypt/live/flipflop-api.example.com/*.pem certs/

# Start with production config
docker-compose -f docker-compose.prod.yml up -d
```

## Configuration Details

### Nginx Reverse Proxy

**File:** `nginx.conf`

**Key Sections:**

1. **HTTP → HTTPS Redirect**
   - All HTTP traffic redirected to HTTPS
   - Port 80 listener only for redirects

2. **TLS Configuration**
   - TLS 1.2, 1.3 only
   - Strong cipher suites
   - Session caching (10m)
   - HSTS header (1 year)

3. **Security Headers**
   - `X-Content-Type-Options: nosniff` - prevent MIME sniffing
   - `X-Frame-Options: DENY` - prevent clickjacking
   - `X-XSS-Protection` - XSS filter
   - `Referrer-Policy` - control referrer info
   - `Permissions-Policy` - disable unnecessary APIs

4. **Rate Limiting**
   - General API: 100 req/sec per IP (burst 50)
   - Token endpoint: 10 req/min per IP (burst 5)
   - Health check: Unlimited (logged separately)

5. **Performance**
   - Gzip compression for JSON/text
   - HTTP/2 multiplexing
   - Connection pooling to upstream
   - Buffer tuning

### TLS Certificate Details

**Self-Signed (Dev):**
- 2048-bit RSA
- 365-day validity
- Subject: CN=flipflop-api.local

**Let's Encrypt (Prod):**
- Auto-renewal every 60 days
- 90-day certificate lifetime
- Free certificate authority

## Testing & Validation

### SSL/TLS Check

```bash
# Test SSL configuration
openssl s_client -connect localhost:443 -tls1_2

# Check certificate
openssl x509 -in certs/flipflop-api.crt -text -noout

# Verify certificate chain
openssl verify -CAfile certs/flipflop-api.crt certs/flipflop-api.crt
```

### Security Headers

```bash
curl -I https://localhost/health

# Check for headers:
# Strict-Transport-Security
# X-Content-Type-Options
# X-Frame-Options
# X-XSS-Protection
```

### Load Testing (Rate Limiting)

```bash
# Should rate limit after 100 req/sec
for i in {1..150}; do curl -k https://localhost/health; done
```

### API Functionality

```bash
# Issue token
TOKEN=$(curl -k -s -X POST "https://localhost/dev/issue-token?machine_id=test" | jq -r .token)

# Call API
curl -k -H "Machine-ID: test" -H "Fencing-Token: $TOKEN" https://localhost/experiments
```

## Monitoring

### View Access Logs

```bash
docker-compose -f docker-compose.prod.yml logs nginx

# Or from host
tail -f nginx_logs/flipflop_access.log
```

### Check Certificate Expiry

```bash
# Self-signed
openssl x509 -enddate -noout -in certs/flipflop-api.crt

# Let's Encrypt
certbot certificates
```

### Performance Metrics

```bash
# Connection count
docker exec flipflop-nginx netstat -an | grep ESTABLISHED | wc -l

# Request rate
tail -f nginx_logs/flipflop_access.log | wc -l
```

## Troubleshooting

### Certificate Error

```
SSL_ERROR_BAD_CERT_DOMAIN or similar
```

**Solution:**
- Verify certificate CN matches domain name
- For self-signed: Use `-k` flag with curl or accept in browser
- For Let's Encrypt: Verify domain DNS points to server

### Port Already in Use

```
bind: address already in use
```

**Solution:**
```bash
# Check what's using ports 80/443
sudo netstat -tulpn | grep -E ':80|:443'
sudo lsof -i :80 -i :443
```

### API Not Responding Through Nginx

**Check:**
```bash
# Direct API
curl http://private-read-api:8000/health

# Via nginx
curl -k https://localhost/health

# Container connectivity
docker exec flipflop-nginx ping private-read-api
```

## Migration from HTTP to HTTPS

1. **Enable HTTPS** with self-signed or Let's Encrypt
2. **Keep HTTP redirect** (automatic in nginx.conf)
3. **Update client code** to use https:// endpoints
4. **Test thoroughly** before removing HTTP redirect
5. **Monitor logs** for connection issues

## Production Checklist

- [ ] Domain name acquired and DNS configured
- [ ] Let's Encrypt certificate obtained
- [ ] Nginx config updated with domain name
- [ ] Auto-renewal setup verified
- [ ] Firewall rules: ports 80, 443 open
- [ ] Rate limiting tuned for expected traffic
- [ ] HSTS header preload list registration (optional)
- [ ] Certificate pinning considered (optional)
- [ ] WAF/DDoS protection configured (if needed)
- [ ] Monitoring & alerting on certificate expiry

## Next Steps

1. **Centralized Logging:** Export nginx logs to aggregation service
2. **Monitoring:** Set up Prometheus/Grafana for TLS metrics
3. **API Gateway:** Consider Kong or similar for additional API features
