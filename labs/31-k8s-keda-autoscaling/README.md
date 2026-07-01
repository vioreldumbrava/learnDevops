# Lab 31 — KEDA event-driven autoscaling

**Maps to:** deepens §19 · **Milestone:** K8s deep-dive · *the standout skill*

## Concept

The HPA scales on CPU/memory — but many workloads should scale on **work waiting**, not CPU.
**KEDA** scales a Deployment on external signals: queue depth, topic lag, stream length, cron,
and dozens more. Here it's a perfect fit: the **worker** already consumes a Redis list
(`dojo:jobs`), so we scale it on **queue depth** — and it can even scale to zero when idle.

## What you'll do

Install KEDA, autoscale the worker on the Redis queue, flood the queue, and watch replicas grow.

## Steps

```powershell
# Install KEDA
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda -n keda --create-namespace
kubectl -n keda rollout status deploy/keda-operator --timeout=180s

kubectl apply -f deploy/k8s/keda/scaledobject.yaml
kubectl -n devops-dojo get scaledobject,hpa   # KEDA creates a managed HPA

# Flood the queue via the API (each progress toggle enqueues a job), then watch it scale:
1..200 | ForEach-Object {
  Invoke-WebRequest -UseBasicParsing -Method POST -ContentType 'application/json' `
    -Body '{\"completed\":true}' http://localhost/api/progress/01-docker-basics > $null
}
kubectl -n devops-dojo get pods -l app=worker -w
```

## How it works

[scaledobject.yaml](../../deploy/k8s/keda/scaledobject.yaml) targets the `worker` Deployment
with a `redis` trigger on `dojo:jobs` and `listLength: 5` (aim for ~5 queued jobs per replica).
KEDA translates that into a managed HPA driven by an external metric; as the list grows past the
target it adds workers (up to `maxReplicaCount: 10`), and scales back down (toward
`minReplicaCount`) as it drains. This is the pattern behind autoscaling consumers, ETL, and
inference queues in production.

## Exercise

Set `minReplicaCount: 0` and add an `idleReplicaCount: 0`, then let the queue drain fully —
watch the worker scale to **zero** pods, then spin back up on the next job. Scale-to-zero is
KEDA's superpower for bursty/idle workloads (and cost).

## Checkpoint

- ✅ `kubectl get scaledobject` shows the worker scaler active and a managed HPA created.
- ✅ Flooding the queue scales `worker` replicas up; draining scales them back down.
- ✅ You can explain event-driven vs. CPU-based autoscaling.

## Common failures

- No scaling → KEDA can't reach Redis (`address: redis:6379` must resolve in-namespace), or the
  queue never grows (make sure the API/worker are running so jobs are produced).
- Replicas flap → tune `cooldownPeriod`/`pollingInterval` and the `listLength` target.

➡️ Next: [Lab 32 — Argo Rollouts (canary)](../32-k8s-argo-rollouts/)
