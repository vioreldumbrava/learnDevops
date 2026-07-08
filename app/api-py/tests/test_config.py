"""Config parsing — the Python mirror of config_test.go: defaults when unset,
env override when present."""
import importlib

from app import config


def test_defaults(monkeypatch):
    for var in ("PORT", "DATABASE_URL", "REDIS_URL", "OTEL_EXPORTER_OTLP_ENDPOINT",
                "OTEL_SERVICE_NAME"):
        monkeypatch.delenv(var, raising=False)
    cfg = config.load()
    assert cfg.port == "8080"
    assert cfg.database_url.startswith("postgres://")
    assert cfg.redis_url == "redis://localhost:6379/0"
    assert cfg.otlp_endpoint == ""          # empty -> tracing disabled
    assert cfg.service_name == "dojo-api"


def test_env_override(monkeypatch):
    monkeypatch.setenv("PORT", "9999")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "tempo:4318")
    cfg = config.load()
    assert cfg.port == "9999"
    assert cfg.otlp_endpoint == "tempo:4318"
