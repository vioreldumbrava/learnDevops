# Operator Lab 02 — The reconcile loop

**Maps to:** the heart of the project · **Project:** dojo-operator · **Platform**

**Run from:** the [`dojo-operator/`](../../) folder — `cd dojo-operator` from the repo root. Needs Go 1.23+ installed.

## Concept

Controllers are **level-based, not edge-based**. The reconciler is never told
"the user changed the schedule" — it is handed a *name*, reads desired state
(the CR) and actual state (CronJob/PVC), and **converges** actual toward
desired. Written that way, one code path handles create, update, tampering,
restarts and missed events. This is the same mechanism ArgoCD used on your
deployments in lab 25 — self-heal is not a feature, it *is* reconciliation.

## What you'll do

Run the controller **on your laptop** against the kind cluster, watch it build
the children, then fight it — and lose.

## Steps

```powershell
# 1. Start the operator locally. It authenticates with YOUR kubeconfig —
#    that's why it works without any in-cluster RBAC (lab 05 changes that).
go run ./cmd
```

Leave it running; in a **second terminal** (also in `dojo-operator/`):

```powershell
# 2. The children appeared within seconds of the controller starting:
kubectl -n devops-dojo get cronjob,pvc
#    dojo-db-backup (schedule */2 * * * *) and dojo-db-backups (1Gi)

# 3. FIGHT THE ROBOT — delete its CronJob:
kubectl -n devops-dojo delete cronjob dojo-db-backup
kubectl -n devops-dojo get cronjob
#    ...it's back. Watch the first terminal: a Reconcile fired the moment the
#    delete happened (the controller WATCHES what it owns).

# 4. Tamper instead of delete — edit the schedule behind the operator's back:
kubectl -n devops-dojo patch cronjob dojo-db-backup --type merge -p '{\"spec\":{\"schedule\":\"0 0 1 1 *\"}}'
kubectl -n devops-dojo get cronjob dojo-db-backup -o jsonpath="{.spec.schedule}"
#    -> */2 * * * *   (converged back on the next reconcile)

# 5. Change DESIRED state the right way — through the CR:
kubectl -n devops-dojo patch djb dojo-db --type merge -p '{\"spec\":{\"schedule\":\"*/3 * * * *\"}}'
kubectl -n devops-dojo get cronjob dojo-db-backup -o jsonpath="{.spec.schedule}"
#    -> */3 * * * *   (spec is the ONLY input the robot obeys)
```

Stop the operator with `Ctrl+C` when done (or keep it running for lab 03).

## How it works

`SetupWithManager` declares two watch sources: `For(DojoBackup)` and
`Owns(CronJob)`. Both feed the same work queue with the same currency — a
namespace/name. `Reconcile` then does the whole job from scratch every time:
fetch CR → ensure PVC → `CreateOrUpdate` the CronJob from spec → write status.
`CreateOrUpdate` is the convergence primitive: it computes the desired object
and patches only if it differs. Steps 3 and 4 are literally the same code path
as step 5 — that's the elegance. Reads come from a local **cache** (informers),
so all this watching costs almost no API traffic. Read
[internal/controller/dojobackup_controller.go](../../internal/controller/dojobackup_controller.go)
alongside the log output — every step is annotated.

## Exercise

Kill the operator (`Ctrl+C`), delete the CronJob, confirm it stays gone (no
controller = no behavior — lab 01's lesson from the other side). Restart
`go run ./cmd` and confirm it comes back *without any event happening* — on
startup the controller lists everything it cares about and reconciles it all.
That's why missed events don't matter.

## Checkpoint

- ✅ Deleting the CronJob brings it back within seconds.
- ✅ Tampered fields snap back; changes via the CR stick.
- ✅ You can explain level-based vs edge-based and why ArgoCD's self-heal is
  the same mechanism.

## Common failures

- `go run` fails with auth errors → your kubeconfig context isn't the kind
  cluster: `kubectl config use-context kind-kind`.
- CronJob never appears → the CRD or sample from lab 01 isn't applied; check
  the operator log — it prints every reconcile and error.
- Patch commands fail in PowerShell → keep the `\"` escaping exactly as shown
  (PowerShell 5.1 strips bare inner quotes from native-command args).

➡️ Next: [Operator Lab 03 — Status, conditions & events](../03-status-conditions-events/)
