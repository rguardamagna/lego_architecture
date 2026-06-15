"""JSON structured logging with correlation IDs."""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formatea logs como JSON con campos estructurados."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "service"):
            log_entry["service"] = record.service
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }
        return json.dumps(log_entry, default=str)


def setup_logging(service: str = "auth", level: str = "INFO") -> logging.Logger:
    """Configura logger global con formato JSON."""
    logger = logging.getLogger(service)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)

    logger = logging.getLogger(service)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
