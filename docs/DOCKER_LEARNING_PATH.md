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
| 13 | Image registry: ghcr.io, tags, SBOM | [labs/13](../labs/13-image-registry/) | ✅ |
| 14 | Artifact repository | [labs/14](../labs/14-artifact-repository/) | ✅ |
| 15 | CI/CD with GitHub Actions | [labs/15](../labs/15-cicd/) | ✅ |
| 16 | IaC: Terraform | [labs/16](../labs/16-terraform/) | ✅ |
| 17 | Config management: Ansible | [labs/17](../labs/17-ansible/) | ✅ |
| 18 | Deploy to VPS/EC2 + HTTPS | [labs/18](../labs/18-deploy-https/) | ✅ |
| 19 | Security hardening | [labs/19](../labs/19-security/) | ✅ |
| 20 | Load testing (k6) | [labs/20](../labs/20-load-testing/) | ✅ |
| 21 | Horizontal scaling | [labs/21](../labs/21-scaling/) | ✅ |
| 22 | Kubernetes on kind | [labs/22](../labs/22-kubernetes/) | ✅ |
| 23 | Helm packaging | [labs/23](../labs/23-helm/) | ✅ |
| 24 | Self-hosted CI/CD with Jenkins (alt. to 15) | [labs/24](../labs/24-jenkins/) | ✅ |
| 25 | **Capstone:** EKS + GitOps (ArgoCD) | [labs/25](../labs/25-capstone-eks-gitops/) | ✅ |
| 26 | Production secrets management | [labs/26](../labs/26-secrets-management/) | ✅ |
| 27–34 | **Kubernetes deep-dive** (RBAC, NetworkPolicy, Kyverno, cert-manager, KEDA, Argo Rollouts, Velero, kube-prometheus-stack) | [labs/27–34](../labs/) | ✅ |

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

# Milestone 2 — Delivery & infrastructure

## Step 13 — Image registry: tags, push, SBOM

**Concept.** A **registry** stores/serves images. You **tag** (`repo:version`), `push`, and
`pull`. A tag is a movable label; a **digest** (`@sha256:…`) is immutable. An **SBOM** lists
what's inside an image.

**Why.** Servers should run a known, scanned artifact — not rebuild from source each time.

**Do.**
```powershell
docker run -d -p 5000:5000 --name registry registry:2
docker tag devops-dojo/api localhost:5000/dojo/api:0.1.0
docker push localhost:5000/dojo/api:0.1.0
docker scout quickview devops-dojo/api          # vulnerability summary
```

**Checkpoint.** Image pushed & pulled from a registry; you can explain tag vs digest.

➡️ Full lab: [labs/13-image-registry](../labs/13-image-registry/)

## Step 14 — Artifact repository (Nexus)

**Concept.** A repository manager (Nexus/Artifactory) stores *many* artifact types (images,
npm/Go packages, raw files) with users, permissions, retention, and upstream proxying — more
than a plain registry.

**Do.** (heavy; own overlay)
```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.nexus.yaml up -d nexus
# then create a hosted Docker repo in the UI (http://localhost:8081) and push to :8085
```

**Checkpoint.** You pushed an image (or raw artifact) into Nexus and added a retention policy.

➡️ Full lab: [labs/14-artifact-repository](../labs/14-artifact-repository/)

## Step 15 — CI/CD with GitHub Actions

**Concept.** **CI** runs build/test/scan on every change; **CD** publishes (and can deploy)
the result. It's the highest-value automation in DevOps.

**Why.** Turns "works on my machine" into "verified & shippable on every commit."

**Do.** Push to GitHub and watch the Actions tab; images land under Packages (GHCR).
```powershell
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin master
```

**Understand.** [.github/workflows/ci.yml](../.github/workflows/ci.yml): a **test** job
(`go vet`/`go test`, frontend build, compose validate, Trivy fs scan) and a **build** job
(Buildx build, metadata tags, SBOM + provenance, push to GHCR on non-PR, Trivy image scan).

**Checkpoint.** A green CI run; `api`/`frontend` images published; PRs build but don't push.

➡️ Full lab: [labs/15-cicd](../labs/15-cicd/)

