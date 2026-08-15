# Lab 11 — Logging: Loki + Grafana Alloy

**Tier:** specialization · **Track:** SRE · **Maps to:** original §11

**Run from:** the **repo root** (`learnDevops/`). Every command and path below is relative to it.

## Concept

Logs are the second pillar of observability. Instead of reading one container at a time,
centralize them: **Grafana Alloy** discovers containers and ships their stdout/stderr to
**Loki**, which you query in Grafana with LogQL. Alloy replaces Promtail, which reached end
of life on 2 March 2026. Structured JSON logs let you filter by fields such as service,
status, and duration.

## What you'll do

Ship the stack's logs through Alloy to Loki and query the API's structured request logs.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml `
  -f deploy/compose/compose.observability.yaml up -d --build

# Generate normal and failing requests.
1..20 | ForEach-Object { curl.exe -s http://localhost:8080/api/steps | Out-Null }
1..5  | ForEach-Object { curl.exe -s http://localhost:8080/api/nope  | Out-Null }

# Confirm the collector is healthy before opening Grafana.
docker compose -f deploy/compose/compose.yaml `
  -f deploy/compose/compose.observability.yaml logs --tail=50 alloy
```

In **Grafana** (<http://localhost:3001>) → **Explore** → datasource **Loki**:

```logql
{compose_project="devops-dojo"}
{compose_service="api"}
{compose_service="api"} | json | status >= 400
```

For a machine-checkable delivery test, query Loki directly:

```powershell
$query = [uri]::EscapeDataString('{compose_service="api"}')
$result = Invoke-RestMethod "http://localhost:3100/loki/api/v1/query_range?query=$query&limit=20"
if ($result.data.result.Count -eq 0) { throw "Alloy has not delivered an API log to Loki" }
```

When finished:

```powershell
docker compose -f deploy/compose/compose.yaml `
  -f deploy/compose/compose.observability.yaml down
```

## How it works

The API emits one JSON line per request through Go's `slog`. Alloy reads the read-only Docker
socket, discovers Compose containers, promotes Compose metadata into Loki labels, and pushes
each stream to Loki. The configuration lives at
[`deploy/monitoring/alloy/config.alloy`](../../deploy/monitoring/alloy/config.alloy).

> **Local trust boundary:** reading the Docker socket is root-equivalent access to the local
> engine. This is acceptable for this isolated lab, not a production collector pattern. In a
> production platform, scope the collector and its permissions deliberately.

## Exercise

Find slow requests with `{compose_service="api"} | json | duration_ms > 5`, then correlate
them with the metrics from lab 10. Logs explain individual events; metrics describe their
frequency and trend.

## Checkpoint

- `{compose_service="api"}` returns log lines in Grafana Explore.
- `... | json | status >= 400` isolates the generated 404s.
- The direct Loki query returns at least one API stream delivered by Alloy.
- You can also find `db`, `redis`, and `worker` streams.

## Common failures

- No logs in Loki → inspect `docker compose ... logs alloy`; confirm Docker Desktop exposes
  the socket and that `loki` is healthy.
- LogQL parse error → `| json` must precede field filters such as `status >= 400`.
- Empty direct query immediately after traffic → wait a few seconds for batching, then retry.

➡️ Next: [Lab 12 — Tracing + Alerting](../12-tracing-and-alerting/)
