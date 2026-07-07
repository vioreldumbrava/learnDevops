# Operator Lab 01 — CRDs: the API half

**Maps to:** deepens labs 22/27–34 · **Project:** dojo-operator · **Platform**

**Run from:** the [`dojo-operator/`](../../) folder — `cd dojo-operator` from the repo root.

## Concept

An operator is two halves: a **custom API type** (the CRD) and a **controller**
(the code). This lab installs ONLY the API half — and that's the lesson: a
CustomResourceDefinition teaches the API server a brand-new REST endpoint with
schema validation, `kubectl` support, RBAC-able verbs and etcd storage, *with
zero code running*. Every operator you've used (cert-manager's `Certificate`,
KEDA's `ScaledObject`, Argo's `Rollout`, Velero's `Schedule`) starts exactly
like this.

## What you'll do

Install the CRD, poke the new API with kubectl, watch the schema reject bad
input, apply a real DojoBackup — and observe that *nothing happens*.

## Steps

Prereq: your kind cluster with the Dojo deployed (lab 22), so `devops-dojo`
namespace, the `db` Service and `dojo-secrets` exist.

```powershell
# 1. Teach the API server a new type (this is ALL a CRD install is):
kubectl apply -f config/crd/dojo.dev_dojobackups.yaml

# 2. It's a real API now — discoverable, documented, kubectl-native:
kubectl api-resources | findstr dojo
kubectl explain dojobackup.spec           # docs generated from the schema
kubectl explain dojobackup.spec.database.passwordSecret

# 3. Schema validation happens at APPLY time, server-side — try garbage:
kubectl apply -f - <<'EOF'
apiVersion: dojo.dev/v1alpha1
kind: DojoBackup
metadata: { name: bad, namespace: devops-dojo }
spec: { schedule: 5, database: { host: db } }
EOF
# -> rejected: schedule wants a string, database is missing required fields

# 4. Apply the real one:
kubectl apply -f config/samples/backup.yaml
kubectl -n devops-dojo get djb            # shortName works; Ready column is empty
kubectl -n devops-dojo get dojobackup dojo-db -o yaml
```

Now look for the CronJob this is supposed to create:

```powershell
kubectl -n devops-dojo get cronjobs       # No resources found
```

**Nothing happened.** The object sits in etcd, validated and inert.

## How it works

`kubectl apply` of a CRD creates a row in the `customresourcedefinitions`
registry; the API server immediately starts serving
`/apis/dojo.dev/v1alpha1/namespaces/*/dojobackups` backed by etcd, enforcing
the `openAPIV3Schema` on every write (that's step 3's rejection — server-side,
before anything is stored). `kubectl explain`, printer columns and the `djb`
shortname all come from fields in the CRD. What does NOT exist yet is anything
that *watches* these objects — Kubernetes is a database with an API until a
controller gives a type behavior. Read
[config/crd/dojo.dev_dojobackups.yaml](../../config/crd/dojo.dev_dojobackups.yaml)
top to bottom; every stanza is annotated.

## Exercise

Add a printer column `Retention` (JSONPath `.spec.retention`) to the CRD,
re-apply it, and confirm `kubectl get djb` shows the new column. You've just
changed your API's UX with zero code.

## Checkpoint

- ✅ `kubectl explain dojobackup.spec` prints your field documentation.
- ✅ The garbage apply in step 3 is rejected with a schema error.
- ✅ `kubectl -n devops-dojo get djb` lists `dojo-db` — and no CronJob exists.
- ✅ You can say why: **a CRD is data + schema; behavior needs a controller.**

## Common failures

- `no matches for kind "DojoBackup"` → the CRD apply failed or you typo'd
  `apiVersion: dojo.dev/v1alpha1`.
- The step-3 apply *succeeds* → you're on an old cluster with structural schema
  validation off (kind ≥1.22 enforces it; recreate the cluster).
- `namespaces "devops-dojo" not found` → deploy the app first (lab 22).

➡️ Next: [Operator Lab 02 — The reconcile loop](../02-reconcile-loop/)
