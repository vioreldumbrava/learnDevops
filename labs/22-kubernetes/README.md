# Lab 22 — Kubernetes on kind with Gateway API

**Tier:** core · **Maps to:** original §20 · **Milestone:** delivery

**Run from:** the **repo root** (`learnDevops/`). Every command and path below is relative to it.

## Concept

Compose runs containers on one host; Kubernetes orchestrates workloads across a cluster with
self-healing, rolling updates, and declarative networking.

| Compose | Kubernetes |
|---------|------------|
| service | Deployment + Service |
| named volume | PersistentVolumeClaim / StatefulSet |
| `.env` / environment | ConfigMap + Secret |
| one-shot `migrate` | Job |
| Caddy / published ports | Gateway + HTTPRoute |
| `--scale` | replicas + HorizontalPodAutoscaler |

The supported route uses **Gateway API** and **Envoy Gateway v1.8.3**. The retired
ingress-nginx controller exists only under `deploy/k8s/legacy/` for a later migration
comparison; do not install it here.

## What you'll do

Create a kind cluster, install Envoy Gateway, deploy the stack, prove the Gateway is
programmed, and exercise self-healing and scaling.

## Steps

The annotated walkthrough is in
[`deploy/k8s/README.md`](../../deploy/k8s/README.md). The complete command path is:

```powershell
kind create cluster --config deploy/k8s/kind/kind-cluster.yaml

helm install eg oci://docker.io/envoyproxy/gateway-helm --version v1.8.3 `
  --namespace envoy-gateway-system --create-namespace
kubectl wait -n envoy-gateway-system --for=condition=Available `
  deployment/envoy-gateway --timeout=300s
kubectl apply -f deploy/k8s/gateway/gatewayclass.yaml

docker build -t devops-dojo/api:dev ./app/api
docker build -t devops-dojo/frontend:dev ./app/frontend
kind load docker-image devops-dojo/api:dev devops-dojo/frontend:dev

kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
kubectl apply -f deploy/k8s/base/

kubectl -n devops-dojo wait --for=condition=Available `
  deployment/api deployment/frontend --timeout=180s
kubectl -n devops-dojo wait --for=condition=Programmed gateway/dojo --timeout=180s
kubectl -n devops-dojo get pods,svc,gateway,httproute
curl.exe --fail http://localhost/api/steps
```

## How it works

The raw manifests mirror Compose: Postgres is a StatefulSet with a PVC;
Redis/API/worker/frontend are Deployments and Services; migrations run as a Job; and an
HTTPRoute sends `/api` and `/healthz` to the API while `/` goes to the frontend. The local
Gateway asks Envoy Gateway for a NodePort service on `30080`, which kind maps to host port
80. `Programmed=True` proves a controller accepted and configured the Gateway; the object
merely existing is not enough.

The namespace enforces the `restricted` Pod Security Standard. Workloads therefore run as
non-root where compatible, disallow privilege escalation, drop Linux capabilities, and use
the runtime-default seccomp profile. Inspect those settings rather than treating them as
decorative YAML:

```powershell
kubectl get namespace devops-dojo --show-labels
kubectl -n devops-dojo get deployment api -o yaml
```

## Exercise

Watch Kubernetes self-heal and scale:

```powershell
kubectl -n devops-dojo delete pod -l app=api
kubectl -n devops-dojo scale deploy/api --replicas=4
kubectl -n devops-dojo get pods -l app=api -w
```

Then apply the HPA (metrics-server setup is in the Kubernetes README) and drive load to see
the replica count change.

## Checkpoint

- API, frontend, worker, Redis, and Postgres are healthy.
- `gateway/dojo` reports `Programmed=True`, and its HTTPRoute has accepted/resolved refs.
- `/api/steps` returns the manifest-backed curriculum through the Gateway.
- Deleting an API pod recreates it; changing replicas changes the running pod count.
- The default namespace path passes the restricted Pod Security policy.

## Common failures

- `ImagePullBackOff` → load the exact image/tag into kind.
- Migration Job fails → create `dojo-migrations` before applying the workloads.
- Gateway never becomes Programmed → verify the `eg` GatewayClass and Envoy Gateway pods.
- Programmed but connection refused → check the generated Envoy service uses NodePort 30080
  and the kind port mapping matches it.
- Pod Security rejection → inspect the event and remediate the workload security context;
  do not remove the namespace policy to make the symptom disappear.

Teardown: `kind delete cluster`.

➡️ Next: [Lab 23 — Helm packaging](../23-helm/)
