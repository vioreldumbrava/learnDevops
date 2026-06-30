# DevOps Dojo — Step-by-Step Learning Guide

This is the master guide for learning DevOps by **building, running, and operating one real
application**: *DevOps Dojo*, a small 3‑tier web app (Go API + React frontend + Postgres +
Redis) whose subject is the very curriculum you're working through. You deploy the app that
tracks your progress.

The philosophy: don't learn Docker, then Compose, then Kubernetes as disconnected topics.
Instead, take one app and progressively add every layer a real production system needs —
packaging, orchestration, persistence, backups, health, caching, observability, delivery,
infrastructure, security, scaling, Kubernetes. Each concept is motivated by a concrete need
of *this* app.

> **Guide + Labs.** This document is the *narrative* — it teaches each concept and gives the
> essential commands. Each step links to a **lab** under [`labs/`](../labs/) that contains the
> full hands-on walkthrough with an **Exercise**, a **Checkpoint** (your pass/fail test), and
> **Common failures**. Work through the guide top to bottom; drop into the lab when you want
> to do it for real.
>
> New to the Linux shell (needed from Step 18, servers)? See
> [LINUX_FOR_CONTAINERS.md](LINUX_FOR_CONTAINERS.md).

---

## The application you'll operate

```
                 Browser
                    │
   (prod) :80/443   ▼
        ┌────────► Caddy ────────────┬──────────────► frontend  (React/Nginx; dev: Vite :5173)
        │  reverse proxy + auto-TLS  │
        │                            └──► /api/* ──►  api (Go) ──► Postgres  (db)   [stateful]
        │                                              │    └────► Redis     (cache + queue)
        │                                              │                ▲
        │                                              │             worker (Go)   [stateless]
        │   observability (separate overlay):          │
        │     /metrics ─► Prometheus ─► Grafana        │
        │     logs ─────► Promtail ───► Loki ─► Grafana │
        │     traces ───► Tempo ──────────────► Grafana │
        │     alerts ───► Alertmanager                  │
        └───────────────────────────────────────────────
```

| Tier | Tech | Teaches |
|------|------|---------|
| `frontend` | React + Vite + TS | image build phases, dev hot reload vs prod static serving |
| `api` | Go (`chi`, `pgx`) | tiny secure images, `/healthz` `/readyz` `/metrics`, tracing, JSON logs |
| `worker` | Go | background jobs, queues, **stateless** scaling |
| `db` | PostgreSQL | migrations, backups, **stateful** services, volumes |
| `redis` | Redis | caching + a job queue |
| `caddy` | Caddy | reverse proxy, automatic HTTPS |
| observability | Prometheus, Grafana, Loki, Promtail, Tempo, Alertmanager | the three pillars + alerting |

**Stateless vs stateful** is the backbone idea: `api`, `worker`, `frontend` are stateless
(run many copies freely — Steps 21–22); `db` and `redis` are stateful (need volumes and care
to scale). Keep that distinction in mind from Step 04 on.

---

## Prerequisites

- Docker Desktop (Linux containers) + Docker Compose v2 — verify: `docker version`, `docker compose version`
- PowerShell (commands below are written for it)
- Optional later: `kubectl` + `kind`, `helm`, `terraform`, `ansible`, `k6`. You do **not**
  need Go or Node installed — they run inside build containers.

You also need a local env file:

```powershell
copy .env.example .env
```

---

## Running it (the three stacks)

Commands run from the **repo root**. Compose is told where the files are with `-f`.
To keep commands short, set this once per terminal:

```powershell
$dc = "docker","compose","-f","deploy/compose/compose.yaml"
```

Then:

```powershell
# DEVELOPMENT — Vite hot reload at http://localhost:5173
& $dc -f deploy/compose/compose.dev.yaml up --build

# PRODUCTION-style — behind Caddy at http://localhost
& $dc -f deploy/compose/compose.prod.yaml --env-file .env up -d --build

# OBSERVABILITY overlay — adds Grafana http://localhost:3001 (admin/admin)
& $dc -f deploy/compose/compose.dev.yaml -f deploy/compose/compose.observability.yaml up -d --build
```

Stop and wipe data for a clean slate:

```powershell
& $dc down -v
```

