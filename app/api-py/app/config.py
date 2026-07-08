"""Runtime configuration from environment variables — a 1:1 port of the Go
app's internal/config/config.go. Same variable names and defaults, so a single
.env (and the same Compose/K8s wiring) drives either implementation. That shared
contract is the whole point of the twin: only the language changes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    port: str
    database_url: str
    redis_url: str
    otlp_endpoint: str  # host:port for OTLP/HTTP; empty disables tracing
    service_name: str


def _getenv(key: str, default: str) -> str:
    v = os.getenv(key)
    return v if v else default


def load() -> Config:
    return Config(
        port=_getenv("PORT", "8080"),
        database_url=_getenv(
            "DATABASE_URL", "postgres://dojo:dojo@localhost:5432/dojo?sslmode=disable"
        ),
        redis_url=_getenv("REDIS_URL", "redis://localhost:6379/0"),
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
        service_name=_getenv("OTEL_SERVICE_NAME", "dojo-api"),
    )


cfg = load()
