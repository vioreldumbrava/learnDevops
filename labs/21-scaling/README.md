# Lab 21 — Horizontal scaling

**Maps to:** original §19 · **Milestone:** 3

## Concept

Scale **out** by running more replicas of **stateless** services (`api`, `worker`,
`frontend`). Two rules:
- **Stateful** services (`db`, `redis`) can't be scaled by just adding copies — they'd
  diverge; they need clustering/replication strategies.
- A service with a **fixed host port** can't have multiple replicas (they'd collide on the
  port) — put it behind a reverse proxy instead, and don't publish its host port.

## What you'll do

Scale the worker trivially, then scale the web tier behind a load-balancing Caddy.

## Steps — the easy win: worker

```powershell
docker compose -f deploy/compose/compose.yaml up -d --scale worker=3
docker compose -f deploy/compose/compose.yaml ps
```

Three workers share the Redis queue; each job is handled by exactly one. No proxy needed —
the worker has no ports.

## Steps — the web tier behind Caddy

```powershell
docker compose --env-file .env `
  -f deploy/compose/compose.yaml `
  -f deploy/compose/compose.prod.yaml `
  -f deploy/compose/compose.scale.yaml `
  up -d --build --scale api=3 --scale frontend=2

docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml -f deploy/compose/compose.scale.yaml ps

# Hit it repeatedly; requests are spread across the api replicas
1..10 | ForEach-Object { (Invoke-WebRequest -UseBasicParsing http://localhost/api/steps).StatusCode }
```

Tear down:

```powershell
docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml -f deploy/compose/compose.scale.yaml down -v
```

## How it works

[compose.scale.yaml](../../deploy/compose/compose.scale.yaml) removes the `api`/`frontend`
host ports (so replicas don't collide) and swaps Caddy to
[Caddyfile.scale](../../deploy/caddy/Caddyfile.scale), which uses **dynamic DNS upstreams**
(`dynamic a`) to re-resolve the service name and load-balance across every replica Docker
returns. `db` and `redis` are deliberately left at one replica.

## Exercise

While the scaled web tier runs, re-run the k6 load test from lab 20 against Caddy
(`-e TARGET_URL=http://caddy:80`) with high VUs, and compare p95 latency to the single-replica
run. More stateless replicas ⇒ more headroom.

## Checkpoint

- ✅ `--scale worker=3` shows three worker containers sharing the queue.
- ✅ `--scale api=3` runs three API replicas reachable through Caddy on port 80.
- ✅ You can explain why `db` isn't scaled the same way.

## Common failures

- `port is already allocated` when scaling → you scaled a service that still publishes a host
  port; use the scale overlay (which removes them) and reach it via Caddy.
- All requests seem to hit one replica → give Caddy's `dynamic a` a moment to refresh (5s), or
  confirm you're using `Caddyfile.scale` (the scale overlay mounts it).

➡️ Next: [Lab 22 — Kubernetes on kind](../22-kubernetes/)