> **Why `-f`?** Compose defaults to `compose.yaml` in the current folder. Ours lives under
> `deploy/compose/`, and we layer **overlays** (`compose.dev.yaml`, `compose.prod.yaml`,
> `compose.observability.yaml`) on top of the base. Files merge left → right.

---

## The learning path

Steps mirror the lab folders. ✅ = built & runnable now (Milestone 1). ⏳ = Milestone 2/3.

| # | Step | Lab | Status |
|---|------|-----|--------|
| 00 | Prerequisites & repo tour | [labs/00](../labs/00-prerequisites/) | ✅ |
| 01 | Docker basics: images, containers, layers | [labs/01](../labs/01-docker-basics/) | ✅ |
| 02 | Containerize the API: multi-stage, distroless, non-root | [labs/02](../labs/02-containerize-api/) | ✅ |
| 03 | Containerize the frontend | [labs/03](../labs/03-containerize-frontend/) | ✅ |
| 04 | Docker Compose: multi-service, DNS, volumes | [labs/04](../labs/04-docker-compose/) | ✅ |
| 05 | Dev/prod Compose separation | [labs/05](../labs/05-dev-prod-compose/) | ✅ |
| 06 | Database & migrations | [labs/06](../labs/06-database-migrations/) | ✅ |
| 07 | Backups & restore | [labs/07](../labs/07-backup-restore/) | ✅ |
| 08 | Health checks: liveness vs readiness | [labs/08](../labs/08-health-checks/) | ✅ |
| 09 | Cache + background worker (Redis queue) | [labs/09](../labs/09-cache-and-worker/) | ✅ |
| 10 | Monitoring: Prometheus + Grafana | [labs/10](../labs/10-monitoring/) | ✅ |
| 11 | Logging: Loki + Promtail | [labs/11](../labs/11-logging/) | ✅ |
| 12 | Tracing + Alerting | [labs/12](../labs/12-tracing-and-alerting/) | ✅ |
| 13 | Image registry: ghcr.io, tags, SBOM | labs/13 | ⏳ |
| 14 | Artifact repository | labs/14 | ⏳ |
| 15 | CI/CD with GitHub Actions | labs/15 | ⏳ |
| 16 | IaC: Terraform | labs/16 | ⏳ |
| 17 | Config management: Ansible | labs/17 | ⏳ |
| 18 | Deploy to VPS/EC2 + HTTPS | labs/18 | ⏳ |
| 19 | Security hardening | labs/19 | ⏳ |
| 20 | Load testing (k6) | labs/20 | ⏳ |
| 21 | Horizontal scaling | labs/21 | ⏳ |
| 22 | Kubernetes on kind | labs/22 | ⏳ |
| 23 | Helm packaging | labs/23 | ⏳ |

---

# Milestone 1 — Foundation (build & operate locally)

## Step 00 — Prerequisites & repo tour

**Concept.** DevOps = reliably shipping *and operating* software. Before touching it, know
your tools and where things live: app code in `app/` + `db/`, ops code in `deploy/`.

**Do.** `docker version`, `docker compose version`, `git init`, `copy .env.example .env`.

➡️ Full lab: [labs/00-prerequisites](../labs/00-prerequisites/)

## Step 01 — Docker basics: images, containers, layers

**Concept.** An **image** is a packaged read-only filesystem + start metadata. A **container**
is a running instance of it. A **layer** is one cached filesystem step from the Dockerfile.

**Why.** This is the unit of deployment for everything that follows.

**Do.**
```powershell
docker build -t devops-dojo/api ./app/api
docker run --rm -p 8080:8080 devops-dojo/api   # then: curl http://localhost:8080/healthz
docker history devops-dojo/api                 # see the layers
```

**Understand.** The image is built multi-stage, so the final layers are just a static binary
on a minimal base — no compiler shipped.

**Checkpoint.** Image is tens of MB; `/healthz` returns `{"status":"ok"}`.

➡️ Full lab: [labs/01-docker-basics](../labs/01-docker-basics/)

## Step 02 — Containerize the API: multi-stage, distroless, non-root

**Concept.** Production images should be small, secure, and cache-friendly: compile in a fat
stage, ship only the binary on a **distroless** base, run as a **non-root** user, and copy
`go.mod` before source so dependency layers stay cached.

