# Runbook — API down or erroring (`/api/*` failing)

**Trigger:** blackbox probe on `/healthz` failing, error-rate alert
(`dojo_http_requests_total{status=~"5.."}`), or users report the dashboard won't load data.
**Impact:** the dashboard reads/writes fail; worker jobs may still drain.
**Severity guide:** all replicas down = page; one replica flapping = ticket.
**Dashboards:** Grafana → dojo-api (request rate, error rate, p95).

## Quick diagnosis (first 5 minutes)

1. `kubectl -n devops-dojo get pods -o wide` — are api pods `Running` and `READY 1/1`?
   - `CrashLoopBackOff` / `Error` → go to **A**.
   - `Running` but `0/1 READY` → go to **B**.
   - All green → go to **C** (the silent one).
2. `kubectl -n devops-dojo describe pod <api-pod>` — read the last Events block.
3. `kubectl -n devops-dojo logs deploy/api --previous` — the last crash's own words.

## Mitigation

### A — pods crashing (CrashLoopBackOff, OOMKilled, StartError)

```powershell
kubectl -n devops-dojo rollout history deploy/api        # did a deploy just happen?
kubectl -n devops-dojo rollout undo deploy/api           # roll back first, debug later
kubectl -n devops-dojo rollout status deploy/api
```

Exit code 137 + `OOMKilled` in describe = memory limit, not a bug — rolling back the limit
change (or raising it) is the fix.

### B — pods not Ready (readiness failing)

`/readyz` checks Postgres and Redis, so this is usually a *dependency* outage:

```powershell
kubectl -n devops-dojo get pods -l app=db
kubectl -n devops-dojo get pods -l app=redis
kubectl -n devops-dojo scale statefulset/db --replicas=1   # if db was scaled/evicted
```

Do **not** restart the api pods — they'll recover on their own once the dependency is back.

### C — everything green but traffic fails

```powershell
kubectl -n devops-dojo get endpoints api                  # <none> = selector/labels bug
kubectl -n devops-dojo get svc api -o jsonpath='{.spec.selector}'
kubectl -n devops-dojo port-forward deploy/api 8080:8080  # can the pod serve directly?
```

Empty endpoints → fix the Service selector to match pod labels (`app: api`). Pod serves on
port-forward but not via Ingress → work outward: Service → Ingress → ingress-nginx controller.

## Known causes seen before

| Signature | Cause | Reference |
|-----------|-------|-----------|
| StartError, `no such file` | broken image/command | lab 35 drill 1 |
| exit 137 OOMKilled | memory limit too low | lab 35 drill 2 |
| 0/1 Ready, db pod missing | Postgres outage | lab 35 drill 3 |
| green pods, no endpoints | Service selector typo | lab 35 drill 4 |
| rollout stuck, ImagePullBackOff | unpublished/typo'd tag | lab 35 drill 5 |

## After the incident

- Verify: `curl http://localhost/api/steps` returns JSON; error-rate panel back to baseline.
- Postmortem: [../postmortem-template.md](../postmortem-template.md).
