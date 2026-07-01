# Lab 22 — Kubernetes on kind

**Maps to:** original §20 · **Milestone:** 3

## Concept

Compose runs containers on one host; **Kubernetes** orchestrates them across a cluster with
self-healing, rolling updates, and autoscaling. The mental model maps cleanly:

| Compose | Kubernetes |
|---------|------------|
| service | Deployment + Service |
| named volume | PersistentVolumeClaim (StatefulSet for stateful) |
| `.env` / environment | ConfigMap + Secret |
| one-shot `migrate` | Job |
| Caddy / published ports | Ingress |
| `--scale` | `replicas` + HorizontalPodAutoscaler |

## What you'll do

Run the whole stack on a local **kind** cluster and reach it through an Ingress.

## Steps

Full walkthrough (create cluster, install ingress-nginx, load images, apply) is in
[deploy/k8s/README.md](../../deploy/k8s/README.md). The short version:

```powershell
kind create cluster --config deploy/k8s/kind/kind-cluster.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait -n ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s

docker build -t devops-dojo/api:dev ./app/api
docker build -t devops-dojo/frontend:dev ./app/frontend
kind load docker-image devops-dojo/api:dev devops-dojo/frontend:dev

kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
kubectl apply -f deploy/k8s/base/

kubectl -n devops-dojo get pods,svc,ingress
```

Open <http://localhost/> and <http://localhost/api/steps>.

## How it works

The manifests in [deploy/k8s/base/](../../deploy/k8s/base/) mirror the Compose stack: Postgres
is a **StatefulSet** with a PVC, Redis/api/worker/frontend are **Deployments** + **Services**,
migrations run as a **Job** (SQL supplied by the `dojo-migrations` ConfigMap), and an
**Ingress** routes `/api`→api and `/`→frontend. The API's `livenessProbe`/`readinessProbe`
hit `/healthz` and `/readyz` — the same split from lab 08, now driving K8s scheduling.

## Exercise

Watch Kubernetes self-heal and scale:

```powershell
kubectl -n devops-dojo delete pod -l app=api    # K8s recreates it immediately
kubectl -n devops-dojo scale deploy/api --replicas=4
kubectl -n devops-dojo get pods -l app=api -w
```

Then apply the HPA (`deploy/k8s/base/hpa.yaml`, needs metrics-server — see the k8s README) and
drive load to watch it scale automatically.

## Checkpoint

- ✅ `kubectl -n devops-dojo get pods` shows api/frontend/worker/redis Running and db Ready.
- ✅ <http://localhost/api/steps> returns the 24 steps through the Ingress.
- ✅ Deleting an API pod recreates it; scaling changes replica count.

## Common failures

- Pods `ImagePullBackOff` → you didn't `kind load docker-image` (or the tag differs from
  `devops-dojo/api:dev`).
- `migrate` Job failing → the `dojo-migrations` ConfigMap wasn't created before applying.
- Ingress 404 → the ingress-nginx controller isn't ready yet.

Teardown: `kind delete cluster`.

➡️ Next: [Lab 23 — Helm packaging](../23-helm/)