## Step 16 — Infrastructure as Code: Terraform

**Concept.** Describe servers/networks/firewalls in version-controlled files. Terraform
`plan`s the change, then `apply`s it — reproducible and easy to destroy.

**Do.**
```powershell
cd deploy/terraform
copy terraform.tfvars.example terraform.tfvars   # set allowed_ssh_cidr (SSH key auto-generated)
terraform init; terraform plan; terraform apply
terraform output                                  # public_ip, ansible_inventory_line
```

**Understand.** IaC (Terraform) decides *what infrastructure exists*; config management
(Ansible, Step 17) decides *how it's configured*. State lives in `terraform.tfstate`
(gitignored, sensitive).

**Checkpoint.** `apply` yields a reachable instance; a second `plan` shows no changes. Run
`terraform destroy` when done.

➡️ Full lab: [labs/16-terraform](../labs/16-terraform/) ·
config: [deploy/terraform](../deploy/terraform/)

## Step 17 — Configuration management: Ansible

**Concept.** Install/configure software on the server **idempotently** over SSH — running
twice is safe and converges to the same state.

**Do.** (from a Linux/macOS/WSL control node)
```bash
cd deploy/ansible
cp inventory.ini.example inventory.ini    # paste Terraform's ansible_inventory_line
ansible dojo -m ping
ansible-playbook playbook.yml -e repo_url=https://github.com/<you>/<repo>.git \
  -e postgres_password=$(openssl rand -hex 16) -e site_domain=":80" -e acme_email=you@example.com
# open http://<server-ip>
```

**Understand.** [playbook.yml](../deploy/ansible/playbook.yml) installs Docker, clones the
repo, renders `.env`, and runs the prod compose stack — each task idempotent.

**Checkpoint.** `ansible-playbook` finishes with `failed=0`; the app serves on the server;
a re-run reports `changed=0` for unchanged tasks.

➡️ Full lab: [labs/17-ansible](../labs/17-ansible/) · config: [deploy/ansible](../deploy/ansible/)

## Step 24 — Self-hosted CI/CD with Jenkins (alternative to Step 15)

**Concept.** Step 15 used GitHub Actions (**managed** CI/CD). **Jenkins** is the classic
**self-hosted** alternative — a server you run and extend, with pipeline-as-code in a
`Jenkinsfile` (Groovy) instead of YAML. Same build→test→scan→publish goal; you own the infra.

**Why.** Managed vs self-hosted CI/CD is a real, recurring decision; a lot of industry
infrastructure runs on Jenkins, and it teaches agents, credentials, plugins, and
Docker-outside-of-Docker.

**Do.** (heavy; own overlay, mounts the Docker socket)
```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.jenkins.yaml up -d --build jenkins
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.jenkins.yaml exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
# http://localhost:8088 -> new Pipeline job -> "Pipeline script from SCM" -> this repo, script path Jenkinsfile
```

**Understand.** [Jenkinsfile](../Jenkinsfile) mirrors [ci.yml](../.github/workflows/ci.yml):
Test (Go) and Build frontend run in per-stage `docker` agents; Build images + Scan use the
mounted socket. Compare the two files side by side.

**Checkpoint.** A Pipeline job runs the `Jenkinsfile` green; you can name two things Jenkins
makes you own that Actions handled for free.

➡️ Full lab: [labs/24-jenkins](../labs/24-jenkins/) · config: [deploy/jenkins](../deploy/jenkins/)

---

# Milestone 3 — Cloud, scale & Kubernetes

## Step 18 — Deploy to VPS/EC2 with HTTPS

**Concept.** Put the prod stack on a public server with **automatic HTTPS** — Caddy fetches
and renews Let's Encrypt certs the moment it sees a real domain + ports 80/443.

**Do.** Point a DNS `A` record at the server's Elastic IP, then set the domain and redeploy:
```bash
ansible-playbook playbook.yml -e repo_url=... -e postgres_password=... \
  -e site_domain=dojo.example.com -e acme_email=you@example.com
```

**Understand.** Only Caddy is public (80/443); app/DB ports stay private (the Terraform
security group + `127.0.0.1` binding enforce it). Update = `git pull` + `compose up -d`;
rollback = `git checkout <sha>` + `compose up -d`.

