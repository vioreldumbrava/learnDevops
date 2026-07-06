# Lab 09 — Cache + background worker (Redis queue)

**Maps to:** extra (rounds out the original path) · **Milestone:** 1

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Two classic uses of Redis:
- **Cache:** store the result of an expensive read so repeated requests are fast. You must
  **invalidate** it when the underlying data changes.
- **Queue:** push work onto a list and let a separate **worker** process it off the request
  path. The worker is **stateless**, so you can run many copies (lab 21).

## What you'll do

Observe a cache hit/miss and a job flowing from the API to the worker.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml up -d --build

# First call computes from Postgres (MISS); second is served from Redis (HIT)
curl -i http://localhost:8080/api/steps | Select-String "X-Cache"
curl -i http://localhost:8080/api/steps | Select-String "X-Cache"

# Toggling progress invalidates the cache AND enqueues a worker job
curl -X POST http://localhost:8080/api/progress/01-docker-basics -H "Content-Type: application/json" -d '{\"completed\":true}'

# The worker logs show it consuming the job
docker compose -f deploy/compose/compose.yaml logs worker

# Peek at Redis directly
docker compose -f deploy/compose/compose.yaml exec redis redis-cli keys "*"
docker compose -f deploy/compose/compose.yaml down
```

## How it works

`GET /api/steps` checks Redis (`steps:all`); on a miss it queries Postgres, caches the JSON
for 30s, and returns `X-Cache: MISS` (then `HIT`). `POST /api/progress/{id}` writes to
Postgres, **deletes** the cache key (so the next read is fresh), and `LPUSH`es a job onto
`dojo:jobs`. The `worker` service (same image, `/worker` entrypoint) `BRPOP`s that queue and
processes jobs — standing in for report/certificate generation you'd offload from the API.

## Exercise

Scale the worker to 3 and toggle several labs quickly, then read the logs:

```powershell
docker compose -f deploy/compose/compose.yaml up -d --scale worker=3
docker compose -f deploy/compose/compose.yaml logs worker | Select-String "processing job"
```

Different replicas pick up different jobs — that's the payoff of a stateless worker + queue.

## Checkpoint

- ✅ Second `/api/steps` call shows `X-Cache: HIT`.
- ✅ After a progress POST, the worker logs `processing job progress:...`.
- ✅ (Exercise) With 3 workers, jobs are spread across replicas.

## Common failures

- Always `MISS` → cache TTL (30s) expired between calls, or you POSTed in between (which
  invalidates). Call twice quickly.
- No worker logs → ensure the `worker` service is up (`docker compose ps`).

➡️ Next: [Lab 10 — Monitoring](../10-monitoring/)
