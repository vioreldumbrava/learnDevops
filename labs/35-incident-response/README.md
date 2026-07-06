# Lab 35 — Incident response: break-fix drills

**Maps to:** extra · **Milestone:** 4 — Operate & Automate · **SRE**

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Every DevOps interview has a round of *"production is broken — what do you do?"*, and every
real job has a pager. What's being graded is not the fix but the **method**: a calm, repeatable
diagnosis loop, spoken out loud. This lab makes you practice that loop by deliberately breaking
the stack you built in lab 22 — eight times, eight different ways — and recovering it.

The loop (memorize it, say it in interviews):

```powershell
kubectl -n devops-dojo get pods -o wide                                  # 1. what is broken?
kubectl -n devops-dojo describe pod <pod>                                # 2. events — why?
kubectl -n devops-dojo logs <pod> --previous                             # 3. the app's story
kubectl -n devops-dojo get endpoints                                     # 4. is traffic routable?
kubectl -n devops-dojo get events --sort-by=.lastTimestamp               # 5. what changed?
```

Two artifacts make this professional instead of heroic: **runbooks** (what to do *before* you
panic — see [docs/runbooks/](../../docs/runbooks/)) and **postmortems** (what you learn *after*
— see [docs/postmortem-template.md](../../docs/postmortem-template.md)).

## What you'll do

Run the stack on kind (lab 22 setup), then for each drill: **inject → observe symptoms →
diagnose with the loop → fix → state the prevention**. Do them in order; each teaches a
different failure signature. Each drill also has a one-command injector in
[scripts/chaos/](../../scripts/chaos/) (bash — run from WSL or Git Bash).

Prerequisite: the lab 22 stack is up (`kind` cluster, images loaded, `deploy/k8s/base/`
applied) and <http://localhost/api/steps> works.

## Steps

### Drill 1 — CrashLoopBackOff (broken startup)

```powershell
# Inject: point the container at a binary that doesn't exist
kubectl -n devops-dojo patch deploy api --type json -p '[{"op":"add","path":"/spec/template/spec/containers/0/command","value":["/does-not-exist"]}]'
```

