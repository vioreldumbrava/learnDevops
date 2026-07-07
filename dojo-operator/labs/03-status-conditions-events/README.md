# Operator Lab 03 — Status, conditions & events

**Maps to:** deepens labs 08/35 · **Project:** dojo-operator · **Platform/SRE**

**Run from:** the [`dojo-operator/`](../../) folder — operator from lab 02 still running (`go run ./cmd`).

## Concept

`spec` is the user's half; **`status` is the controller's half** — its report of
what it observed. The API enforces the split via the **/status subresource**
(spec writes can't touch status and vice versa). Inside status, **conditions**
are the convention the whole ecosystem builds on: `kubectl wait`, ArgoCD health
checks, and your lab-35 debugging all read conditions. **Events** are the
complementary channel: timestamped breadcrumbs for humans in `kubectl describe`.
You've *consumed* all three since lab 08 — today your own software *produces*
them.

## What you'll do

Watch a real backup run land in status, use `kubectl wait` against your own
condition, trigger a manual backup, and read your controller's events.

## Steps

```powershell
# 1. Your CRD's printer columns come alive (wait ~2 min for the first run):
kubectl -n devops-dojo get djb
#   NAME      SCHEDULE      READY   LASTSUCCESS   AGE
#   dojo-db   */3 * * * *   True    45s           20m

# 2. The ecosystem contract — wait on YOUR condition like on any built-in:
kubectl -n devops-dojo wait --for=condition=Ready djb/dojo-db --timeout=60s

# 3. Read the full report your controller wrote:
kubectl -n devops-dojo get djb dojo-db -o jsonpath="{.status}" | ConvertFrom-Json | ConvertTo-Json -Depth 5
#   conditions[Ready], activeJobs, lastScheduleTime, lastSuccessfulTime,
#   observedGeneration

# 4. Trigger a backup NOW instead of waiting for cron (standard ops move):
kubectl -n devops-dojo create job --from=cronjob/dojo-db-backup manual-backup-1
kubectl -n devops-dojo wait --for=condition=complete job/manual-backup-1 --timeout=120s

# 5. Proof the backup is real — the job log shows the dump + the prune:
kubectl -n devops-dojo logs job/manual-backup-1
#   backup written: /backups/dojo_20260707_...sql
#   (and, once >3 dumps exist, "removed ..." lines: retention at work)

# 6. Events — your Recorder calls, in kubectl describe where humans look:
kubectl -n devops-dojo describe djb dojo-db
#   Events: Normal PVCCreated / Normal Reconciled ...
```

## How it works

`updateStatus` lists the Jobs owned by the CronJob, computes
`activeJobs`/`lastSuccessfulTime`, sets the `Ready` condition via
`meta.SetStatusCondition` (which maintains `lastTransitionTime` correctly — only
bumped on actual state *transitions*), and writes through `r.Status().Update` —
the subresource. `observedGeneration` is the staleness handshake: consumers
compare it to `metadata.generation` to know whether the status refers to the
spec they're looking at. Events go through the manager's `EventRecorder`, which
batches and dedupes (that's the `x2` counters in describe output).

## Exercise

Break the database reference on purpose: patch the CR's
`database.passwordSecret.key` to `WRONG_KEY`, trigger a manual job, and watch
where the failure shows up — job pod `CreateContainerConfigError` (the pod
can't resolve the secret key), `activeJobs` in status, events on describe. Then
fix it back. This is exactly the lab-35 diagnosis path, on your own resource.

## Checkpoint

- ✅ `kubectl get djb` shows Ready=True and a LastSuccess age.
- ✅ `kubectl wait --for=condition=Ready` returns immediately.
- ✅ The manual job's log shows a written dump (and prunes once >retention).
- ✅ You can explain why status needs its own subresource.

## Common failures

- Ready column empty → the operator isn't running (status is *written by the
  controller*, nothing else).
- Job fails with `password authentication failed` → `dojo-secrets` doesn't
  match the db's actual password (did you change the Helm values?).
- `lastSuccessfulTime` never moves → the CronJob is suspended, or the schedule
  hasn't fired yet — check `kubectl get cronjob` LAST SCHEDULE.

➡️ Next: [Operator Lab 04 — Ownership, GC & finalizers](../04-ownership-gc-finalizers/)
