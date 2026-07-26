# Lab 50 — Same service, two languages (Go vs Python)

**Maps to:** extra (polyglot) · **Milestone:** Foundation · **Platform**

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

> ℹ️ **Order note:** optional, and out of numeric order on purpose (appended late). Do it any
> time after [lab 09](../09-cache-and-worker/) — you just need the app, the Redis cache and the
> worker to exist. [CURRICULUM.md](../../docs/CURRICULUM.md) shows the intended order.

## Concept

The DevOps Dojo API ships in **two implementations**: the Go [`app/api`](../../app/api/) you've
used all along, and a Python/FastAPI twin [`app/api-py`](../../app/api-py/). They are not two
different apps — they are the **same service** behind the **same contract**: identical HTTP
endpoints and JSON, the same Postgres schema, the same Redis queue, the same `dojo_*` Prometheus
metric names, the same env vars. So the React frontend, the database, and your Grafana
dashboards work against **either one without changing anything**.

That's the lesson, and it's a senior one: **the API contract is the interface; the language is
an implementation detail.** A polyglot fleet stays coherent not because everything is written in
one language, but because every service honours the same contracts (HTTP, metric names, log
shape). This lab makes you *feel* that by hot-swapping the backend language under a running
system.

## What you'll do

Run the stack on the Go backend, swap it to the Python backend with a one-file Compose overlay
(nothing else changes), prove the behaviour is identical, then compare the two implementations.

## Steps

### 1. Run the Go backend, look at the contract

```powershell
docker compose -f deploy/compose/compose.yaml up -d --build
curl -s -D- http://localhost:8080/api/steps -o steps-go.json    # note the X-Cache header
curl -s http://localhost:8080/metrics | Select-String dojo_http_    # the metric names
# Open http://localhost:3000 and tick a couple of labs complete.
docker compose -f deploy/compose/compose.yaml down
```

### 2. Swap to the Python backend — one overlay, nothing else

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.py.yaml up -d --build
```

[compose.py.yaml](../../deploy/compose/compose.py.yaml) overrides just three keys on the `api`
and `worker` services — build context, image tag, and start command. Service names, port 8080,
the db/redis/frontend services, and every dependency are inherited unchanged.

### 3. Prove it's the same service

```powershell
# Same 57 steps, same JSON field names (id, lab_no, completed, drilled, last_practiced_at, …):
curl -s http://localhost:8080/api/steps -o steps-py.json
#   -> the ticks you made under Go in step 1 are STILL THERE. State lives in
#      Postgres, not in the app — so swapping the app language changes nothing.

# Same cache behaviour (MISS then HIT):
curl -s -D- http://localhost:8080/api/steps -o $null | Select-String -i x-cache

# Same metric names — your existing Prometheus/Grafana/alerts don't know the difference:
curl -s http://localhost:8080/metrics | Select-String dojo_http_

# Same worker contract: toggling a lab enqueues dojo:jobs, the Python worker drains it:
curl -s -X POST http://localhost:8080/api/progress/01-docker-basics `
  -H "Content-Type: application/json" -d '{\"completed\":true}'
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.py.yaml logs worker --tail 5
#   -> {"msg":"processing job","job":"progress:01-docker-basics"}  {"msg":"job done",...}
```

The **frontend at http://localhost:3000 behaves identically** — it never knew the backend changed.

### 4. Compare the two implementations

```powershell
docker images | Select-String "devops-dojo/api"      # image size
```

| | Go (`app/api`) | Python (`app/api-py`) |
|---|---|---|
| **Image size** | ~52 MB (distroless static binary) | ~276 MB (python:3.12-slim + interpreter + deps) |
| **Source size** | ~690 lines | ~550 lines |
| **Concurrency** | goroutine per request (cheap threads, preemptive) | async/await on one event loop (cooperative) |
| **Web layer** | chi router + net/http | FastAPI + Starlette/uvicorn |
| **DB / Redis** | pgxpool / go-redis | asyncpg / redis.asyncio |
| **Startup** | instant (compiled) | ~1s (interpreter + imports) |
| **Type safety** | compile-time | runtime (pydantic validates at the edges) |
| **Best when** | throughput, small images, CPU-bound, long-running | speed of iteration, data/ML ecosystem, glue |

### 5. Clean up

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.py.yaml down
```

## How it works

The two apps are structured the same on purpose so you can read them side by side:
`config`, `store` (Postgres), `cache` (Redis + queue), `metrics`, `telemetry`, an HTTP layer, and
a worker entrypoint. The Python `store.py` even uses the **same SQL** — asyncpg's `$1`
placeholders are identical to pgx's — so the queries are copy-paste equal. What genuinely differs
is the *concurrency model* (goroutines vs asyncio) and the *packaging* (a static binary on
distroless vs an interpreter image). In Kubernetes the swap is one line, because the contract —
not the code — is what the cluster wires together:

```powershell
kubectl -n devops-dojo set image deploy/api api=devops-dojo/api-py:dev   # after `kind load`
```

## Exercise

Run the observability overlay too
(`-f deploy/compose/compose.observability.yaml`) and open the API dashboard in Grafana while the
**Python** backend serves. The panels light up unchanged — because both export the same
`dojo_http_*` metrics. That single fact is why a company can run a polyglot fleet on one
monitoring stack.

## Checkpoint

- ✅ The frontend and DB behave identically on both backends; progress ticked under Go is still
  present under Python (state lives in Postgres).
- ✅ `/api/steps` returns the same 24-step JSON with the same field names; `/metrics` exposes the
  same `dojo_http_*` names on both.
- ✅ The Python worker drains the `dojo:jobs` queue the API enqueues to.
- ✅ You can state, with the size/concurrency numbers to back it, when you'd choose Go vs Python
  for a service.

## Common failures

- `api-py` build fails on `asyncpg` → the slim image needs no compiler for the wheels used here;
  if you pinned a source-only version, add `build-essential` or use the provided pins.
- Python worker logs a Redis `TimeoutError` → you're on an older `app/api-py`; the current
  `cache.dequeue` treats a blocking-read timeout as "no job, poll again".
- `/api/steps` differs between backends → you changed one implementation's JSON; the contract is
  the test — keep them equal (that's the point).
- Port 8080 already bound → the Go stack from step 1 is still up; `down` it first.

## Where to go next

- Point k6 (lab 20) at each backend and compare p95 latency and throughput under the same load —
  turns this qualitative comparison into numbers.
- The **operator** is deliberately Go-only (`dojo-operator/`); Python's `kopf` is the equivalent
  framework if you ever want the same twin exercise for a controller.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md).
