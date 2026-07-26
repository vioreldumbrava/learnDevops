"""The DevOps Dojo REST API — Python/FastAPI twin of the Go app/api.

Same endpoints, same JSON, same status codes, same probes and /metrics, so the
React frontend and the shared Postgres/Redis can't tell which one is serving.
Idiomatic differences from Go, called out for the lab-50 comparison:
  * async/await on one event loop (asyncio) instead of a goroutine per request;
  * FastAPI dependency-injection (get_store/get_cache) makes the handlers unit-
    testable with fakes — no DB/Redis needed in CI.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from . import metrics, telemetry
from .cache import Cache
from .config import cfg
from .store import Store

JOB_QUEUE = "dojo:jobs"
STEPS_CACHE_KEY = "steps:all"
STEPS_CACHE_TTL = 30  # seconds — matches the Go handler


# --- structured JSON logging (one line per request, Loki-friendly, matches Go) -
def _setup_logger() -> logging.Logger:
    log = logging.getLogger("dojo-api")
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(h)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


logger = _setup_logger()


def _log(level: int, msg: str, **fields) -> None:
    logger.log(level, json.dumps({"msg": msg, **fields}))


# --- dependency-injected singletons (populated by the lifespan) ----------------
_store: Store | None = None
_cache: Cache | None = None


def get_store() -> Store:
    if _store is None:
        raise RuntimeError("store not initialised")
    return _store


def get_cache() -> Cache:
    if _cache is None:
        raise RuntimeError("cache not initialised")
    return _cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the DB/Redis pools on startup, close them on SIGTERM. Tolerant on
    purpose: a failed dependency doesn't crash the process, it just makes
    /readyz report 503 (the readiness split from lab 08)."""
    global _store, _cache
    telemetry.init(cfg.service_name, cfg.otlp_endpoint)
    try:
        _store = await Store.connect(cfg.database_url)
    except Exception as e:  # pragma: no cover - needs a real DB to hit
        _log(logging.ERROR, "connect database", error=str(e))
    try:
        c = Cache(cfg.redis_url)
        await c.ping()
        _cache = c
    except Exception as e:  # pragma: no cover - needs real Redis to hit
        _log(logging.ERROR, "connect redis", error=str(e))
    yield
    if _store is not None:
        await _store.close()
    if _cache is not None:
        await _cache.close()


app = FastAPI(title="DevOps Dojo API (Python)", lifespan=lifespan)


# --- middleware: metrics for every request + one structured log line -----------
@app.middleware("http")
async def observe(request: Request, call_next):
    start = time.perf_counter()
    metrics.http_in_flight.inc()
    try:
        response = await call_next(request)
    finally:
        metrics.http_in_flight.dec()

    # Label by the matched ROUTE TEMPLATE (e.g. /api/progress/{id}), never the
    # raw path — same bounded-cardinality rule as the Go chi RoutePattern.
    route_obj = request.scope.get("route")
    route = getattr(route_obj, "path", None) or "unmatched"
    method = request.method
    metrics.http_duration.labels(method, route).observe(time.perf_counter() - start)
    metrics.http_requests.labels(method, route, str(response.status_code)).inc()

    # Skip the noisy liveness/metrics endpoints in the access log (matches Go).
    if request.url.path not in ("/healthz", "/metrics"):
        _log(
            logging.INFO,
            "http_request",
            method=method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=int((time.perf_counter() - start) * 1000),
        )
    return response


# --- operational endpoints -----------------------------------------------------
@app.get("/healthz")
async def healthz():
    """Liveness: the process is up. No dependency checks (lab 08)."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    """Readiness: can we actually serve? Ping DB + Redis, 503 if either is down."""
    checks = {"db": "ok", "redis": "ok"}
    ready = True
    if _store is None:
        checks["db"], ready = "not initialised", False
    else:
        try:
            await _store.ping()
        except Exception as e:
            checks["db"], ready = str(e), False
    if _cache is None:
        checks["redis"], ready = "not initialised", False
    else:
        try:
            await _cache.ping()
        except Exception as e:
            checks["redis"], ready = str(e), False
    return JSONResponse(checks, status_code=200 if ready else 503)


@app.get("/metrics")
async def prometheus_metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- the API ------------------------------------------------------------------
@app.get("/api/steps")
async def list_steps(store: Store = Depends(get_store), cache: Cache = Depends(get_cache)):
    cached = await cache.get(STEPS_CACHE_KEY)
    if cached is not None:
        return Response(cached, media_type="application/json", headers={"X-Cache": "HIT"})

    steps = await store.list_steps()
    # mode="json" so last_practiced_at serialises to an ISO string, not a datetime object.
    body = json.dumps([s.model_dump(mode="json") for s in steps])
    await cache.set(STEPS_CACHE_KEY, body, STEPS_CACHE_TTL)
    return Response(body, media_type="application/json", headers={"X-Cache": "MISS"})


@app.post("/api/progress/{step_id}")
async def set_progress(
    step_id: str,
    request: Request,
    store: Store = Depends(get_store),
    cache: Cache = Depends(get_cache),
):
    # Absent means "leave that flag alone", so both are optional — but a body with
    # neither is a no-op the caller didn't mean (same 400 as Go).
    try:
        req = await request.json()
        completed = None if req.get("completed") is None else bool(req["completed"])
        drilled = None if req.get("drilled") is None else bool(req["drilled"])
    except Exception:
        return JSONResponse({"error": "invalid body"}, status_code=400)
    if completed is None and drilled is None:
        return JSONResponse({"error": "set completed and/or drilled"}, status_code=400)

    if not await store.step_exists(step_id):
        return JSONResponse({"error": "unknown step"}, status_code=404)

    progress = await store.set_progress(step_id, completed, drilled)
    # Invalidate the cached list and queue a report-refresh job (same as Go).
    await cache.delete(STEPS_CACHE_KEY)
    await cache.enqueue(JOB_QUEUE, f"progress:{step_id}")
    return progress.model_dump(mode="json")


@app.get("/api/notes")
async def list_notes(step: str = "", store: Store = Depends(get_store)):
    if not step:
        return JSONResponse({"error": "missing step query param"}, status_code=400)
    notes = await store.list_notes(step)
    return [n.model_dump(mode="json") for n in notes]


@app.post("/api/notes")
async def add_note(request: Request, store: Store = Depends(get_store)):
    try:
        req = await request.json()
        step_id, body = req["step_id"], req["body"]
    except Exception:
        step_id, body = "", ""
    if not step_id or not body:
        return JSONResponse(
            {"error": "step_id and body are required"}, status_code=400
        )
    note = await store.add_note(step_id, body)
    return JSONResponse(note.model_dump(mode="json"), status_code=201)


telemetry.instrument_app(app)