**Why.** Smaller images deploy faster and have a far smaller attack surface (no shell, no
package manager for an attacker to use).

**Do.**
```powershell
docker images devops-dojo/api                                  # small
docker run --rm --entrypoint sh devops-dojo/api -c "whoami"     # FAILS: no shell (good!)
```

**Understand.** `gcr.io/distroless/static:nonroot` has no `/bin/sh`. `COPY` bakes code in;
a **bind mount** (`-v`) maps live host files in — used for dev hot reload in Step 05.

**Checkpoint.** The `sh` command fails; rebuilds reuse cached dependency layers.

➡️ Full lab: [labs/02-containerize-api](../labs/02-containerize-api/)

## Step 03 — Containerize the frontend

**Concept.** A SPA has a **build** phase (Node/Vite compiles React → static files) and a
**serve** phase (Nginx hands them to browsers). Multi-stage keeps Node out of the final image.

**Do.**
```powershell
docker build -t devops-dojo/frontend ./app/frontend
docker run --rm -p 3000:80 devops-dojo/frontend   # open http://localhost:3000
```

**Understand.** Standalone (no API), the page loads but shows "Couldn't reach the API" —
proof the tiers are independent containers.

**Checkpoint.** `http://localhost:3000` renders; `curl .../healthz` returns `ok`.

➡️ Full lab: [labs/03-containerize-frontend](../labs/03-containerize-frontend/)

## Step 04 — Docker Compose: multi-service, DNS, volumes

**Concept.** Real apps are several containers that must start in order and talk to each other.
Compose declares them once: shared network with **service-name DNS**, **volumes** for
persistence, `depends_on` for ordering, and one-shot jobs (migrations) that finish first.

**Why.** This is how you run the whole system with a single command.

**Do.**
```powershell
& $dc up -d --build
& $dc ps                 # db healthy -> migrate exits 0 -> api/worker/frontend start
& $dc exec db psql -U dojo -d dojo -c "select count(*) from steps;"
# open http://localhost:3000, tick a lab, reload -> it persists
```

**Understand.** The API reaches Postgres at `db:5432` purely by service name. `db-data` /
`redis-data` volumes survive `down`; `down -v` deletes them.

**Checkpoint.** `/api/steps` returns 24 steps; toggling a lab persists across reload.

➡️ Full lab: [labs/04-docker-compose](../labs/04-docker-compose/)

## Step 05 — Dev/prod Compose separation

**Concept.** Same app, different config. **Overlays** layer dev (hot reload, exposed DBs) or
prod (Caddy, restart policies, single public entrypoint) on top of the base.

**Do.**
```powershell
& $dc -f deploy/compose/compose.dev.yaml up --build          # 5173, edit App.tsx -> instant reload
& $dc -f deploy/compose/compose.prod.yaml --env-file .env up -d --build   # http://localhost via Caddy
```

**Understand.** App host ports bind to `127.0.0.1`, so on a server only Caddy (80/443) is
public; Caddy reaches the app by service name. `!override`/`!reset` tags replace inherited
values instead of merging.

**Checkpoint.** Dev hot-reloads at :5173; prod serves via Caddy at :80.

➡️ Full lab: [labs/05-dev-prod-compose](../labs/05-dev-prod-compose/)

## Step 06 — Database & migrations

**Concept.** Evolve schema in **versioned, repeatable** steps with a migration tool
(golang-migrate), not by hand-editing a live DB. A one-shot `migrate` service applies ordered
`.up.sql` files and records the version.

**Do.**
```powershell
& $dc up -d db
& $dc run --rm migrate
& $dc exec db psql -U dojo -d dojo -c "select * from schema_migrations;"
```

**Understand.** Re-running `up` is a no-op (idempotent), which is why the API can depend on it
every boot. Migrations live in [`db/migrations/`](../db/migrations/).

**Checkpoint.** `schema_migrations` shows the applied versions; `steps` has 24 rows.

➡️ Full lab: [labs/06-database-migrations](../labs/06-database-migrations/)

## Step 07 — Backups & restore

