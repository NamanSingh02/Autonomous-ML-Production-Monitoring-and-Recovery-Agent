"""Formatting service events as JSON without logging sensor payloads."""

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname, "event": record.getMessage(),
        }
        output.update(getattr(record, "fields", {}))
        return json.dumps(output, allow_nan=False)


def service_logger() -> logging.Logger:
    logger = logging.getLogger("ml_service")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
