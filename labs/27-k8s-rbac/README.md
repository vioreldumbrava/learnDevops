# Lab 27 — Kubernetes RBAC & least privilege

**Maps to:** deepens §17 · **Milestone:** K8s deep-dive · **Cert:** CKA/CKS

## Concept

**RBAC** controls *who* can do *what* in the cluster. The building blocks: a **ServiceAccount**
(identity for pods), a **Role**/**ClusterRole** (a set of allowed verbs on resources), and a
**RoleBinding**/**ClusterRoleBinding** (grants a Role to a subject). Least privilege means each
workload gets its own identity with **only** the access it needs — often *none*.

## What you'll do

Give the app a dedicated identity with no API access (and no mounted token), and grant a
separate read-only identity scoped to the namespace.

## Steps

```powershell
kubectl apply -f deploy/k8s/rbac/serviceaccounts.yaml
kubectl apply -f deploy/k8s/rbac/ops-readonly.yaml

# The app SA has no permissions — prove it (expect "no"):
kubectl auth can-i list secrets -n devops-dojo --as=system:serviceaccount:devops-dojo:dojo-api

# The ops-viewer SA can read pods but not delete them:
kubectl auth can-i list pods    -n devops-dojo --as=system:serviceaccount:devops-dojo:ops-viewer   # yes
kubectl auth can-i delete pods  -n devops-dojo --as=system:serviceaccount:devops-dojo:ops-viewer   # no

# Point the API at its SA and stop mounting the token:
kubectl -n devops-dojo patch deployment api --type=merge -p '{\"spec\":{\"template\":{\"spec\":{\"serviceAccountName\":\"dojo-api\",\"automountServiceAccountToken\":false}}}}'
```

## How it works

[serviceaccounts.yaml](../../deploy/k8s/rbac/serviceaccounts.yaml) creates `dojo-api` with
`automountServiceAccountToken: false` — the app never talks to the API server, so it shouldn't
carry a credential a compromised container could abuse. [ops-readonly.yaml](../../deploy/k8s/rbac/ops-readonly.yaml)
is the classic Role + RoleBinding: get/list/watch on common resources, scoped to one namespace.
`kubectl auth can-i --as=...` is the fastest way to test any RBAC grant.

## Exercise

Create a `ClusterRole`/`ClusterRoleBinding` that lets `ops-viewer` read nodes (a cluster-scoped
resource a namespaced Role can't grant), and confirm with `kubectl auth can-i list nodes --as=...`.
Notice *why* it must be a ClusterRole.

## Checkpoint

- ✅ `can-i list secrets` as `dojo-api` returns **no**.
- ✅ `ops-viewer` can list but not delete pods.
- ✅ The API runs with `serviceAccountName: dojo-api` and no mounted token.

## Common failures

- `can-i` returns "yes" unexpectedly → a broad ClusterRoleBinding (e.g. default `edit`/`admin`)
  is granting it; RBAC is additive and the widest grant wins.

➡️ Next: [Lab 28 — NetworkPolicies](../28-k8s-network-policies/)
