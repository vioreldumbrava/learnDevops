# Lab 08 — Health checks: liveness vs readiness

**Maps to:** original §9 · **Milestone:** 1

## Concept

Two different questions:
- **Liveness** (`/healthz`): "is the process alive?" If not, restart it.
- **Readiness** (`/readyz`): "can it serve traffic *right now*?" It checks dependencies
  (DB, Redis). If not ready, stop sending it traffic — but don't restart it.

Conflating them causes restart loops (e.g., restarting the app because the database is slow).
Compose uses healthchecks for `depends_on: condition: service_healthy`; Kubernetes uses the
same split as liveness/readiness probes (lab 22).

## What you'll do

Watch the two endpoints diverge when a dependency goes away.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml up -d --build
docker compose -f deploy/compose/compose.yaml ps   # note the health column

# Both healthy now
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz

# Take the database away
docker compose -f deploy/compose/compose.yaml stop db

# Liveness still OK (process is fine) ...
curl http://localhost:8080/healthz
# ... but readiness fails (can't reach the DB) -> HTTP 503
curl -i http://localhost:8080/readyz

# Bring it back
docker compose -f deploy/compose/compose.yaml start db
curl http://localhost:8080/readyz
docker compose -f deploy/compose/compose.yaml down
```

## How it works

`/healthz` returns 200 unconditionally (the binary is the healthcheck — `/api -healthcheck`,
since the distroless image has no shell). `/readyz` pings Postgres **and** Redis with a 2s
timeout and returns 503 if either is down, with a JSON body naming the failing dependency.
The Compose healthcheck on `api` uses liveness; `depends_on` on `db`/`redis` uses *their*
healthchecks so the API only starts once they're ready.

## Exercise

Stop `redis` instead of `db` and hit `/readyz`. Read the JSON body — which dependency does
it name? Confirm `/healthz` is still 200.

## Checkpoint

- ✅ With `db` stopped: `/healthz` = 200, `/readyz` = 503.
- ✅ The `/readyz` body names the broken dependency.
- ✅ `docker compose ps` shows the api's health status reflecting liveness.

## Common failures

- `/readyz` always 503 → the api can't resolve `db`/`redis`; check they're on the same
  Compose project and running.
- Curl shows no status → add `-i` to see headers including the HTTP code.

➡️ Next: [Lab 09 — Cache + background worker](../09-cache-and-worker/)
