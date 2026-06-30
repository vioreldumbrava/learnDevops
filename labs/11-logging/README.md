# Lab 11 — Logging: Loki + Promtail

**Maps to:** original §11 · **Milestone:** 1

## Concept

Logs are the second pillar of observability. Instead of `docker logs` per container, you
**centralize** them: **Promtail** discovers containers and ships their stdout to **Loki**,
which you query in Grafana with LogQL — filtering by service, status, or text. Structured
(JSON) logs make this far more powerful than plain text.

## What you'll do

Ship the stack's logs to Loki and query the API's structured request logs.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml `
  -f deploy/compose/compose.observability.yaml up -d --build

# Generate a mix of traffic (some 404s)
1..20 | ForEach-Object { curl -s http://localhost:8080/api/steps > $null }
1..5  | ForEach-Object { curl -s http://localhost:8080/api/nope  > $null }
```

In **Grafana** (<http://localhost:3001>) → **Explore** → datasource **Loki**:

```logql
{compose_project="devops-dojo"}                       # everything
{compose_service="api"}                               # just the API
{compose_service="api"} | json | status >= 400        # only error responses
```

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.observability.yaml down
```

## How it works

The API logs one JSON line per request via Go's `slog` (method, path, status, duration_ms).
Promtail (`deploy/monitoring/promtail/promtail-config.yml`) reads the **Docker socket** to
discover containers, labels each stream with `compose_service`/`compose_project`, and pushes
to Loki. In Grafana, `| json` parses the line so you can filter on fields like `status`.

> ⚠️ Promtail reads the Docker socket — powerful and convenient locally, but a security
> consideration in production (revisited in lab 19).

## Exercise

Find the slowest requests: query `{compose_service="api"} | json | duration_ms > 5` and
correlate with the metrics from lab 10. Logs tell you *what happened*; metrics tell you
*how often* — together they're far stronger than either alone.

## Checkpoint

- ✅ `{compose_service="api"}` returns log lines in Grafana Explore.
- ✅ `... | json | status >= 400` isolates the 404s you generated.
- ✅ You can see `db`, `redis`, `worker` streams too.

## Common failures

- No logs in Loki → Promtail can't reach the Docker socket; on Docker Desktop ensure file
  sharing is enabled. Check `docker compose logs promtail`.
- LogQL parse error → `| json` must come before field filters like `status >= 400`.

➡️ Next: [Lab 12 — Tracing + Alerting](../12-tracing-and-alerting/)
