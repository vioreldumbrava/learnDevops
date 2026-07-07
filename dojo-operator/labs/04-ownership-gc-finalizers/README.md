# Operator Lab 04 — Ownership, garbage collection & finalizers

**Maps to:** deepens labs 28/35 (stuck-Terminating drills) · **Project:** dojo-operator · **Platform**

**Run from:** the [`dojo-operator/`](../../) folder — operator from lab 02 still running.

## Concept

Two mechanisms govern the *death* of Kubernetes objects, and operators use both:

- **ownerReferences** → cascading **garbage collection**: delete the parent and
  the cluster deletes the children. You never write cleanup code for owned
  objects — you declare ownership at creation.
- **Finalizers** → **pre-delete hooks**: while any finalizer string is on an
  object, deletion *pauses* (deletionTimestamp set, object stays). The owning
  controller finishes its cleanup, removes its finalizer, and only then does
  the object disappear. Every "namespace stuck in Terminating" incident you'll
  ever debug is a finalizer whose controller never came back to remove it.

## What you'll do

Trace the ownership chain, watch cascading GC, then manufacture — and correctly
fix — a resource stuck in Terminating.

## Steps

```powershell
# 1. The ownership chain, written in metadata (CR -> CronJob -> Job -> Pod):
kubectl -n devops-dojo get cronjob dojo-db-backup -o jsonpath="{.metadata.ownerReferences}"
#   kind: DojoBackup, name: dojo-db, controller: true

# 2. Cascading GC — delete the parent, count the orphans (there are none):
kubectl -n devops-dojo delete djb dojo-db
kubectl -n devops-dojo get cronjob,pvc,job
#   all gone: CronJob, PVC (and the dumps on it), Jobs — one delete, full cleanup

# 3. Put it back (reconciliation rebuilds everything from the one CR):
kubectl apply -f config/samples/backup.yaml
kubectl -n devops-dojo get cronjob,pvc

# 4. Now the finalizer drill. Make backups FAIL long enough to observe:
kubectl -n devops-dojo scale statefulset db --replicas=0
kubectl -n devops-dojo create job --from=cronjob/dojo-db-backup stuck-drill
#   (pg_dump can't connect; the job retries -> stays active)

# 5. Delete the CR while its job is running:
kubectl -n devops-dojo delete djb dojo-db --wait=false
kubectl -n devops-dojo get djb dojo-db -o jsonpath="{.metadata.deletionTimestamp} {.metadata.finalizers}"
#   deletionTimestamp is SET, finalizer dojo.dev/backup-protection still there:
#   the object is Terminating — held by your controller, on purpose.
kubectl -n devops-dojo describe djb dojo-db | findstr DeletionBlocked

# 6. Fix it the RIGHT way — resolve the condition, don't rip the finalizer:
kubectl -n devops-dojo delete job stuck-drill
#   next reconcile: no active jobs -> controller removes its finalizer -> gone
kubectl -n devops-dojo get djb
#   No resources found.

# 7. Restore the world:
kubectl -n devops-dojo scale statefulset db --replicas=1
kubectl apply -f config/samples/backup.yaml
```

## How it works

`SetControllerReference` stamps the parent's identity into each child at
creation; the cluster's garbage collector does the rest (step 2). The finalizer
is added by the reconciler *before* it creates any children, so there is no
window where the CR can vanish uncleanly. On delete, `handleDeletion` counts
active Jobs: >0 → emit `DeletionBlocked` and requeue; 0 → `RemoveFinalizer` +
Update, and the API server completes the deletion. The escape hatch you'll be
tempted to use in real incidents —
`kubectl patch ... -p '{"metadata":{"finalizers":[]}}'` — skips the cleanup the
finalizer was protecting; it's a last resort for controllers that are *gone
forever*, not a fix. The fix is step 6: give the controller what it's waiting
for.

## Exercise

Design question (write the answer in your notes): the PVC is owner-referenced,
so deleting the CR deletes the *backups themselves*. Velero (lab 33) does NOT
do this with its backup storage. When is each choice right? What would you
change here to orphan the PVC instead? (Hint: create it without
`SetControllerReference`, and think about what "delete" should mean for data.)

## Checkpoint

- ✅ You showed the ownerReferences chain and a full cascading cleanup.
- ✅ You produced a real Terminating-stuck object and read its cause from
  `finalizers` + events.
- ✅ You fixed it by resolving the block — not by force-clearing metadata.

## Common failures

- Step 5 shows no finalizer → your operator wasn't running when you applied
  the CR (finalizers are added by the reconciler; without it there's no
  protection — re-apply with the operator up).
- The CR deletes instantly in step 5 → the drill job already failed its last
  retry (not "active" anymore); re-run steps 4–5 faster or scale db down first.
- PVC survives step 2 → you created it manually in an earlier experiment; only
  operator-created children carry the ownerReference.

➡️ Next: [Operator Lab 05 — RBAC & in-cluster deploy](../05-rbac-and-deploy/)
