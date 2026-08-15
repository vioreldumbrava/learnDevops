# Closed-book drills

Every lab in this repo hands you a working reference. That's deliberate — it means a typo can't
strand you for hours. It also means the labs train **recognition**: you can read a Dockerfile and
nod. Interviews and the CKA test **recall**: you get a blank terminal and a clock.

This file is the other half. Every lab marked `drill_required` in the curriculum manifest has
a from-scratch task with a **time target** and a **pass test**. Electives may remain
reference-only. The rule is one line long:

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

## Common-core drills

These cover the [job-first common core](DOCKER_LEARNING_PATH.md#the-job-first-common-core).
Times assume you've done the lab at least once.

### Lab 00 — host and network diagnostic · target 12 min

From a WSL Bash terminal, prove the path to any HTTPS service in order: DNS (`dig` or
`nslookup`), listening/client sockets (`ss`), TCP+HTTP (`curl -v`), then certificate/SNI
(`openssl s_client`). For the local Dojo, identify the process listening on its published port
and repeat the HTTP step against `/healthz`.

**Pass:** you show evidence at each layer, name exactly where a fabricated bad hostname or
closed port fails, and explain DNS → TCP → TLS → HTTP without notes. Tool installation and
Docker startup are outside the timer.

### Lab 38 — Git recovery and diagnosis · target 15 min

In a disposable clone, create two branches with a real conflict, resolve it during rebase,
then use `git bisect` to locate a deliberately bad commit. Finish by recovering the pre-rebase
state from `git reflog` on a new safety branch.

**Pass:** history is clean, `bisect` names the injected commit, the safety branch points to the
old state, and you can explain why force-pushing a shared branch would be unsafe.

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

### Lab 37 — production-safe glue script · target 15 min

From an empty file, write a Bash health waiter with strict mode, validated arguments, a bounded
retry loop, meaningful exit codes and an `EXIT` trap. Run ShellCheck, then demonstrate both a
successful endpoint and a timeout. Parse its JSON result once with `jq`.

**Pass:** ShellCheck is clean, success returns 0, timeout is non-zero inside the configured
bound, cleanup runs on both paths, and no unquoted user-controlled variable remains.

### Lab 54 — Linux service and disk triage · target 15 min

On the local systemd container, diagnose a stopped unit from status+journal, prove which
process owns its port, then identify a deleted-but-open file that makes `df` and `du`
disagree. Restore the unit without rebooting the container.

**Pass:** the service is active, its endpoint responds, `lsof +L1` (or `/proc/*/fd`) identifies
the open inode, disk space returns after the owning process releases it, and you narrate each
hypothesis before changing state.

### Lab 39 — remote state, locking and OIDC plan · target 18 min

From a small Terraform root, configure an S3 backend with native lockfiles, initialize it,
show a second writer being rejected, and run a read-only CI plan using GitHub OIDC rather than
stored AWS keys. Extract one reusable resource into a module with a typed input and output.

**Pass:** state is remote and encrypted, locking is observed, the workflow has
`id-token: write` plus a scoped `role-to-assume`, no AWS access key secret is referenced, and
`fmt`, `validate`, `tflint` and the plan succeed.

### Lab 40 — AWS identity, audit and operations · target 20 min

Using the resources from lab 40, identify the caller, explain one IAM policy and its trust
policy, trace a private subnet's default route, retrieve one relevant CloudTrail event and one
CloudWatch alarm, then prove the backup workload accesses S3 through workload identity with no
static AWS key in a Secret.

**Pass:** every claim is backed by CLI output, the budget/cost allocation tag exists, the pod's
ServiceAccount maps to the intended role, an out-of-scope S3 action is denied, and you state
which Part A resources can be destroyed before the EKS-only Part B.

### Lab 17 — idempotent configuration · target 12 min

Write a minimal Ansible role that installs a package, renders a validated configuration,
notifies a handler and starts/enables a service. Run it twice against a disposable Linux host.

**Pass:** the first run changes the intended resources, the second reports `changed=0`, the
service answers its health check, and deliberately invalid template data fails before restart.

### Lab 18 — DNS-to-HTTPS deployment diagnosis · target 15 min

Against the lab server, prove DNS, TCP/443, TLS/SNI and HTTP in order with `dig`, `nc`/`ss`,
`openssl s_client` and `curl -v`. Temporarily stop the upstream app, distinguish the resulting
proxy error from a certificate or security-group failure, then restore it.

**Pass:** HTTPS returns successfully after recovery, ports 8080 and 5432 remain non-public,
the certificate matches the hostname, and the failure is localized to the correct layer before
you fix it.

### Lab 22 — Kubernetes, kubectl only · target 6 min

**No editing repository YAML files.** Using generators plus `kubectl apply -f -` and at most
`kubectl patch`/`edit`, produce a two-replica Deployment, Service, Gateway, HTTPRoute, and
liveness/readiness probes against a preinstalled GatewayClass.

**Pass:** traffic works through the Gateway/HTTPRoute; `kubectl delete pod` self-heals; `kubectl rollout
undo` reverts a bad image. Time starts when the cluster is up.

**This is the CKA drill.** If it takes more than 6 minutes, your generator reflexes are the
bottleneck, not your Kubernetes knowledge — see [TOOLBOX.md](TOOLBOX.md).

### Lab 23 — a chart from `helm create` · target 12 min

Scaffold a chart, strip it to what you actually need, and template: image repo/tag, replica
count, an optional HTTPRoute behind a boolean, and resources from values.

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

### Lab 48 — CKA internal mock · target 45 min

The lab's timed 10-task internal mock, on a cluster you created that morning. No repo access.

**Pass:** 8/10 inside 45 minutes, twice, on different weeks. That is the **booking gate**:
schedule the exam four to six weeks after the second pass.

### Lab 48 — CKA full simulator · target 120 min

Use the full simulator under its exam-like rules, including its allowed documentation and
scoring system. Do not substitute the shorter internal task set for this endurance check.

**Pass:** finish the 120-minute simulation and meet the simulator's published passing rule
before sitting the real exam.

---

## Required specialization drills

### Lab 11 — central log diagnosis · target 10 min

With Alloy, Loki and the app running, generate one success, one 4xx and one 5xx. Without opening
the supplied dashboard, write LogQL queries that isolate by service, status class and latency,
then pivot from one request ID to all related lines.

**Pass:** all three queries return only the intended records, the request-ID query reconstructs
the event, and you explain why high-cardinality values belong in log fields rather than labels.

### Lab 12 — trace an unknown slow handler · target 12 min

Instrument a small HTTP handler with a server span and nested dependency span, export it through
OTLP, then introduce a delay and locate it in Tempo without consulting the reference config.

**Pass:** one trace shows the parent/child relationship and delay in the correct span, trace ID
appears in the matching structured log, and you explain what the trace revealed that the log
alone did not.

### Lab 27 — least-privilege RBAC · target 8 min

Create a ServiceAccount, Role and RoleBinding that allow exactly `get`, `list` and `watch` on
pods in one namespace. Prove both allowed and denied operations with impersonation.

**Pass:** the three intended verbs are yes; deleting pods, reading Secrets and the same read in
another namespace are no; no ClusterRoleBinding was used.

### Lab 28 — default-deny recovery · target 10 min

Apply ingress+egress default-deny to the application namespace, observe the failure, then add
only the DNS, Gateway-to-frontend/API, API-to-Postgres/Redis and required return paths.

**Pass:** the app and readiness checks work, an unrelated test pod remains blocked, policy
selectors contain no accidental empty match, and each allow rule is justified aloud.

### Lab 52 — recover persistent data · target 12 min

Create a dynamically provisioned PVC, write a sentinel through a pod, delete/recreate the pod,
then demonstrate the effect of both `Delete` and `Retain` reclaim policies using disposable
claims.

**Pass:** the sentinel survives pod replacement, you recover the retained volume through a new
claim, the delete-policy volume is removed, and access mode versus actual multi-node capability
is explained correctly.

### Lab 53 — scheduling from events · target 10 min

Repair a pod with three independent scheduling faults: an impossible request, an unmatched
taint and an unsatisfied affinity rule. Use scheduler events before editing each fault, then
spread three replicas across available nodes.

**Pass:** the pod schedules, replicas satisfy the requested spread, no control-plane taint was
removed as a shortcut, and every change maps to the event that justified it.

### Lab 55 — prove a database performance fix · target 15 min

Given the seeded slow query, identify it through `pg_stat_statements`, explain its actual plan
and buffers, add the next available reversible index migration, then repeat the same measurement.

**Pass:** the migration is clean and reversible, the new plan uses the intended index, measured
latency or buffer work improves, and you name the index's write/storage cost.

### Lab 56 — SLO burn-rate rule · target 15 min

From a blank Prometheus rules file, define availability SLI/error-ratio recording rules and one
fast/slow multi-window burn-rate alert pair. Route the fast alert to paging and the slow alert
to a ticket receiver.

**Pass:** `promtool check rules` succeeds, a controlled failure fires the fast alert, recovery
clears the short window, and your arithmetic connects the SLO, error budget and burn rate.

## Optional reference tasks

These are useful transfer exercises, but the corresponding elective cards do not require a
timed drill unless you select them for a target role.

| Lab | From-scratch task |
|-----|-------------------|
| 09 | Build a cache-aside read path and queue producer/consumer; prove write invalidation. |
| 19 | Harden a container with read-only rootfs, dropped capabilities and no-new-privileges. |
| 20 | Write a load test with thresholds and find the VU count where p95 breaches. |
| 21 | Scale a stateless service behind a proxy and explain why the database cannot follow. |
| 29–34 | Reproduce only the controller/policy relevant to a role you are targeting. |
| 36 | Promote an image from staging to production as a PR and show history in Git. |
| 41 | Sign an image and make admission reject the unsigned one. |
| 42–47 | Translate the core outcome into the selected enterprise/cloud tool. |
| 49–51 | Trace or replace the data plane when a Platform role calls for that depth. |

---

## How to use this file

1. Filter the dashboard to your route; **Drill next** tells you which required lab is stalest.
2. Set a timer. Actually set it — an untimed drill is just reading.
3. Pass → tick **drilled closed-book** on the card. Fail → leave it, add
   `date | mode | duration | pass/fail | assistance | specific gap` to the card notes, and
   re-run the missed portion in the same week.
4. Anything you had to look up twice belongs in your own notes, not in a re-read of the lab.

The measure of progress here isn't the number of labs completed — it's how many are **drilled**
and how recently. Fifty completed labs and four drilled ones is a worse position than fifteen of
each, because the interview asks you to produce, not to recognise.