**Checkpoint.** `https://<domain>` loads with a valid certificate; 8080/5432 aren't public.

➡️ Full lab: [labs/18-deploy-https](../labs/18-deploy-https/)

## Step 19 — Security hardening

**Concept.** Least privilege: non-root shell-less images, `no-new-privileges`, drop all
capabilities, read-only rootfs + `tmpfs`, private data ports, image scanning, real secrets.

**Do.**
```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.hardening.yaml up -d --build
docker inspect devops-dojo-api-1 --format '{{.HostConfig.ReadonlyRootfs}} {{.HostConfig.CapDrop}} {{.HostConfig.SecurityOpt}}'
docker scout quickview devops-dojo/api:dev
```

**Understand.** [compose.hardening.yaml](../deploy/compose/compose.hardening.yaml) applies the
constraints; the distroless/non-root image and `127.0.0.1`-bound ports from earlier labs are
already part of the story.

**Checkpoint.** `inspect` shows `ReadonlyRootfs=true`, `CapDrop=[ALL]`, `no-new-privileges`,
and the stack is still healthy; a shell/exec into the API fails.

➡️ Full lab: [labs/19-security](../labs/19-security/)

## Step 20 — Load testing (k6)

**Concept.** Push concurrent load and measure against **thresholds** (error rate, p95
latency) so capacity is a number, not a guess.

**Do.**
```powershell
docker compose -f deploy/compose/compose.yaml up -d api
docker compose -f deploy/compose/compose.yaml run --rm -e VUS=50 -e DURATION=1m load-test
```

**Understand.** [load-test.js](../deploy/load-test/load-test.js) fails (non-zero exit) if
`http_req_failed` or `p(95)` breach thresholds — the same gate you'd wire into CI.

**Checkpoint.** k6 prints latency/error summaries; raising VUs eventually breaches a threshold.

➡️ Full lab: [labs/20-load-testing](../labs/20-load-testing/)

## Step 21 — Horizontal scaling

**Concept.** Add replicas of **stateless** services behind a load balancer; **stateful**
services (`db`, `redis`) need clustering, not copies. A fixed host port blocks scaling.

**Do.**
```powershell
docker compose -f deploy/compose/compose.yaml up -d --scale worker=3
docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml `
  -f deploy/compose/compose.scale.yaml up -d --scale api=3 --scale frontend=2
```

**Understand.** [compose.scale.yaml](../deploy/compose/compose.scale.yaml) drops the app host
ports and swaps Caddy to [Caddyfile.scale](../deploy/caddy/Caddyfile.scale) (dynamic DNS
upstreams) so it balances across replicas.

**Checkpoint.** Multiple api/worker replicas run and serve through Caddy; `db` stays single.

➡️ Full lab: [labs/21-scaling](../labs/21-scaling/)

## Step 22 — Kubernetes on kind

**Concept.** Orchestrate across a cluster with self-healing, rolling updates, and autoscaling.
Compose maps cleanly: service→Deployment+Service, volume→PVC (StatefulSet), env→ConfigMap+
Secret, migrate→Job, Caddy→Ingress, `--scale`→replicas+HPA.

**Do.** (full walkthrough in [deploy/k8s/README.md](../deploy/k8s/README.md))
```powershell
kind create cluster --config deploy/k8s/kind/kind-cluster.yaml
kind load docker-image devops-dojo/api:dev devops-dojo/frontend:dev
kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
kubectl apply -f deploy/k8s/base/
```

**Checkpoint.** Pods Running; `http://localhost/api/steps` returns 24; deleting an API pod
self-heals; `kubectl scale` changes replicas.

➡️ Full lab: [labs/22-kubernetes](../labs/22-kubernetes/) · manifests: [deploy/k8s/base](../deploy/k8s/base/)

## Step 23 — Helm packaging

**Concept.** Package the manifests as a parameterized **chart** with `values.yaml`; one
`helm install`/`upgrade`/`rollback` per environment instead of hand-edited YAML.