- **Symptoms:** new pods flap `StartError` → `CrashLoopBackOff`; the site still works
  (old ReplicaSet keeps serving — that's the rolling update protecting you).
- **Diagnose:** `describe pod` → Events say `exec: "/does-not-exist": no such file or
  directory`; `logs --previous` would show the last crash's output if the process had started.
- **Fix:** `kubectl -n devops-dojo rollout undo deploy/api` — every bad change in this lab that
  touched the pod template is one `rollout undo` away. Verify: `kubectl -n devops-dojo rollout status deploy/api`.
- **Prevent:** CI runs the image before publishing (lab 15); canary rollouts abort bad
  revisions before 100% (lab 32).

### Drill 2 — OOMKilled

```powershell
# Inject: starve the API of memory (Go runtime can't start in 8Mi)
kubectl -n devops-dojo patch deploy api --type json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources/requests/memory","value":"8Mi"},{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"8Mi"}]'
```

- **Symptoms:** restarts climbing; `describe pod` shows `Last State: Terminated — Reason:
  OOMKilled, Exit Code: 137`.
- **Diagnose:** 137 = SIGKILL from the kernel's OOM killer, not an app bug — the logs end
  mid-flight with no error, which is itself the clue.
- **Fix:** `kubectl -n devops-dojo rollout undo deploy/api`.
- **Prevent:** size requests/limits from real load tests (lab 20); alert on
  `container_memory_working_set_bytes` near the limit (labs 12/34).

### Drill 3 — Readiness cascade (dependency down)

```powershell
# Inject: take Postgres away
kubectl -n devops-dojo scale statefulset/db --replicas=0
```

- **Symptoms:** API pods show `Running` but `0/1 Ready`; `kubectl -n devops-dojo get endpoints api`
  is empty; the dashboard loads (frontend is fine) but every API call fails.
- **Diagnose:** `describe pod` → `Readiness probe failed`; `/readyz` pings Postgres (lab 08) so
  the pods pulled themselves out of the Service *without restarting* — exactly the
  liveness-vs-readiness split. If liveness checked the DB, you'd see restart loops on top of a
  DB outage.
- **Fix:** `kubectl -n devops-dojo scale statefulset/db --replicas=1` and watch endpoints refill.
- **Prevent:** liveness must never depend on downstreams; alert on `kube_deployment_status_replicas_available` (lab 34).

### Drill 4 — Service selector mismatch (the silent one)

```powershell
# Inject: one-letter typo in the Service selector
kubectl -n devops-dojo patch svc api -p '{"spec":{"selector":{"app":"apy"}}}'
```

- **Symptoms:** *everything is green* — pods Running and Ready — yet `/api/steps` times out
  with 502/504. This is the interview classic because `get pods` looks perfect.
- **Diagnose:** step 4 of the loop: `kubectl -n devops-dojo get endpoints api` → `<none>`.
  Compare `kubectl -n devops-dojo get svc api -o jsonpath='{.spec.selector}'` with the pod
  labels. No endpoints = the Service matches nothing.
- **Fix:** `kubectl -n devops-dojo patch svc api -p '{"spec":{"selector":{"app":"api"}}}'`
- **Prevent:** don't hand-edit live objects — in the GitOps capstone (lab 25) ArgoCD would
  revert this drift automatically within minutes.

### Drill 5 — ImagePullBackOff (bad rollout that can't even start)

```powershell
# Inject: deploy a tag that exists nowhere
kubectl -n devops-dojo set image deploy/api api=devops-dojo/api:v9.9.9
```

- **Symptoms:** new pods `ErrImagePull` → `ImagePullBackOff`; `kubectl rollout status` hangs;
  old pods keep serving traffic.
- **Diagnose:** `describe pod` → pull error (not in the local kind images, not in any
  registry). On kind, remember lab 22: local images must be `kind load docker-image`-ed.
- **Fix:** `kubectl -n devops-dojo rollout undo deploy/api`.
- **Prevent:** only deploy tags CI actually published (lab 15); prefer digests over mutable
  tags (lab 13); progressive delivery halts a rollout that never goes Ready (lab 32).

### Drill 6 — Bad migration (and the dirty-state trap)

```powershell
# Inject: add a broken migration (do NOT commit it), rebuild the ConfigMap, re-run the Job
'SELEC 1;' | Out-File -Encoding ascii db/migrations/000099_break.up.sql
'SELECT 1;' | Out-File -Encoding ascii db/migrations/000099_break.down.sql
kubectl -n devops-dojo delete configmap dojo-migrations
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
kubectl -n devops-dojo delete job migrate
kubectl apply -f deploy/k8s/base/migrate-job.yaml
```

- **Symptoms:** `kubectl -n devops-dojo get jobs` shows `migrate` retrying/failing;
  `kubectl -n devops-dojo logs job/migrate` shows the SQL syntax error. The app keeps running —
  the failed migration rolled back.
- **Diagnose:** the trap is what's *left behind*: golang-migrate marked the schema **dirty**:
  `kubectl -n devops-dojo exec db-0 -- psql -U dojo -d dojo -c "SELECT * FROM schema_migrations;"`
  → `version=99, dirty=t`. Re-running now refuses with `Dirty database version 99`.
- **Fix:** remove the bad files, reset the version, rebuild, re-run:

  ```powershell
  Remove-Item db/migrations/000099_break.*.sql
  kubectl -n devops-dojo exec db-0 -- psql -U dojo -d dojo -c "UPDATE schema_migrations SET version = 2, dirty = false;"
  kubectl -n devops-dojo delete configmap dojo-migrations; kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
  kubectl -n devops-dojo delete job migrate; kubectl apply -f deploy/k8s/base/migrate-job.yaml
  kubectl -n devops-dojo logs job/migrate -f    # "no change"
  ```

- **Prevent:** migrations reviewed + run in CI against a scratch DB before they reach an
  environment; take a backup before schema changes (lab 07 / runbook `db-restore`).

### Drill 7 — Database rejects writes (the disk-full signature, safely)

A full data disk puts Postgres into an effectively read-only state: the site *reads* fine and
probes pass, but every write 500s. Actually filling the disk on kind would hurt the whole node
(hostpath PVCs don't enforce size), so simulate the same failure mode directly:

```powershell
# Inject
kubectl -n devops-dojo exec db-0 -- psql -U dojo -d dojo -c "ALTER SYSTEM SET default_transaction_read_only = on; SELECT pg_reload_conf();"
```

- **Symptoms:** dashboard loads, `/readyz` is green (it only checks connectivity) — but
  toggling a step fails. A *partial* outage: the hardest kind to spot from probes alone.
- **Diagnose:** API logs (`kubectl -n devops-dojo logs deploy/api`, or Loki in lab 11) show
  `cannot execute INSERT in a read-only transaction`. Confirm on the DB:
  `kubectl -n devops-dojo exec db-0 -- psql -U dojo -d dojo -c "SHOW default_transaction_read_only;"`
- **Fix:** `kubectl -n devops-dojo exec db-0 -- psql -U dojo -d dojo -c "ALTER SYSTEM RESET default_transaction_read_only; SELECT pg_reload_conf();"`
- **Prevent:** alert on disk usage *before* it's full (node exporter, lab 34); probes can't
  catch everything — you also need error-rate alerts on writes (lab 12).

### Drill 8 — Run one blind

Have someone (or a script — `scripts/chaos/roulette.sh` picks one at random) inject a fault
without telling you which. Start the timer, work the loop out loud, write down: time to
*detect*, time to *diagnose*, time to *fix*. That transcript is your interview story.

## How it works

Each drill maps to a distinct **failure signature** you can name from the first command:

| First observation | Signature | Drill |
|-------------------|-----------|-------|
| `CrashLoopBackOff`, exec error in events | broken image/config | 1 |
| Exit code 137, `OOMKilled` | resource starvation | 2 |
| `Running` but not `Ready` | dependency failure | 3 |
| All green, no endpoints | routing/selector bug | 4 |
| `ImagePullBackOff`, rollout stuck | bad artifact reference | 5 |
| Job failing, app fine | data-layer change gone wrong | 6 |
| Green probes, failing writes | partial/stateful outage | 7 |

Interviewers escalate through exactly these: they don't want the answer, they want to hear
*"pods are Ready but the Service has no endpoints, so I check the selector"*. The runbooks in
[docs/runbooks/](../../docs/runbooks/) capture the same diagnosis paths per *symptom* (as an
on-call engineer sees them), not per cause.

## Exercise

1. After drill 4 (or your blind run), write a postmortem using
   [docs/postmortem-template.md](../../docs/postmortem-template.md) — a worked example is in
   [docs/postmortems/](../../docs/postmortems/). Blameless, timeline, root cause, action items.
2. If you did lab 30 (cert-manager): delete the TLS secret it manages
   (`kubectl -n devops-dojo delete secret <cert-secret>`) and watch cert-manager reissue it —
   certificate expiry is the classic "it broke at 3am and nothing was deployed" incident.
3. Re-run drill 3 with the observability stack from lab 34 installed and find the moment of
   failure in Grafana *before* looking at kubectl — detection via dashboards is how real
   on-call works.

## Checkpoint

- ✅ You recovered all seven injected faults without recreating the cluster.
- ✅ From `get pods` + `get endpoints` output alone, you can name which signature you're
  looking at and say the next command out loud.
- ✅ You've written one postmortem and can walk someone through it in two minutes.

## Common failures

- Drill patches "stack up" → you forgot a `rollout undo` between drills. Check
  `kubectl -n devops-dojo rollout history deploy/api` and `kubectl -n devops-dojo get deploy api -o yaml`
  before the next drill; `scripts/chaos/heal.sh` resets everything.
- Drill 6 keeps failing after the fix → you rebuilt the ConfigMap but didn't delete the old
  Job (Jobs are immutable — delete and re-apply), or `schema_migrations` is still dirty.
- Drill 7 seems to do nothing → the setting applies to *new* transactions; retry the toggle in
  the UI, and confirm with `SHOW default_transaction_read_only;`.

➡️ Next: [Lab 36 — Multi-environment promotion](../36-multi-env-promotion/)
