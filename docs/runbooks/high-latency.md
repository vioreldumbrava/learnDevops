# Runbook — API slow (p95 latency above threshold)

**Trigger:** p95 alert on `dojo_http_request_duration_seconds` (see
`deploy/monitoring/prometheus/alerts.yml`), or users report the dashboard is sluggish.
**Impact:** degraded UX; timeouts upstream if it worsens.
**Severity guide:** p95 > 1s sustained = investigate now; brief spike during deploy = watch.
**Dashboards:** Grafana → dojo-api (p95, request rate, in-flight); node/cluster (lab 34).

## Quick diagnosis (first 5 minutes)

Work the three pillars in order — *what* → *what happened* → *where the time went*:

1. **Metrics:** is it all endpoints or one? Did request rate jump (load) or stay flat
   (something got slower)? Check `dojo_http_in_flight_requests` — climbing in-flight with
   flat rate means requests are stuck, not numerous.
2. **Logs (Loki):** `{compose_service="api"} | json | duration > 1s` — errors, retries,
   timeouts toward db/redis?
3. **Traces (Tempo):** open a slow trace — is the time in the `store.*` (Postgres) span, the
   cache span, or the handler itself? This answers "app vs database" in one click.
4. Resources: `kubectl -n devops-dojo top pods` — CPU-throttled api pods (at their `limits`)
   or a db pod at its ceiling?

## Mitigation

- **Load-shaped** (rate up, all endpoints slow): scale out —
  `kubectl -n devops-dojo scale deploy/api --replicas=4` (or let the HPA/KEDA do it, labs 22/31).
- **DB-shaped** (time in `store.*` spans): check Postgres — long queries
  (`SELECT * FROM pg_stat_activity WHERE state != 'idle';`), missing cache (Redis down makes
  every read hit the DB — check `kubectl -n devops-dojo get pods -l app=redis`).
- **Throttle-shaped** (CPU at limit): raise the CPU limit or add replicas; confirm with
  `container_cpu_cfs_throttled_periods_total` in Prometheus.
- **Deploy-shaped** (started at a rollout): `kubectl -n devops-dojo rollout undo deploy/api`.

## Known causes seen before

| Signature | Cause | Reference |
|-----------|-------|-----------|
| every read slow, cache MISS logs | Redis down/flushed | lab 09 |
| time in store.* spans | slow/locked queries | lab 12 traces |
| in-flight climbing, writes failing | DB read-only / disk full | lab 35 drill 7 |

## After the incident

- Verify: p95 back under threshold for 15 min; no in-flight buildup.
- If the fix was "add replicas", feed the new baseline back into the k6 thresholds (lab 20).
- Postmortem: [../postmortem-template.md](../postmortem-template.md).