**Do.**
```powershell
helm template dojo deploy/k8s/helm/devops-dojo        # render/verify
helm install dojo deploy/k8s/helm/devops-dojo -n devops-dojo --create-namespace
helm upgrade dojo deploy/k8s/helm/devops-dojo -n devops-dojo --set api.replicas=4
```

**Understand.** The chart in [deploy/k8s/helm/devops-dojo](../deploy/k8s/helm/devops-dojo/)
templates images/replicas/ingress/HPA from values; migrations run as a Helm hook.

**Checkpoint.** `helm template` renders cleanly; `install` serves the app; `upgrade --set
api.replicas=4` scales and `helm rollback` reverts.

➡️ Full lab: [labs/23-helm](../labs/23-helm/)

## Step 25 — Capstone: DevOps Dojo on EKS via GitOps

**Concept.** Bring it all together the way real teams run software: a managed **EKS** cluster
(Terraform), images built/scanned/pushed by **CI** to a registry, delivered by **GitOps
(ArgoCD)** that continuously reconciles the cluster to Git — self-healing and rollback via
`git revert`.

**Why.** This is the end-to-end story that gets you hired: *commit → tested/scanned/versioned
image → Kubernetes on AWS through a self-healing GitOps pipeline.*

**Do.** (real cloud cost — destroy when done)
```powershell
cd deploy/eks; terraform init; terraform apply       # EKS cluster
terraform output -raw configure_kubectl | Invoke-Expression
# install ingress-nginx + ArgoCD, then:
kubectl apply -f deploy/gitops/argocd/application.yaml
```

**Understand.** Terraform ([deploy/eks](../deploy/eks/)) builds the cluster; CI publishes
images to GHCR; ArgoCD ([deploy/gitops](../deploy/gitops/)) syncs the Helm chart from Git.

**Checkpoint.** ArgoCD reports **Synced/Healthy**; the app serves via the ELB; scaling a
deployment by hand is auto-reverted; you `terraform destroy` afterward.

➡️ Full lab: [labs/25-capstone-eks-gitops](../labs/25-capstone-eks-gitops/)

## Step 26 — Production secrets management

**Concept.** Never commit real secrets or bake them into images. The app consumes a Kubernetes
`Secret` by name; something **external** populates it — **Sealed Secrets** (encrypted, safe to
commit, GitOps-native) or the **External Secrets Operator** (synced from AWS Secrets
Manager/Vault).

**Why.** This closes the biggest "not production-grade" gap in the project — plaintext secrets.

**Do.**
```powershell
# Chart stops rendering the Secret; you provide dojo-secrets externally:
helm upgrade --install dojo deploy/k8s/helm/devops-dojo -n devops-dojo --set secrets.create=false
```

**Understand.** The chart guards its Secret with `{{- if .Values.secrets.create }}`; workloads
reference `dojo-secrets` by name regardless of who creates it. See
[deploy/secrets](../deploy/secrets/) for both the Sealed Secrets workflow and the External
Secrets Operator manifests.

**Checkpoint.** `helm template ... --set secrets.create=false` renders no Secret; the app still
runs from an externally-managed `dojo-secrets`; no plaintext secret is in Git.

➡️ Full lab: [labs/26-secrets-management](../labs/26-secrets-management/) · config: [deploy/secrets](../deploy/secrets/)

---

🎉 **The full path is complete** — from `docker build` to a self-healing, GitOps-delivered
Kubernetes deployment on AWS.

## Kubernetes deep-dive track (Platform/SRE · CKA/CKS-aligned)

Optional but high-value if you're targeting Platform/SRE roles. Each builds on the same app and
runs on kind (or EKS). Full walkthroughs in the labs; one-line each:

- **[27 · RBAC & least privilege](../labs/27-k8s-rbac/)** — dedicated ServiceAccount with no
  token; scoped Role/RoleBinding; test with `kubectl auth can-i`.
- **[28 · NetworkPolicies](../labs/28-k8s-network-policies/)** — default-deny + explicit allows
  (zero-trust), enforced by Calico.
- **[29 · Kyverno](../labs/29-k8s-kyverno/)** — policy-as-code at admission (no `:latest`,
  require limits/labels), Audit → Enforce.
