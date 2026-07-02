"""Structured JSON logging with request IDs (lab 06).

One JSON object per line on stdout — the same convention as the main Go API's
`internal/telemetry`, so the Loki pipeline from lab 11 parses both services
without extra configuration. The request ID rides a ContextVar set by the HTTP
middleware in main.py, so any log line emitted while handling a request carries
it automatically.
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar

from .config import cfg

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        rid = request_id_var.get()
        if rid:
            entry["request_id"] = rid
        fields = getattr(record, "fields", None)
        if fields:
            entry.update(fields)
        return json.dumps(entry)


def _setup() -> logging.Logger:
    logger = logging.getLogger("dojo_ai")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(cfg.LOG_LEVEL.upper())
        logger.propagate = False
    return logger


_log = _setup()


def info(msg: str, **fields) -> None:
    _log.info(msg, extra={"fields": fields})


def error(msg: str, **fields) -> None:
    _log.error(msg, extra={"fields": fields})
