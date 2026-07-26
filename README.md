# DevOps Dojo 🥋

A **hands-on, step-by-step DevOps learning project**. You learn by building, running,
deploying, and operating a small but real web application — and the application you deploy
*is* the curriculum: a dashboard that shows the roadmap and tracks your progress.

> Replaces the old `DBC_to_C_code`-based learning path with a relatable, stateful 3‑tier
> app so that databases, monitoring, scaling, and queues are **real**, not bolted on.
> The full step-by-step teaching guide is
> [docs/DOCKER_LEARNING_PATH.md](docs/DOCKER_LEARNING_PATH.md); each concept links to a
> hands-on lab under [labs/](labs/).

![DevOps Dojo architecture and toolchain](docs/architecture.svg)

> 🤖 **Second project — [ai-assistant/](ai-assistant/):** a local, private **RAG assistant**
> (LLMOps) that answers questions about these docs using a local LLM via **Ollama / LM Studio**,
> **Qdrant** vectors, grounding guardrails, metrics, an eval harness, and Compose/CI/K8s. It's
> the AI-infra differentiator on top of this DevOps foundation.

> ⚙️ **Third project — [dojo-operator/](dojo-operator/):** build your own **Kubernetes
> operator** in Go — a CRD + controller that manages scheduled Postgres backups for the Dojo's
> database (reconcile loop, status/conditions, finalizers, GC, least-priv RBAC, fake-client
> tests). You've *used* operators (cert-manager, KEDA, ArgoCD); this teaches how they work
> inside — the Platform-engineer depth signal. Six step-by-step labs.

## What you build

| Tier | Tech | Why it's here |
|------|------|---------------|
| `frontend` | React + Vite + TypeScript | The dashboard UI |
| `api` | Go (`chi`, `pgx`) | REST API with real `/metrics`, `/healthz`, `/readyz`, tracing |
| `api-py` | Python (`FastAPI`, `asyncpg`) | Optional drop-in twin of `api` — same contract; swap via a Compose overlay ([lab 50](labs/50-go-vs-python-parity/)) |
| `worker` | Go | Background jobs off a Redis queue (teaches scaling & queues) |
| `db` | PostgreSQL | Progress, notes, curriculum — teaches migrations & backups |
| `redis` | Redis | Cache + job queue |
| `caddy` | Caddy | Reverse proxy + automatic HTTPS (prod) |
| observability | Prometheus, Grafana, Loki, Promtail, Tempo, Alertmanager | metrics, logs, traces, alerts |

## Prerequisites

- Docker Desktop (Linux containers) + Docker Compose v2
- PowerShell (commands are written for it; bash equivalents are easy)
- Optional later: Node 20+, Go 1.23+ (only if you want to run app code outside Docker),
  `kubectl` + `kind`, `helm`, `terraform`, `ansible`, `k6`

New to the Linux side of containers? Read [docs/LINUX_FOR_CONTAINERS.md](docs/LINUX_FOR_CONTAINERS.md).

## Quick start (development)

From the **repo root**:

```powershell
copy .env.example .env
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.dev.yaml up --build
```

Then open:

- Dashboard (Vite dev server): http://localhost:5173
- API health: http://localhost:8080/healthz
- API metrics: http://localhost:8080/metrics

Toggle a lab "complete" in the UI, reload the page, and confirm it persisted — that round
trip proves the **frontend → api → Postgres** path is working (Redis caches the read).

