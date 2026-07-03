import logging
import sys
from typing import Any
import json

# Instance attributes every LogRecord carries (name, msg, args, exc_info, ...).
# These live on the instance, not the class, so comparing against
# logging.LogRecord.__dict__ (the class dict) would keep every single one of
# them as a false "extra" — including exc_info, whose traceback object isn't
# JSON-serializable and crashes json.dumps() the moment anyone logs with
# exc_info=True or uses logger.exception(...).
_RESERVED_RECORD_ATTRS = frozenset(vars(logging.makeLogRecord({})).keys())


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

        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _RESERVED_RECORD_ATTRS and not k.startswith("_")
        }
        log.update(extras)

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler])
