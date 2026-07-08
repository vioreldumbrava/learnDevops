# app/api-py — the Python (FastAPI) twin of the Go API

A **drop-in alternative backend** for the DevOps Dojo. It speaks the exact same
HTTP contract as [`app/api`](../api/) (the Go version), hits the **same** Postgres
schema and **same** Redis queue, and exports the **same** `dojo_*` Prometheus
metrics — so the React frontend, the database, Grafana dashboards and alerts all
work against it **unchanged**. Only the language and runtime differ.

Its whole reason to exist is the comparison in
[lab 50](../../labs/50-go-vs-python-parity/): *the API contract is the interface;
the language is an implementation detail.*

## Side-by-side map to the Go app

| Concern | Go (`app/api`) | Python (`app/api-py`) |
|---|---|---|
| Web framework | chi | FastAPI |
| Concurrency | goroutine per request | async/await on one event loop |
| Postgres | `pgxpool` | `asyncpg` (same `$1` placeholders, same SQL) |
| Redis | `go-redis` | `redis.asyncio` |
| Metrics | `prometheus/client_golang` | `prometheus-client` (identical names) |
| Tracing | OTel `otelhttp` | OTel `FastAPIInstrumentor` |
| Config | `internal/config` | `app/config.py` (same env vars) |
| Entry points | `cmd/api`, `cmd/worker` | `app.main:app`, `python -m app.worker` |
| Image | distroless (static binary) | `python:3.12-slim`, non-root |

Endpoints (identical to Go): `GET /healthz`, `GET /readyz`, `GET /metrics`,
`GET /api/steps` (Redis-cached, `X-Cache: HIT|MISS`),
`POST /api/progress/{id}` (enqueues `dojo:jobs`), `GET|POST /api/notes`.

## Run it

Against the shared stack, via the Compose overlay (from the repo root):

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.py.yaml up --build
```

This overrides the `api` and `worker` services to build from here — everything
else (db, redis, frontend, ports) is unchanged. Open the dashboard and it behaves
exactly as before.

Run the tests (no DB/Redis needed — the store/cache are faked):

```powershell
docker run --rm -v ${PWD}/app/api-py:/w -w /w python:3.12-slim `
  sh -c "pip install -r requirements-dev.txt && pytest"
```

## Layout

```
app/config.py     env → settings (mirrors config.go)
app/store.py      asyncpg pool + Step/Note models (mirrors store.go)
app/cache.py      redis.asyncio cache + queue (mirrors cache.go)
app/metrics.py    Prometheus metrics — SAME names as the Go app
app/telemetry.py  OTel OTLP tracing (mirrors telemetry.go)
app/main.py       FastAPI app: routes, probes, /metrics, middleware
app/worker.py     Redis-queue consumer (mirrors cmd/worker)
tests/            contract tests with in-memory fakes
```