- **[30 · cert-manager](../labs/30-k8s-cert-manager/)** — automatic in-cluster TLS (self-signed
  or Let's Encrypt).
- **[31 · KEDA](../labs/31-k8s-keda-autoscaling/)** — event-driven autoscaling of the worker on
  Redis queue depth (even to zero).
- **[32 · Argo Rollouts](../labs/32-k8s-argo-rollouts/)** — canary/blue-green progressive
  delivery with pause/promote/abort.
- **[33 · Velero](../labs/33-k8s-velero-backup/)** — scheduled namespace backup + restore drill
  (cluster-state DR).
- **[34 · kube-prometheus-stack](../labs/34-k8s-kube-prometheus-stack/)** — the Prometheus
  Operator; scrape the app via a `ServiceMonitor`.

These map directly onto what **CKA/CKS** and Platform/SRE interviews probe.

## Milestone 4 — Operate, Automate & Prove It (labs 35–42)

The last mile between "can build it" and "can run it" — troubleshooting under pressure,
scripting, IaC maturity, promotion flows, supply-chain proof. These are the topics interviews
and screening tests hit hardest. One line each; full walkthroughs in the labs:

- **[35 · Incident response](../labs/35-incident-response/)** — eight scripted break-fix
  drills against your own stack (CrashLoopBackOff, OOMKilled, selector typo, dirty
  migration…), plus [runbooks](runbooks/) and a [postmortem template](postmortem-template.md).
  The "production is broken — go" interview round, rehearsed.
- **[36 · Multi-env promotion](../labs/36-multi-env-promotion/)** — dev/staging/prod from one
  Helm chart via an ArgoCD **ApplicationSet**; promotion = a PR bumping an image tag; prod
  deliberately manual-sync.
- **[37 · Bash & Python automation](../labs/37-scripting-automation/)** — backup rotation,
  wait-for-healthy, restore verification, an AWS tag audit ([scripts/](../scripts/)), and
  jq/awk log drills. *Do anytime after lab 07.*
- **[38 · Git workflows](../labs/38-git-workflows/)** — PR flow, interactive rebase, a
  manufactured merge conflict, `git bisect` on a planted bug, branch protection. *Do anytime.*
- **[39 · Terraform state & modules](../labs/39-terraform-state-and-modules/)** — S3 remote
  state + locking, a reusable module, directory-per-env, and fmt/validate/tflint/checkov in CI.
- **[40 · AWS core services](../labs/40-aws-core-services/)** — RDS, S3 lifecycle backups,
  IAM/**IRSA** (AWS access with zero stored keys), and a guided read of your VPC.
  💸 Needs the lab 25 cluster.
- **[41 · Supply-chain security](../labs/41-supply-chain-security/)** — cosign **keyless
  signing** in CI, Kyverno signature verification at admission, and a Trivy CRITICAL gate
  with a governed `.trivyignore`.
- **[42 · GitLab CI](../labs/42-gitlab-ci/)** — the same pipeline translated to
  `.gitlab-ci.yml` (optional, but GitLab is everywhere in EU job postings).

## Companion project: AI Assistant (LLMOps)

Beyond this DevOps path, the repo includes a second, standalone example project —
[`ai-assistant/`](../ai-assistant/) — a **local/remote RAG assistant** that answers questions
about *these very docs and labs* using a local LLM via **Ollama** or **LM Studio** (or one
running on another PC), with Qdrant vectors, grounding guardrails, MMR re-ranking, conversation
memory, Prometheus metrics + a Grafana dashboard, an evaluation harness, and Compose/CI/K8s. It
adds **Python** and **LLMOps** to the portfolio — the AI-infra differentiator on top of these
DevOps foundations. Start at [ai-assistant/README.md](../ai-assistant/README.md) and its
[labs/](../ai-assistant/labs/).

## Getting hired

The capstone (Step 25) is your interview centerpiece; the incident drills (lab 35) are your
second one — rehearsed answers to "tell me about something you debugged". Prepare with
[INTERVIEW_PREP.md](INTERVIEW_PREP.md): a portfolio talk track with likely questions and
strong, project-grounded answers for every concept in this guide, plus troubleshooting
scenarios and an honest gap-closing study plan (**CKA first** — labs 22–34 are most of the
prep — then AWS SAA).

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
