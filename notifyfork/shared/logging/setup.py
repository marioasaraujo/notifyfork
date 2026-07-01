import logging
import sys
from typing import Any
import json


class JSONFormatter(logging.Formatter):
    """
    Structured JSON logs — plays nicely with GCP Cloud Logging,
    Datadog, and any log aggregator that parses JSON.
    """

    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.formatTime(record),
        }

        if hasattr(record, "__dict__"):
            extras = {
                k: v
                for k, v in record.__dict__.items()
                if k not in logging.LogRecord.__dict__ and not k.startswith("_")
            }
            log.update(extras)

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler])
