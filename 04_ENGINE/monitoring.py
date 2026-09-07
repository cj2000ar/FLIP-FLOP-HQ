"""
Prometheus Monitoring for FlipFlop API

Metrics:
- Request count (endpoint, method, status)
- Request latency (p50, p95, p99)
- Token validation failures
- Database query latency
- Health check status
"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server
from contextlib import contextmanager
import time
import logging

logger = logging.getLogger(__name__)

# Request metrics
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request latency',
    ['endpoint', 'method'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Auth metrics
token_validation_failures = Counter(
    'token_validation_failures_total',
    'Token validation failures',
    ['reason']  # expired, invalid, missing
)

token_validation_duration = Histogram(
    'token_validation_duration_seconds',
    'Token validation latency',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05)
)

# Database metrics
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query latency',
    ['endpoint', 'operation'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Health metrics
health_check_status = Gauge(
    'api_health_status',
    'API health status (1=healthy, 0=unhealthy)'
)

# Token store metrics
active_tokens = Gauge(
    'active_tokens',
    'Active valid tokens in store'
)


@contextmanager
def track_request(endpoint: str, method: str):
    """Context manager for tracking request metrics"""
    start_time = time.time()
    status = 500
    try:
        yield lambda s: globals().__setitem__('status', s)
    finally:
        duration = time.time() - start_time
        request_duration.labels(endpoint=endpoint, method=method).observe(duration)
        request_count.labels(endpoint=endpoint, method=method, status=status).inc()


@contextmanager
def track_token_validation():
    """Context manager for tracking token validation"""
    start_time = time.time()
    try:
        yield
    except Exception as e:
        duration = time.time() - start_time
        token_validation_duration.observe(duration)

        reason = 'invalid'
        if 'expired' in str(e).lower():
            reason = 'expired'
        elif 'missing' in str(e).lower():
            reason = 'missing'

        token_validation_failures.labels(reason=reason).inc()
        raise
    else:
        duration = time.time() - start_time
        token_validation_duration.observe(duration)


@contextmanager
def track_db_query(endpoint: str, operation: str = 'fetch'):
    """Context manager for tracking database queries"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        db_query_duration.labels(endpoint=endpoint, operation=operation).observe(duration)


def update_token_store_size(count: int):
    """Update active token count"""
    active_tokens.set(count)


def set_health_status(is_healthy: bool):
    """Update health status"""
    health_check_status.set(1 if is_healthy else 0)


def start_metrics_server(port: int = 8001):
    """Start Prometheus metrics HTTP server"""
    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
        logger.info(f"Access metrics at http://localhost:{port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


# Prometheus scrape config (add to prometheus.yml):
PROMETHEUS_SCRAPE_CONFIG = """
  - job_name: 'flipflop-api'
    static_configs:
      - targets: ['localhost:8001']
    scrape_interval: 30s
    scrape_timeout: 10s
"""

# Grafana dashboard JSON (use in Grafana UI):
GRAFANA_DASHBOARD = {
    "dashboard": {
        "title": "FlipFlop API Metrics",
        "panels": [
            {
                "title": "Request Rate (req/sec)",
                "targets": [
                    {"expr": "rate(api_requests_total[1m])"}
                ]
            },
            {
                "title": "Request Latency p95",
                "targets": [
                    {"expr": "histogram_quantile(0.95, api_request_duration_seconds)"}
                ]
            },
            {
                "title": "Token Validation Failures",
                "targets": [
                    {"expr": "rate(token_validation_failures_total[5m])"}
                ]
            },
            {
                "title": "Active Tokens",
                "targets": [
                    {"expr": "active_tokens"}
                ]
            },
            {
                "title": "Database Query Latency p99",
                "targets": [
                    {"expr": "histogram_quantile(0.99, db_query_duration_seconds)"}
                ]
            },
            {
                "title": "API Health Status",
                "targets": [
                    {"expr": "api_health_status"}
                ]
            }
        ]
    }
}
