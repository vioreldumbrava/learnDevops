# Lab 12 — Tracing + Alerting

**Maps to:** extra (completes observability) · **Milestone:** 1

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

**Tracing** is the third pillar: a trace follows one request across functions/services as a
tree of **spans**, showing where time went. The Dojo API uses **OpenTelemetry** to export
traces to **Tempo**. Separately, **alerting** turns metrics into action: Prometheus
evaluates rules and pushes firing alerts to **Alertmanager**, which routes notifications.

## What you'll do

See a request's trace (with a nested DB span), then fire a real alert.

## Steps — tracing

```powershell
docker compose -f deploy/compose/compose.yaml `
  -f deploy/compose/compose.observability.yaml up -d --build

# Make requests so traces are produced (the overlay points the API at Tempo)
1..10 | ForEach-Object { curl -s http://localhost:8080/api/steps > $null }
```

In **Grafana** (<http://localhost:3001>) → **Explore** → datasource **Tempo** → **Search** →
run a search and open a trace. You'll see the `dojo-api` server span with a child
`store.ListSteps` span (and `SetProgress` if you toggle progress).

## Steps — alerting

```powershell
# See the configured rules
Start-Process http://localhost:9090/alerts

# Fire ApiDown by stopping the API
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.observability.yaml stop api

# After ~1 min the alert moves Pending -> Firing; see it routed to Alertmanager
Start-Process http://localhost:9093

# Recover
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.observability.yaml start api
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.observability.yaml down
```

## How it works

- **Tracing:** `telemetry.go` sets up an OTLP/HTTP exporter to `tempo:4318` (enabled only
  when the observability overlay sets `OTEL_EXPORTER_OTLP_ENDPOINT`). `otelhttp` creates the
  server span; the `store` layer starts child spans, so the trace shows the DB call nested
  inside the request.
- **Alerting:** `deploy/monitoring/prometheus/alerts.yml` defines `ApiDown`, `HighErrorRate`,
  and `HighLatencyP95`. Prometheus evaluates them and forwards firing alerts to Alertmanager
  (`:9093`), which groups/routes them (add an email/Slack receiver to actually notify).

You now have all **three pillars** — metrics (10), logs (11), traces (12) — plus alerts, in
one Grafana.

## Exercise

Trigger `HighLatencyP95` or `HighErrorRate`: hammer a bad route
(`1..200 | % { curl -s http://localhost:8080/api/nope > $null }`) and watch the error-rate
alert progress on `:9090/alerts`. Why does it take a few minutes to fire? (Hint: `for: 5m`.)

## Checkpoint

- ✅ A Tempo trace shows a `store.*` span nested under the `dojo-api` request span.
- ✅ Stopping the API moves `ApiDown` to **Firing** and it appears in Alertmanager.
- ✅ You can explain the metrics/logs/traces split.

## Common failures

- No traces → make sure you used the **observability** overlay (it injects the Tempo
  endpoint); without it, tracing is intentionally off.
- Alert never fires → give it the `for:` duration; confirm Prometheus → Status ▸ Rules loaded.

➡️ Milestone 1 complete. Milestone 2 (CI/CD, Terraform, Ansible) comes next — see
[docs/CURRICULUM.md](../../docs/CURRICULUM.md).
