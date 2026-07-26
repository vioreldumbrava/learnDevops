# Closed-book drills

Every lab in this repo hands you a working reference. That's deliberate — it means a typo can't
strand you for hours. It also means the labs train **recognition**: you can read a Dockerfile and
nod. Interviews and the CKA test **recall**: you get a blank terminal and a clock.

This file is the other half. Each drill is a from-scratch task with a **time target** and a
**pass test**. The rule is one line long:

> **The repo's answer files stay closed.** Work in a scratch directory. `man`, `--help`,
> `kubectl explain` and the official docs are allowed — that's what you get in the exam and at
> work. This repo's files, your old notes, and an AI assistant are not.

Mark a lab **drilled** in the dashboard only when it passes **inside** its time target. Miss the
target and it stays undrilled — that's the signal, not a failure. See
[WEEKLY.md](WEEKLY.md) for when to run these; the dashboard's *Drill next* panel picks which.

**Run these in bash (WSL), not PowerShell** — see [TOOLBOX.md](TOOLBOX.md). Every exam terminal
and every job you're applying for is bash.

```bash
mkdir -p ~/drills/$(date +%F) && cd ~/drills/$(date +%F)   # today's scratch dir
```

---

## Fast-track drills

These cover the [fast track](DOCKER_LEARNING_PATH.md#the-fast-track-interview-ready-as-soon-as-possible).
Times assume you've done the lab at least once.

### Lab 01/02 — build a production image · target 8 min

1. From an empty directory, write a `main.go` that serves `{"status":"ok"}` on `/healthz` at
   `:8080` (stdlib only, no modules beyond `go mod init`).
2. Write a multi-stage `Dockerfile`: a `golang` build stage producing a **static** binary, a
   **distroless nonroot** runtime stage, `EXPOSE 8080`, correct `ENTRYPOINT`.
3. Order the layers so a source-only change doesn't re-download dependencies.

**Pass:** `docker run --rm -p 8080:8080 IMG` → `curl localhost:8080/healthz` returns the JSON;
`docker run --rm --entrypoint sh IMG` **fails**; `docker images IMG` is under 20 MB; a second
build after editing only `main.go` reuses the `go mod download` layer (`CACHED` in the output).

**Say out loud while you work:** why `CGO_ENABLED=0`, why distroless over alpine, what you lose
(no shell to debug with — so what replaces `exec sh`?).

### Lab 03 — the SPA build/serve split · target 6 min

1. From scratch: a `Dockerfile` that builds any static site with Node in one stage and serves it
   from `nginx:alpine` in the next.
2. Add an nginx config that proxies `/api/` to `http://api:8080` and falls back to `index.html`
   for client-side routes.

**Pass:** the image contains no `node` binary (`docker run --rm --entrypoint sh IMG -c 'which node'`
is empty); the page loads on `:80`; a request to `/some/spa/route` returns the index, not a 404.

### Lab 04 — Compose from a blank file · target 12 min

Write `compose.yaml` from scratch with four services:

1. `db` — Postgres 16 with a **healthcheck** (`pg_isready`) and a named volume.
2. `migrate` — a one-shot that runs to completion.
3. `api` — depends on `db` `service_healthy` **and** `migrate` `service_completed_successfully`.
4. `frontend` — depends on `api`.

**Pass:** `docker compose up -d` → `docker compose ps` shows `migrate` as `Exited (0)` and the
rest healthy; the api reaches the db **by service name**; `docker compose down` keeps the data
and `down -v` destroys it — demonstrate both.

**Trap to avoid:** `depends_on` without a condition only waits for *start*, not for *ready*.

### Lab 05 — overlays · target 6 min

Split your lab-04 file into a base plus two overlays: dev (bind mount + hot reload + published
DB port) and prod (no published app ports, a reverse proxy, `restart: unless-stopped`).

**Pass:** `docker compose -f base.yaml -f dev.yaml config` and `... -f prod.yaml config` both
render, and you can point at the exact line in the merged output that came from the overlay.
Explain when merge isn't what you want and what replaces the inherited value instead.

### Lab 06 — a migration under pressure · target 8 min

1. Write a new `.up.sql`/`.down.sql` pair adding a column with a non-null default and an index.
2. Apply it with `migrate` against a running Postgres.
3. Roll it back. Apply it again.

**Pass:** `select * from schema_migrations;` shows the version; the down migration truly reverses
it; re-running `up` is a no-op. Explain why "idempotent" is what lets the api depend on it at
every boot, and what a `dirty` version means.

### Lab 07 — restore, not backup · target 10 min

1. `pg_dump` a running database to the host.
2. Delete a row you care about.
3. Restore and prove the row came back.

**Pass:** the row is back and you narrate why the dump living *outside* the container is the
whole point. Bonus: state what this procedure does **not** protect against (it's a full-restore,
not point-in-time — name what would give you PITR).

### Lab 08 — probes · target 6 min

Add to a service, from memory: an unconditional liveness endpoint, a readiness endpoint that
checks a dependency and returns **503** naming the broken one, and Compose healthchecks wired so
a dependent service waits.

**Pass:** stop the database → liveness still 200, readiness 503 with the dependency named, the
container is **not** restarted. Then say what the same split is called in Kubernetes and what
happens if you point liveness at the readiness logic.

### Lab 10 — metrics and PromQL · target 10 min

1. From scratch: a `prometheus.yml` scraping two targets, one of them a `/metrics` endpoint.
2. Write, without looking anything up:
   - request rate per second over 5 minutes,
   - the **error ratio** (5xx / all),
   - **p95** latency from a histogram.
3. Add one alert rule with a `for:` clause.

**Pass:** Prometheus shows both targets UP and all three expressions return data. Explain what
`rate()` does to a counter reset, and why `histogram_quantile` needs `sum by (le)`.

### Lab 13 — tags, digests, SBOM · target 6 min

Run a local registry, push an image under two tags, then **move** one tag to a different image.

**Pass:** you can show that the digest didn't move when the tag did, pull by digest, and state
in one sentence why production should deploy digests. Generate an SBOM and say what you'd do
with it.

### Lab 15 — a pipeline from a blank YAML · target 15 min

Write `.github/workflows/ci.yml` from scratch: a test job and a build job that only pushes on
non-PR events, with image tags derived from branch/SHA and a vulnerability scan that **fails**
the build on CRITICAL.

**Pass:** `act` or a pushed branch runs it green; a PR builds but does not push. Explain where
you'd put the build cache and why the scan runs against the digest, not the tag.

### Lab 16 — Terraform from a blank directory · target 12 min

From scratch: provider, a VM, a security group allowing SSH from **your IP only** plus 80/443,
an output for the public IP, and a variable with a validation rule.

**Pass:** `terraform validate` and `plan` are clean; a second `plan` after `apply` shows no
changes. Explain what's in state, why it's sensitive, and what `plan` can't detect.

### Lab 22 — Kubernetes, kubectl only · target 6 min

**No editing YAML files.** Using `kubectl create ... --dry-run=client -o yaml`, generators, and
at most `kubectl patch`/`edit`, produce: a Deployment with 2 replicas, a Service, an Ingress, and
liveness + readiness probes.

**Pass:** traffic works through the Ingress; `kubectl delete pod` self-heals; `kubectl rollout
undo` reverts a bad image. Time starts when the cluster is up.

**This is the CKA drill.** If it takes more than 6 minutes, your generator reflexes are the
bottleneck, not your Kubernetes knowledge — see [TOOLBOX.md](TOOLBOX.md).

### Lab 23 — a chart from `helm create` · target 12 min

Scaffold a chart, strip it to what you actually need, and template: image repo/tag, replica
count, an optional Ingress behind a boolean, and resources from values.

**Pass:** `helm template` renders clean YAML; `helm install` serves the app;
`helm upgrade --set replicas=4` scales it; `helm rollback` reverts. Explain what `helm rollback`
actually does and where the release history lives.

### Lab 25 — the capstone, spoken · target 10 min (no terminal)

Whiteboard the full path — commit → CI → registry → GitOps → cluster — naming every component,
then answer, unprompted:

- What does ArgoCD do that `kubectl apply` in CI doesn't?
- Where do the cluster credentials live in each model?
- How do you roll back? How do you roll back if Git is down?
- What's the blast radius when the ApplicationSet template is wrong?

**Pass:** ten minutes, no notes, no gaps. This is the interview, not a lab.

### Lab 26 — secrets · target 8 min

From scratch, make a chart consume a `Secret` **it does not create**, then populate that Secret
by an external mechanism.

**Pass:** `helm template --set secrets.create=false` renders no Secret; the workload still
starts; nothing plaintext is in Git. Explain the trade-off between Sealed Secrets and an
external secrets operator, and what each one does when the cluster is rebuilt from scratch.

### Lab 35 — blind incident · target 20 min

`scripts/chaos/roulette.sh` picks a failure you don't get to see. Narrate out loud:
**observe → hypothesize → verify → fix → confirm.**

**Pass:** root cause **and** fix inside 20 minutes, the method narrated as if someone were
watching your screen, and a three-line postmortem written afterwards
([template](postmortem-template.md)).

This is the only drill that gets *harder* as you get better at it — once the eight scripted
faults are familiar, combine two, or have the injector run while you're away from the keyboard.

### Lab 48 — CKA mock · target 120 min

The lab's timed 10-task mock exam, on a cluster you created that morning. No repo access.

**Pass:** 8/10 inside the time limit, twice, on different weeks.

---

## Beyond the fast track

These have no time target yet — write one the first time you run each, based on how long it
actually took, then hold yourself to it next time.

| Lab | The from-scratch task |
|-----|----------------------|
| 09 | A cache-aside read path and a queue producer/consumer, from an empty file. Prove the invalidation is correct on write. |
| 11 | Ship container logs to an aggregator and write three queries: by service, by status class, by latency threshold. |
| 12 | Instrument one handler with a nested span; explain what a trace shows that a log can't. |
| 17 | A playbook that installs a package, renders a templated config, and restarts a unit — idempotently. Prove `changed=0` on re-run. |
| 19 | Harden a container from memory: read-only rootfs, dropped capabilities, no-new-privileges, and the tmpfs mounts that keeps it working. |
| 20 | A load script with pass/fail thresholds, then find the VU count where p95 breaches. |
| 21 | Scale a stateless service behind a proxy; explain in one sentence why the database can't follow. |
| 27 | A ServiceAccount + Role + RoleBinding scoped to exactly three verbs; prove it with `auth can-i`. |
| 28 | Default-deny, then the minimum allows to make the app work again. |
| 36 | Promote an image tag from staging to prod as a PR; show the deploy history as `git log`. |
| 37 | A Bash script with strict mode, a trap, and argument validation; shellcheck-clean first try. |
| 39 | Remote state with locking, from a blank backend block. Then a module with inputs and outputs. |
| 41 | Sign an image and make admission reject the unsigned one. |
| 54 | A systemd unit + timer from memory; `systemd-analyze verify` clean. |
| 55 | Find the slow query, prove why with `EXPLAIN`, fix it, prove the fix. |
| 56 | A burn-rate alert from a blank rules file: recording rule, fast window, slow window. |

---

## How to use this file

1. The dashboard's **Drill next** panel tells you which lab is stalest.
2. Set a timer. Actually set it — an untimed drill is just reading.
3. Pass → tick **drilled closed-book** on the card. Fail → leave it, note *why* it failed in the
   lab's notes on the card, and re-run it in the same week.
4. Anything you had to look up twice belongs in your own notes, not in a re-read of the lab.

The measure of progress here isn't the number of labs completed — it's how many are **drilled**
and how recently. Fifty completed labs and four drilled ones is a worse position than fifteen of
each, because the interview asks you to produce, not to recognise.
