"""OpenTelemetry tracing over OTLP/HTTP — a port of the Go app's
internal/telemetry/telemetry.go. Same env var (OTEL_EXPORTER_OTLP_ENDPOINT),
same rule: empty endpoint = tracing disabled (a no-op provider). When enabled,
spans export to Tempo (lab 12) and sit in the same trace view as the Go API's.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("dojo-api")


def init(service_name: str, endpoint: str) -> None:
    """Configure the global tracer provider. No-op when endpoint is empty."""
    if not endpoint:
        return

    # Imported lazily so the package still runs (untraced) if the OTel SDK
    # isn't installed — same defensive posture as the Go "continue without
    # traces" path.
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Accept "http://host:port", "https://host:port" or bare "host:port".
    ep = endpoint.removeprefix("http://").removeprefix("https://")
    exporter = OTLPSpanExporter(endpoint=f"http://{ep}/v1/traces")

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    logger.info("tracing enabled -> %s", ep)


def instrument_app(app) -> None:
    """Auto-instrument FastAPI so every request is a span (the equivalent of the
    Go otelhttp handler wrapper). Safe to call even when tracing is disabled."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as e:  # pragma: no cover - instrumentation is best-effort
        logger.warning("fastapi instrumentation unavailable: %s", e)
