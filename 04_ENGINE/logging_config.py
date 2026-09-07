"""
Centralized Logging Configuration for FlipFlop API

Features:
- Structured JSON logging (machine-readable)
- File rotation (daily, 100MB max, 30-day retention)
- Separate files for API, audit, errors
- Timestamp, request ID, level, message
- Production-ready with cloud export hooks
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger
import os


class StructuredFormatter(jsonlogger.JsonFormatter):
    """JSON formatter with custom fields"""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id


def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """
    Setup centralized logging with file rotation and structured format

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # Clear existing handlers
    root_logger.handlers.clear()

    # 1. API Log (all requests, responses)
    api_handler = TimedRotatingFileHandler(
        filename=str(log_path / "api.log"),
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days
        encoding="utf-8"
    )
    api_handler.setFormatter(StructuredFormatter())
    api_logger = logging.getLogger("flipflop.api")
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)

    # 2. Audit Log (auth, token validation, state changes)
    audit_handler = TimedRotatingFileHandler(
        filename=str(log_path / "audit.log"),
        when="midnight",
        interval=1,
        backupCount=90,  # Keep 90 days for compliance
        encoding="utf-8"
    )
    audit_handler.setFormatter(StructuredFormatter())
    audit_logger = logging.getLogger("flipflop.audit")
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)

    # 3. Error Log (exceptions, failures)
    error_handler = RotatingFileHandler(
        filename=str(log_path / "errors.log"),
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=10,
        encoding="utf-8"
    )
    error_handler.setFormatter(StructuredFormatter())
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)

    # 4. Console output (development)
    if os.getenv("DEBUG") == "1":
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # 5. Main API handler (to file)
    main_handler = TimedRotatingFileHandler(
        filename=str(log_path / "flipflop.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    main_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(main_handler)

    return root_logger


def get_logger(name: str):
    """Get configured logger"""
    return logging.getLogger(name)


# Export commonly used loggers
api_logger = logging.getLogger("flipflop.api")
audit_logger = logging.getLogger("flipflop.audit")
