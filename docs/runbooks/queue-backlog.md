# Runbook — job queue backing up (`dojo:jobs`)

**Trigger:** queue-depth alert, or progress toggles apply but downstream effects lag.
**Impact:** background work (report refresh jobs) delayed; user-facing reads/writes still OK.
**Severity guide:** steadily growing depth = investigate; bounded burst that drains = normal.
**Dashboards:** Grafana → dojo-api; KEDA scaling events if lab 31 is applied.

## Quick diagnosis (first 5 minutes)

1. How deep, and is it growing?

   ```powershell
   kubectl -n devops-dojo exec deploy/redis -- redis-cli LLEN dojo:jobs
   # run twice, 30s apart: growing = consumers broken or outpaced; shrinking = burst draining
   ```

2. Are there consumers at all?

   ```powershell
   kubectl -n devops-dojo get pods -l app=worker         # Running? Ready? restarting?
   kubectl -n devops-dojo logs deploy/worker --tail=50   # consuming, erroring, or silent?
   ```

3. Producer-side sanity: is the API suddenly enqueueing far more than usual (request-rate
   panel), i.e. is this a demand spike rather than a consumer failure?

## Mitigation

- **No workers / crashing workers:** treat like [api-down](api-down.md) mitigation A —
  `kubectl -n devops-dojo rollout undo deploy/worker` if it started with a deploy.
- **Workers healthy but outpaced:** scale them — the worker is stateless and pulls from the
  queue, so replicas share work with no coordination:

  ```powershell
  kubectl -n devops-dojo scale deploy/worker --replicas=4
  ```

  With KEDA (lab 31) this happens automatically from queue depth — check
  `kubectl -n devops-dojo get scaledobject` if it didn't.
- **Workers stuck on a poison message** (same job failing in a loop in the logs): capture the
  payload, then remove it — `redis-cli LREM dojo:jobs 1 "<payload>"` — and file the bug. Don't
  flush the queue.

## Known causes seen before

| Signature | Cause | Reference |
|-----------|-------|-----------|
| depth grows, worker logs silent | worker can't reach Redis | lab 09 |
| depth grows during load test | expected — watch it drain | labs 20/31 |
| same payload erroring repeatedly | poison message | this runbook |

## After the incident

- Verify: `LLEN dojo:jobs` at/near zero and stable; worker logs consuming.
- Postmortem if user-visible: [../postmortem-template.md](../postmortem-template.md).
