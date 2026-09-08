"""Health check HTTP server for FlipFlop Scheduler"""

import json
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from health_check import HealthChecker

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health endpoints"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self._handle_health()
        elif self.path == '/health/detail':
            self._handle_health_detail()
        elif self.path == '/metrics':
            self._handle_metrics()
        else:
            self.send_error(404)

    def _handle_health(self):
        """Simple health status"""
        try:
            hc = HealthChecker()
            result = hc.check_all()

            status_code = 200 if result['status'] == 'HEALTHY' else (
                503 if result['status'] == 'UNHEALTHY' else 200
            )

            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {
                'status': result['status'],
                'timestamp': result['timestamp'],
                'authority': result.get('authority', 'ZERO'),
                'live': result.get('live', 'OFF')
            }

            self.wfile.write(json.dumps(response).encode())
            logger.info(f"GET /health -> {result['status']}")

        except Exception as e:
            self.send_error(500, str(e))
            logger.error(f"Health check error: {e}")

    def _handle_health_detail(self):
        """Detailed health status"""
        try:
            hc = HealthChecker()
            result = hc.check_all()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            self.wfile.write(json.dumps(result, indent=2).encode())
            logger.info(f"GET /health/detail -> OK")

        except Exception as e:
            self.send_error(500, str(e))
            logger.error(f"Detailed health check error: {e}")

    def _handle_metrics(self):
        """Prometheus-style metrics"""
        try:
            hc = HealthChecker()
            result = hc.check_all()

            metrics = []
            metrics.append(f"# HELP flipflop_scheduler_status Scheduler health status")
            metrics.append(f"# TYPE flipflop_scheduler_status gauge")
            status_value = 1 if result['status'] == 'HEALTHY' else 0
            metrics.append(f"flipflop_scheduler_status {status_value}")

            for check_name, check_result in result['checks'].items():
                ok = 1 if check_result.get('ok', False) else 0
                metrics.append(f"flipflop_check_{check_name} {ok}")

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()

            self.wfile.write('\n'.join(metrics).encode())
            logger.info(f"GET /metrics -> OK")

        except Exception as e:
            self.send_error(500, str(e))
            logger.error(f"Metrics error: {e}")


class HealthServer:
    """HTTP server for health checks"""

    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start server in background thread"""
        self.server = HTTPServer((self.host, self.port), HealthCheckHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(f"Health server started on {self.host}:{self.port}")

    def stop(self):
        """Stop server"""
        if self.server:
            self.server.shutdown()
            logger.info("Health server stopped")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    server = HealthServer('0.0.0.0', 8080)
    server.start()

    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
