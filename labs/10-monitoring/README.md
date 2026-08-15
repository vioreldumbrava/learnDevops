# Lab 10 — Monitoring: Prometheus + Grafana

**Maps to:** original §10 · **Milestone:** 1

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

**Metrics** are cheap numeric time-series (request counts, latencies, gauges). **Prometheus**
*scrapes* a `/metrics` endpoint on an interval and stores them; **Grafana** visualizes them.
For services that don't expose metrics, a **blackbox exporter** probes their HTTP endpoints
from outside. The Dojo API exposes real metrics, so this is genuine monitoring, not a toy.

## What you'll do

Start the observability overlay, see the API's metrics scraped, and read a Grafana dashboard.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml `
  -f deploy/compose/compose.observability.yaml up -d --build

# The raw metrics the API exposes
curl http://localhost:8080/metrics | Select-String "dojo_http_requests_total"

# Generate some traffic
1..50 | ForEach-Object { curl -s http://localhost:8080/api/steps > $null }
```

Open:
- **Prometheus** <http://localhost:9090> → Status ▸ Targets (the `dojo-api` target is `UP`),
  then graph `rate(dojo_http_requests_total[1m])`.
- **Grafana** <http://localhost:3001> (admin / admin) → dashboard **DevOps Dojo · API**.

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.observability.yaml down
```

## How it works

The API uses `prometheus/client_golang` to expose counters/histograms/gauges at `/metrics`
(see [metrics.go](../../app/api/internal/httpapi/metrics.go)). Prometheus' scrape config
(`deploy/monitoring/prometheus/prometheus.yml`) pulls `api:8080/metrics` every 15s and also
drives the **blackbox** probes of `/healthz`. Grafana is provisioned automatically with the
Prometheus datasource and the `dojo-api` dashboard.

## Exercise

Add a panel to the dashboard (or a Prometheus graph) for **error ratio**:
`sum(rate(dojo_http_requests_total{status=~"5.."}[5m])) / sum(rate(dojo_http_requests_total[5m]))`.
Then hit a non-existent route a few times (`curl http://localhost:8080/api/nope`) and watch
the `unmatched`/`404` series appear.

## Checkpoint

- ✅ Prometheus shows the `dojo-api` target **UP**.
- ✅ `rate(dojo_http_requests_total[1m])` is non-zero after generating traffic.
- ✅ The Grafana dashboard shows request rate and p95 latency.

## Common failures

- Target DOWN → the `api` service isn't running, or you forgot the observability overlay.
- Grafana "no data" → generate traffic first; check the time range is "last 15 minutes".

➡️ Next: [Lab 13 — Image registry](../13-image-registry/)