Stop everything:

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.dev.yaml down
```

Wipe the database volume for a clean start:

```powershell
docker compose -f deploy/compose/compose.yaml down -v
```

## How to use the labs

Work through `labs/00..26` in order, then pick up the Kubernetes deep-dive (`27..34` + the
CKA exam-ops drills in `48`, the networking deep dives in `49`/`51`, and storage/scheduling
in `52`/`53`), the
operate-and-automate track (`35..42` plus `54..56` — Linux server ops, Postgres under load,
SLOs & burn-rate alerting; labs 37–38 can be done anytime after the foundation),
and the ecosystem-breadth track (`43..47`, TWN-inspired).
In a hurry to interview? Follow the ⚡ **fast track** in
[docs/CURRICULUM.md](docs/CURRICULUM.md) instead and do the rest in parallel with applying.
Every lab follows the same shape:

> **Concept (what & why) → What you'll do → Steps → How it works → Exercise → Checkpoint → Common failures → Maps to**

**How the labs work (read this once):** the app and all its infrastructure are *already
written* in this repo. You don't build each file from a blank page — you **read** the
pre-written file, **run** it, **prove** the property it demonstrates, then **extend** it in
the lab's **Exercise** (that's the type-it-yourself part: add a migration, tighten a policy,
write a script). This is deliberate: you always have a working reference, so a typo can't
strand you for hours. Labs build on each other's artifacts — lab 02 reuses lab 01's image,
lab 18 deploys the server from labs 16–17, lab 35 breaks the cluster from lab 22.

**Then close the book.** That model trains recognition; interviews and the CKA test recall
from a blank terminal on a clock. So each lab also has a **closed-book drill** in
[docs/DRILLS.md](docs/DRILLS.md) — a from-scratch task with a time target and a pass test —
and the dashboard tracks *completed* (read it) and *drilled* (can do it) as two separate
states, with a **Drill next** panel that picks the stalest one for you.
[docs/WEEKLY.md](docs/WEEKLY.md) is the repeating week and the dated calendar;
[docs/TOOLBOX.md](docs/TOOLBOX.md) is the one-time setup (`kind` and `helm` still need
installing).

A couple of labs sort out of numeric order on purpose (they were added later): **lab 24**
(Jenkins) is a Milestone 2 lab, and **lab 48** (CKA drills) belongs in the Kubernetes
deep-dive. Each says so at the top; [docs/CURRICULUM.md](docs/CURRICULUM.md) is the source of
truth for sequence.

Each lab states **where to run its commands** in the *Run from* line under the title — for
most labs that's the **repo root** (`learnDevops/`), not the lab's own folder; labs that need
a different directory (`deploy/terraform`, `ai-assistant/`, …) say so explicitly.

The **Checkpoint** is your pass/fail test for that concept. The full roadmap with status
lives in [docs/CURRICULUM.md](docs/CURRICULUM.md) and inside the running dashboard.

## Repo layout

```
app/api          Go API + worker (one image, two entrypoints)
app/api-py       Python (FastAPI) drop-in twin of app/api — same contract (lab 50)
app/frontend     React + Vite dashboard
db/migrations    golang-migrate SQL (schema + seeded curriculum)
db/seed          throwaway drill data (lab 55) — deliberately NOT migrations
deploy/compose   base + dev + prod + observability Compose files
deploy/systemd   systemd unit, backup timer, logrotate config       (lab 54)
deploy/caddy      Caddyfile (reverse proxy / HTTPS)
deploy/monitoring Prometheus, Grafana, Loki, Promtail, Tempo, Alertmanager, blackbox
deploy/k8s       Kubernetes manifests, Helm chart, kind config   (milestone 3)
deploy/terraform Terraform to provision a VPS/EC2               (milestone 2)
deploy/ansible   Ansible to configure + deploy                  (milestone 2)
deploy/load-test k6 load test                                   (milestone 3)
labs/            one folder per concept
docs/            curriculum + references
.github/workflows CI/CD                                          (milestone 2)
ai-assistant/    Second project: local/remote RAG assistant (LLMOps) — see its own README
dojo-operator/   Third project: build a Kubernetes operator in Go — see its own README
```

## Build status

- ✅ **Milestone 1 — runnable foundation:** app, Compose (dev/prod), Postgres + migrations,
  Redis + worker, health checks, backup/restore, full observability stack, labs 00–12.
- ✅ **Milestone 2 — delivery & infrastructure:** GitHub Actions CI/CD (build/test/scan/push),
  Terraform (provision EC2), Ansible (configure + deploy), Nexus overlay, labs 13–17 —
  plus Jenkins as the self-hosted CI/CD alternative (lab 24).
- ✅ **Milestone 3 — cloud, scale, Kubernetes:** EC2 + HTTPS, security hardening, k6 load test,
  horizontal scaling, Kubernetes on kind + Helm chart, labs 18–23.
- ✅ **Capstone (lab 25):** DevOps Dojo on **AWS EKS** (Terraform) delivered by **GitOps
  (ArgoCD)** — the end-to-end, interview-ready deployment.
- ✅ **Production secrets (lab 26):** Sealed Secrets / External Secrets Operator — no plaintext
  in Git.
- ✅ **Kubernetes deep-dive (labs 27–34 + 48/49 + 51):** RBAC, NetworkPolicies (+Calico), Kyverno,
  cert-manager, KEDA, Argo Rollouts, Velero, kube-prometheus-stack — plus **lab 48**, the
  CKA cluster-ops drills (etcd backup/restore, drain vs PDB, kubelet break-fix, timed mock
  exam), **lab 49**, the networking **data plane** deep dive (pause/veth, ClusterIP +
  kube-proxy DNAT, CoreDNS, service types, the Ingress path), and **lab 51**, the same data
  plane re-implemented in **Cilium/eBPF** (kube-proxy-free Services, Hubble, L7 policy,
  Gateway API with a real LoadBalancer IP on kind), **lab 52** (storage: StorageClass,
  PV/PVC lifecycle, reclaim policies, access modes) and **lab 53** (scheduling: requests,
  taints/tolerations, affinity, topology spread, preemption) — Platform/SRE, CKA/CKS.
- ✅ **Milestone 4 — operate, automate & prove it (labs 35–42, 54–56):** incident drills +
  runbooks, multi-env promotion, Bash/Python automation, Git workflows, Terraform
  state/modules, AWS core services, supply-chain security, GitLab CI — plus **lab 54** (Linux
  server ops: systemd units & timers, journald, SSH hardening, the deleted-but-open disk-full
  drill), **lab 55** (Postgres under load: `pg_stat_statements`, `EXPLAIN (ANALYZE, BUFFERS)`,
  lock contention, connection exhaustion + PgBouncer) and **lab 56** (SLOs & error budgets:
  SLI recording rules, multi-window burn-rate alerting, page-vs-ticket routing,
  [error-budget policy](docs/runbooks/error-budget-policy.md)).
- ✅ **Milestone 5 — ecosystem breadth & portability (labs 43–47):** Jenkins Shared Library +
  dynamic versioning, Ansible dynamic inventory + Terraform handoff, Boto3 ops automation,
  Helm library chart + Helmfile, and the same chart on **Azure AKS**
  (+ [cloud provider map](docs/CLOUD_PROVIDER_MAP.md)) — TWN-bootcamp-inspired additions.

**57 labs authored.** That count is a measure of the library, not of you — the number that
matters is how many are **drilled closed-book** and how recently, which is what the dashboard
tracks.

> 🎯 **Aiming for a DevOps job?** The capstone is your interview centerpiece; see
> [docs/INTERVIEW_PREP.md](docs/INTERVIEW_PREP.md) for a full talk track (likely questions +
> project-grounded answers, troubleshooting scenarios, and a gap-closing study plan) — and
> [docs/WEEKLY.md](docs/WEEKLY.md) for the dated plan that gets you from here to applying.
