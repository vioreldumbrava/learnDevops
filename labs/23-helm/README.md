# Lab 23 — Helm packaging

**Tier:** core · **Milestone:** delivery

**Run from:** the **repo root** (`learnDevops/`). Every command and path below is relative to it.

## Concept

Copying raw manifests for each environment creates drift. Helm packages resources as a chart,
renders environment-specific values, and records releases so upgrades and rollbacks are
repeatable.

## What you'll do

Replace lab 22's raw deployment with the same stack managed by Helm, then perform and verify
an upgrade and rollback through Gateway API.

## Steps

Prerequisites: lab 22's kind cluster, the `eg` GatewayClass, locally loaded images, and Helm.
Start with a clean namespace so Helm does not try to adopt resources created by `kubectl`:

```powershell
kubectl delete namespace devops-dojo --wait=true
kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/

# Render first: this changes nothing in the cluster.
helm lint deploy/k8s/helm/devops-dojo
helm template dojo deploy/k8s/helm/devops-dojo --namespace devops-dojo > $null

helm install dojo deploy/k8s/helm/devops-dojo -n devops-dojo
kubectl -n devops-dojo wait --for=condition=Programmed gateway/dojo --timeout=180s
kubectl -n devops-dojo get pods,svc,gateway,httproute
curl.exe --fail http://localhost/api/steps
```

Upgrade and roll back:

```powershell
$firstRevision = helm history dojo -n devops-dojo -o json |
  ConvertFrom-Json | Select-Object -First 1 -ExpandProperty revision

helm upgrade dojo deploy/k8s/helm/devops-dojo -n devops-dojo `
  --set api.replicas=4 --set frontend.replicas=3
kubectl -n devops-dojo rollout status deployment/api --timeout=180s

helm history dojo -n devops-dojo
helm rollback dojo $firstRevision -n devops-dojo
kubectl -n devops-dojo rollout status deployment/api --timeout=180s
```

When finished, uninstall only the release; retain the cluster for later core labs:

```powershell
helm uninstall dojo -n devops-dojo
```

## How it works

The chart at [`deploy/k8s/helm/devops-dojo`](../../deploy/k8s/helm/devops-dojo/) templates
images, replicas, resources, Gateway/HTTPRoute, security contexts, and HPA. Migrations run as
a post-install/post-upgrade hook because Jobs are immutable. Gateway API is the default;
`ingress.enabled` is an explicitly historical migration option and requires a controller the
learner supplies separately.

## Exercise

Create a local values file that sets a non-default database password, three API replicas, and
`hpa.enabled: false`. Upgrade with `-f`, inspect `helm get values`, then roll back without
reading the walkthrough.

## Checkpoint

- `helm lint` and `helm template` succeed.
- The release serves `/api/steps` through a `Programmed=True` Gateway.
- The upgrade changes live replica counts and `helm rollback` restores the earlier values.
- Restricted workload-security settings are still present in rendered Deployments/Pods.

## Common failures

- Existing-resource ownership error → the lab 22 namespace was not removed before install.
- Missing `dojo-migrations` → recreate it from `db/migrations/` before installing.
- Image pull error → load the images into the kind nodes with the tags in `values.yaml`.
- Gateway unprogrammed → lab 22's Envoy Gateway installation or `eg` class is missing.

➡️ Next: [Lab 26 — Secrets management](../26-secrets-management/), with labs 35 and 25
scheduled later in the common core.