**Concept.** Containers are disposable; **data is not**. Back up to *outside* the DB
container (the host's `./backups/`) and prove a restore actually works.

**Do.**
```powershell
& $dc run --rm db-backup
& $dc run --rm -e BACKUP_FILE=dojo_YYYYmmdd_HHMMSS.sql db-restore
```

**Understand.** `db-backup`/`db-restore` are short-lived `postgres` containers (in the
`backup` profile, so they don't run on `up`). The dump on the host survives even `down -v`.

**Checkpoint.** Delete a row, restore, and watch it come back.

➡️ Full lab: [labs/07-backup-restore](../labs/07-backup-restore/)

## Step 08 — Health checks: liveness vs readiness

**Concept.** **Liveness** (`/healthz`) = "is the process alive?" (if not, restart).
**Readiness** (`/readyz`) = "can it serve *now*?" (checks DB+Redis; if not, stop sending
traffic but don't restart). Conflating them causes restart loops.

**Do.**
```powershell
& $dc stop db
curl http://localhost:8080/healthz       # still 200
curl -i http://localhost:8080/readyz      # 503, names the broken dependency
& $dc start db
```

**Understand.** Compose `depends_on: service_healthy` and Kubernetes liveness/readiness probes
(Step 22) use exactly this split. The distroless image's healthcheck is the binary itself
(`/api -healthcheck`).

**Checkpoint.** With `db` down: `/healthz`=200, `/readyz`=503.

➡️ Full lab: [labs/08-health-checks](../labs/08-health-checks/)

## Step 09 — Cache + background worker (Redis queue)

**Concept.** Redis as a **cache** (fast repeat reads; invalidate on change) and as a **queue**
(push work, a **stateless worker** processes it off the request path).

**Do.**
```powershell
curl -i http://localhost:8080/api/steps | Select-String "X-Cache"   # MISS then HIT
curl -X POST http://localhost:8080/api/progress/01-docker-basics -H "Content-Type: application/json" -d '{\"completed\":true}'
& $dc logs worker                                                    # processing job ...
```

**Understand.** A progress change writes Postgres, deletes the cache key, and enqueues a job
on `dojo:jobs`; the `worker` (same image, `/worker` entrypoint) consumes it. Because it's
stateless, you can run many — the seed of horizontal scaling (Step 21).

**Checkpoint.** Second `/api/steps` is a cache HIT; the worker logs a processed job.

➡️ Full lab: [labs/09-cache-and-worker](../labs/09-cache-and-worker/)

## Step 10 — Monitoring: Prometheus + Grafana

**Concept.** **Metrics** are cheap numeric time-series. **Prometheus** scrapes a `/metrics`
endpoint; **Grafana** visualizes it; a **blackbox exporter** probes endpoints that don't
expose metrics. The API exposes *real* metrics, so this is genuine monitoring.

**Do.**
```powershell
& $dc -f deploy/compose/compose.observability.yaml up -d --build
curl http://localhost:8080/metrics
# Prometheus http://localhost:9090 (Targets), Grafana http://localhost:3001 (dashboard)
```

**Checkpoint.** Prometheus shows the `dojo-api` target UP; the Grafana dashboard shows request
rate and p95 latency.

➡️ Full lab: [labs/10-monitoring](../labs/10-monitoring/)

## Step 11 — Logging: Loki + Promtail

**Concept.** The second pillar: centralize logs. **Promtail** discovers containers and ships
their stdout to **Loki**; query with LogQL in Grafana. Structured (JSON) logs make filtering
by service/status trivial.

**Do.** In Grafana → Explore → Loki:
```logql
{compose_service="api"} | json | status >= 400
```

**Checkpoint.** You can isolate the API's error responses from its logs.

➡️ Full lab: [labs/11-logging](../labs/11-logging/)

## Step 12 — Tracing + Alerting

**Concept.** The third pillar: a **trace** follows one request as a tree of **spans**
(OpenTelemetry → Tempo), showing where time went. **Alerting**: Prometheus evaluates rules and
pushes firing alerts to **Alertmanager**.

**Do.** Generate traffic, then Grafana → Explore → Tempo → open a trace (the request span has
a nested `store.*` DB span). Stop the API to fire the `ApiDown` alert; see it on
`http://localhost:9090/alerts` and `http://localhost:9093`.

**Checkpoint.** A trace shows the nested DB span; `ApiDown` transitions to Firing. You now have
all three pillars + alerts in one Grafana.

➡️ Full lab: [labs/12-tracing-and-alerting](../labs/12-tracing-and-alerting/)

---

# Milestone 2 — Delivery & infrastructure ⏳

These steps are designed and on the roadmap; the labs land in Milestone 2.

## Step 13 — Image registry (ghcr.io, tags, SBOM)
Push versioned images to GitHub Container Registry so deployments pull a known artifact rather
than rebuilding from source. Tag by git SHA + semver; generate an SBOM for provenance.

## Step 14 — Artifact repository
Store build outputs (images, archives) in a repository manager (Artifactory/Nexus) with repo
types, retention, and permissions — what teams use beyond a plain file server.

## Step 15 — CI/CD with GitHub Actions
On every push: build images, run `go test` + the frontend build, scan with Trivy, push to
ghcr, and (optionally) deploy. The single most important automation in DevOps.

## Step 16 — Infrastructure as Code: Terraform
Provision the VPS/EC2 (instance, security group, DNS) **from code** so the environment is
reproducible and reviewable, not hand-clicked.

## Step 17 — Configuration management: Ansible
Configure the freshly provisioned server (install Docker, lay down `.env`, pull images, start
the stack) repeatably — replacing the manual SSH steps.

---

# Milestone 3 — Cloud, scale & Kubernetes ⏳

## Step 18 — Deploy to VPS/EC2 with HTTPS
Put the prod stack on a real server behind Caddy with automatic Let's Encrypt TLS. (Reuses the
existing `devDockerKey.pem`; only ports 22/80/443 open, with 22 limited to your IP.)

## Step 19 — Security hardening
Run non-root, `no-new-privileges`, read-only filesystems, dropped capabilities, real secrets
management, image scanning (Trivy/Docker Scout), and keep DB ports off the public internet.

## Step 20 — Load testing (k6)
Drive load and read the thresholds that matter (`http_req_failed`, p95 latency) so you know
capacity before users find the limit.

## Step 21 — Horizontal scaling
Run multiple **stateless** `api`/`worker` replicas behind Caddy; understand why `db`/`redis`
can't be scaled the same way.

## Step 22 — Kubernetes on kind
Move the stack to a local Kubernetes cluster: Deployments, Services, Ingress, ConfigMap/Secret,
a StatefulSet for Postgres, a Job for migrations, and an HPA. Map Compose concepts → K8s
objects (service → Deployment, volume → PVC, env → ConfigMap/Secret, Caddy → Ingress).

## Step 23 — Helm packaging
Package the manifests as a reusable, parameterized Helm chart — one `helm install` per
environment.

---

## Troubleshooting

**Rebuild from scratch (ignore cache):**
```powershell
docker build --no-cache -t devops-dojo/api ./app/api
docker build --no-cache -t devops-dojo/frontend ./app/frontend
```

**Fresh start (wipe containers + volumes):**
```powershell
& $dc -f deploy/compose/compose.dev.yaml -f deploy/compose/compose.observability.yaml down -v --remove-orphans
```

**Port already in use** — find the owner and change the published port in the relevant compose
file:
```powershell
docker ps --format "table {{.Names}}\t{{.Ports}}"
```
Ports used locally: 3000 (frontend), 5173 (dev vite), 8080 (api), 3001 (Grafana),
9090 (Prometheus), 9093 (Alertmanager), 3100 (Loki), 3200 (Tempo), 9115 (blackbox),
80/443 (Caddy, prod).

**Validate a stack before running it:**
```powershell
& $dc -f deploy/compose/compose.dev.yaml config
```

**Windows bind mounts** — if a bind mount fails, confirm Docker Desktop can access the drive
(Settings → Resources → File sharing).

---

## Where to go next

- Brand new? Start at [Step 00](../labs/00-prerequisites/) and work down.
- Want the at-a-glance roadmap with progress? See [CURRICULUM.md](CURRICULUM.md) — or just run
  the app, which *is* the roadmap.
- Each lab's **Checkpoint** is your proof you understood the concept well enough to apply it.
