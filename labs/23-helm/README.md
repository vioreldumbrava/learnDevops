# Lab 23 — Helm packaging

**Maps to:** extra (completes the K8s story) · **Milestone:** 3

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Applying a folder of raw manifests doesn't scale across environments — you'd copy-paste and
hand-edit image tags, replica counts, and domains. **Helm** packages the manifests as a
**chart** with a `values.yaml` you override per environment, and manages install/upgrade/
rollback as one versioned release.

## What you'll do

Install the same stack via the chart, override values, and upgrade/roll back.

## Steps

Prereqs: a kind cluster with ingress-nginx and the images loaded (lab 22, steps 1–3), plus
Helm installed.

```powershell
# The migrations ConfigMap is still supplied from the SQL files
kubectl create namespace devops-dojo
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/

# See what the chart renders (no cluster changes)
helm template dojo deploy/k8s/helm/devops-dojo

# Install
helm install dojo deploy/k8s/helm/devops-dojo -n devops-dojo

kubectl -n devops-dojo get pods,svc,ingress
```

Open <http://localhost/>. Then override and upgrade:

```powershell
helm upgrade dojo deploy/k8s/helm/devops-dojo -n devops-dojo `
  --set api.replicas=4 --set frontend.replicas=3

helm history dojo -n devops-dojo
helm rollback dojo 1 -n devops-dojo      # back to the first revision
```

Uninstall:

```powershell
helm uninstall dojo -n devops-dojo
```

## How it works

The chart under [deploy/k8s/helm/devops-dojo/](../../deploy/k8s/helm/devops-dojo/) has the
same resources as `k8s/base/`, but templated: images, replica counts, resources, ingress, and
HPA all come from [values.yaml](../../deploy/k8s/helm/devops-dojo/values.yaml). The Secret's
`DATABASE_URL` is assembled from the config/secret values. Migrations run as a Helm
**post-install/post-upgrade hook** (recreated each release, since Jobs are immutable).

## Exercise

Create a `prod-values.yaml` that sets `secrets.postgresPassword`, `api.replicas: 3`, and
`hpa.enabled: false`, then `helm upgrade dojo ... -f prod-values.yaml`. One chart, many
environments — that's the whole point of Helm.

## Checkpoint

- ✅ `helm template` renders all resources without error.
- ✅ `helm install` brings the app up; it serves at <http://localhost/>.
- ✅ `helm upgrade --set api.replicas=4` scales the API; `helm rollback` reverts it.

## Common failures

- `Error: INSTALLATION FAILED ... configmaps "dojo-migrations" not found` → create the
  ConfigMap from `db/migrations/` before installing.
- Image pull errors → load images into kind first (`kind load docker-image ...`).

🎉 That's the full path: from `docker build` to a Helm-managed Kubernetes deployment. See
[docs/CURRICULUM.md](../../docs/CURRICULUM.md) for the whole map and ideas to go further
(GitOps/ArgoCD, service mesh, multi-env promotion).
