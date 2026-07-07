# Operator Lab 05 — RBAC & in-cluster deploy

**Maps to:** deepens labs 02/27 · **Project:** dojo-operator · **Platform**

**Run from:** the [`dojo-operator/`](../../) folder.

## Concept

So far the operator ran on your laptop with *your* kubeconfig — cluster-admin,
in practice. Real operators run **in** the cluster as a Deployment with a
**ServiceAccount** whose permissions are exactly what the reconciler calls and
nothing more. Lab 27 gave a human least privilege; today you do it for
software, and prove the most interesting negative: **the operator that manages
database backups cannot read the database password.** It only wires a
`secretKeyRef` into the backup pod — the kubelet resolves the secret, never the
operator.

## What you'll do

Build the distroless operator image, load it into kind, deploy it with its
RBAC, and interrogate its permissions from the outside.

## Steps

```powershell
# 0. Stop the laptop operator (Ctrl+C in its terminal) — one brain at a time.

# 1. Build and load the image (same multi-stage/distroless recipe as app/api):
docker build -t devops-dojo/operator:dev .
kind load docker-image devops-dojo/operator:dev

# 2. Identity + permissions + workload:
kubectl apply -f config/rbac/rbac.yaml
kubectl apply -f config/manager/deployment.yaml
kubectl -n dojo-operator-system get pods
kubectl -n dojo-operator-system logs deploy/dojo-operator -f   # reconciles resume

# 3. Interrogate the ServiceAccount's permissions — the operator can…
kubectl auth can-i create cronjobs -n devops-dojo --as=system:serviceaccount:dojo-operator-system:dojo-operator     # yes
kubectl auth can-i update dojobackups/status -n devops-dojo --as=system:serviceaccount:dojo-operator-system:dojo-operator  # yes
# …and can NOT:
kubectl auth can-i get secrets -n devops-dojo --as=system:serviceaccount:dojo-operator-system:dojo-operator          # no  <- the point
kubectl auth can-i delete jobs -n devops-dojo --as=system:serviceaccount:dojo-operator-system:dojo-operator          # no (jobs are observe-only)
kubectl auth can-i delete persistentvolumeclaims -n devops-dojo --as=system:serviceaccount:dojo-operator-system:dojo-operator  # no (GC deletes, not us)

# 4. Prove it still works with the narrow role — fight the robot again:
kubectl -n devops-dojo delete cronjob dojo-db-backup
kubectl -n devops-dojo get cronjob      # resurrected, now by the in-cluster pod

# 5. The operator is a service like any other — probes + metrics (labs 08/10):
kubectl -n dojo-operator-system port-forward deploy/dojo-operator 8080:8080
# second terminal:
curl -s http://localhost:8080/metrics | findstr controller_runtime_reconcile_total
```

## How it works

In-cluster, `ctrl.GetConfigOrDie()` finds the ServiceAccount token that the
kubelet projected into the pod — same binary, different credentials, zero code
change. The [ClusterRole](../../config/rbac/rbac.yaml) is derived line-by-line
from what `Reconcile` actually calls (the `+kubebuilder:rbac` markers above it
in the controller source are the paper trail). If you add a `r.Delete(job)`
call tomorrow, the deploy breaks with `Forbidden` until you add the verb —
RBAC as a tripwire for scope creep. The metrics endpoint exposes
`controller_runtime_reconcile_total`, `..._errors_total` and work-queue depth —
what you'd alert on in production (a growing queue = a controller that can't
keep up; compare lab 12's alert design).

## Exercise

Two-part:
1. Delete one verb — remove `create` from the `cronjobs` rule, re-apply, delete
   the CronJob, and read the exact `Forbidden` error in the operator logs; put
   it back. (You'll meet this error in every operator postmortem of your career.)
2. Scale to `replicas: 2` and watch the logs: both pods reconcile (double
   writes!). Add `--leader-elect` to the args, re-apply, and confirm exactly
   one pod logs "became leader" and reconciles — why HA controllers need
   election.

## Checkpoint

- ✅ The in-cluster operator reconciles (step 4's resurrection).
- ✅ `auth can-i` shows yes for cronjobs/status, **no for secrets**, no for
  deleting jobs/PVCs.
- ✅ `/metrics` serves `controller_runtime_*` counters.
- ✅ You can explain how the same binary authenticates on a laptop vs in-cluster.

## Common failures

- `ImagePullBackOff` → you skipped `kind load docker-image` (kind can't pull
  local images from the daemon; loading is explicit).
- Pod runs but nothing reconciles → RBAC not applied; the log will be a wall of
  `Forbidden` — read one and see it names the missing group/resource/verb.
- Two reconcilers logging → you did step 2 with the laptop operator still
  running (also instructive: watch them not conflict — optimistic concurrency
  via resourceVersion rejects the loser's stale writes).

➡️ Next: [Operator Lab 06 — Tests & CI](../06-testing-and-ci/)
