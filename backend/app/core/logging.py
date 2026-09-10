"""
SIH26117 — Sovereign Local Logging Module
Configures local-only Python logging with request tracking. Zero external telemetry.
"""

import logging
import sys
from typing import Optional


class RequestIdFilter(logging.Filter):
    """Filter that injects request_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root and application loggers."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-8s | [%(request_id)s] | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )

    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers = [console_handler]

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with the request ID filter."""
    logger = logging.getLogger(name)
    logger.addFilter(RequestIdFilter())
    return logger
