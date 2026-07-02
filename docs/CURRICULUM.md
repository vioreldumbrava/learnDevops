# DevOps Dojo — Curriculum

Work the labs in order. Each `labs/NN-*/README.md` follows the same template:

> **Concept (what & why) → What you'll do → Steps → How it works → Exercise → Checkpoint → Common failures → Maps to**

For the narrative, teach-it-step-by-step version of this roadmap, read the guide:
[DOCKER_LEARNING_PATH.md](DOCKER_LEARNING_PATH.md). "Maps to" notes which section of the
legacy DBC-based path each lab corresponds to.

## Roadmap

| Lab | Topic | Maps to original § | Milestone | Status |
|-----|-------|--------------------|-----------|--------|
| [00](../labs/00-prerequisites/) | Prerequisites, tooling, repo tour, `git init` | — | 1 | ✅ |
| [01](../labs/01-docker-basics/) | Docker basics: image vs container vs layer | §1 | 1 | ✅ |
| [02](../labs/02-containerize-api/) | Containerize the API: multi-stage, distroless, non-root | §2–3 | 1 | ✅ |
| [03](../labs/03-containerize-frontend/) | Containerize the frontend (multi-stage → Nginx) | §5 | 1 | ✅ |
| [04](../labs/04-docker-compose/) | Docker Compose: multi-service, DNS, networks, volumes | §4 | 1 | ✅ |
| [05](../labs/05-dev-prod-compose/) | Dev/prod Compose separation | §6 | 1 | ✅ |
| [06](../labs/06-database-migrations/) | Postgres + migrations (golang-migrate) | §7 | 1 | ✅ |
| [07](../labs/07-backup-restore/) | Backups & restore | §8 | 1 | ✅ |
| [08](../labs/08-health-checks/) | Health checks: liveness vs readiness | §9 | 1 | ✅ |
| [09](../labs/09-cache-and-worker/) | Redis cache + background worker (queue) | extra | 1 | ✅ |
| [10](../labs/10-monitoring/) | Monitoring: Prometheus + Grafana | §10 | 1 | ✅ |
| [11](../labs/11-logging/) | Logging: Loki + Promtail | §11 | 1 | ✅ |
| [12](../labs/12-tracing-and-alerting/) | Tracing (OTel + Tempo) + Alerting (Alertmanager) | extra | 1 | ✅ |
| [13](../labs/13-image-registry/) | Image registry: ghcr.io, tags, SBOM | §13 | 2 | ✅ |
| [14](../labs/14-artifact-repository/) | Artifact repository (Nexus) | §14 | 2 | ✅ |
| [15](../labs/15-cicd/) | CI/CD with GitHub Actions | §12 | 2 | ✅ |
| [16](../labs/16-terraform/) | IaC: Terraform | extra | 2 | ✅ |
| [17](../labs/17-ansible/) | Config mgmt: Ansible | extra | 2 | ✅ |
| [18](../labs/18-deploy-https/) | Deploy to VPS/EC2 with HTTPS (Caddy) | §15–16 | 3 | ✅ |
| [19](../labs/19-security/) | Security hardening | §17 | 3 | ✅ |
| [20](../labs/20-load-testing/) | Load testing (k6) | §18 | 3 | ✅ |
| [21](../labs/21-scaling/) | Horizontal scaling | §19 | 3 | ✅ |
| [22](../labs/22-kubernetes/) | Kubernetes on kind | §20 | 3 | ✅ |
| [23](../labs/23-helm/) | Helm packaging | extra | 3 | ✅ |
| [24](../labs/24-jenkins/) | Self-hosted CI/CD with Jenkins (alternative to lab 15) | §12 | 2 | ✅ |
| [25](../labs/25-capstone-eks-gitops/) | **Capstone:** DevOps Dojo on EKS via GitOps (ArgoCD) | all | 3 | ✅ |
| [26](../labs/26-secrets-management/) | Production secrets (Sealed Secrets / External Secrets) | §17+ | 3 | ✅ |

### Kubernetes deep-dive track (Platform/SRE · CKA/CKS-aligned)

| Lab | Topic | Cert | Status |
|-----|-------|------|--------|
| [27](../labs/27-k8s-rbac/) | RBAC & least privilege | CKA/CKS | ✅ |
| [28](../labs/28-k8s-network-policies/) | NetworkPolicies (zero-trust) + Calico | CKA/CKS | ✅ |
| [29](../labs/29-k8s-kyverno/) | Policy-as-code (Kyverno) | CKS | ✅ |
| [30](../labs/30-k8s-cert-manager/) | cert-manager (in-cluster TLS) | — | ✅ |
| [31](../labs/31-k8s-keda-autoscaling/) | KEDA event-driven autoscaling | — | ✅ |
| [32](../labs/32-k8s-argo-rollouts/) | Argo Rollouts (canary) | — | ✅ |
| [33](../labs/33-k8s-velero-backup/) | Velero backup & DR | — | ✅ |
| [34](../labs/34-k8s-kube-prometheus-stack/) | kube-prometheus-stack (cluster monitoring) | — | ✅ |

### Milestone 4 — Operate, Automate & Prove It

The interview-readiness track: troubleshooting under pressure, scripting, IaC maturity,
promotion flows, supply-chain proof. Labs 37–38 have no dependencies beyond the foundation —
do them anytime.

| Lab | Topic | Notes | Status |
|-----|-------|-------|--------|
| [35](../labs/35-incident-response/) | Incident response: break-fix drills, runbooks, postmortems | interview centerpiece #2 | ✅ |
| [36](../labs/36-multi-env-promotion/) | Multi-env promotion (Helm values-per-env + ArgoCD ApplicationSet) | — | ✅ |
| [37](../labs/37-scripting-automation/) | Bash & Python automation (scripts/, jq/awk drills) | do anytime after lab 07 | ✅ |
| [38](../labs/38-git-workflows/) | Git workflows: rebase, conflicts, bisect, protection | do anytime | ✅ |
| [39](../labs/39-terraform-state-and-modules/) | Terraform remote state + locking, modules, IaC checks in CI | deepens lab 16 | ✅ |
| [40](../labs/40-aws-core-services/) | AWS core: RDS, S3 lifecycle, IAM/IRSA, VPC tour | 💸 needs EKS (lab 25) | ✅ |
| [41](../labs/41-supply-chain-security/) | Supply chain: cosign signing, admission verification, scan gates | deepens 13/15/29 | ✅ |
| [42](../labs/42-gitlab-ci/) | GitLab CI: translate the pipeline | optional · EU market | ✅ |

Day-2 artifacts that come with this milestone: [runbooks](runbooks/),
[postmortem template](postmortem-template.md) (+ [worked example](postmortems/)), chaos
injectors ([scripts/chaos](../scripts/chaos/)), automation scripts ([scripts](../scripts/)).

## Intentionally out of scope (and why)

Being able to say *no* with reasons is stronger interview signal than shallow coverage:

- **Service mesh (Istio/Linkerd):** for this app, NetworkPolicies (28), cert-manager (30) and
  Argo Rollouts (32) already deliver zero-trust, TLS, and traffic shifting; a mesh adds a
  control plane to operate that the workload doesn't justify. Know what you'd gain (ambient
  mTLS, L7 policy, traffic mirroring) and what it costs before reaching for one.
- **Azure / GCP tracks:** one cloud deep (AWS — labs 16/25/40) beats three shallow. Managed
  k8s, managed DB, IAM, VPC transfer almost one-to-one; AKS/GKE is mostly a syntax change.
- **HA everything:** single NAT gateway, single-AZ RDS, one-node Postgres are conscious cost
  choices for learning — each lab names exactly what flips in production.

> 🎯 **Landing a job:** the capstone (lab 25) is your interview centerpiece, the incident
> drills (lab 35) are the second one, and [INTERVIEW_PREP.md](INTERVIEW_PREP.md) is the talk
> track — likely questions with strong, project-grounded answers for every concept above.

## Companion project — AI Assistant (LLMOps)

A second, standalone example project lives in [`../ai-assistant/`](../ai-assistant/): a
local/remote **RAG assistant** over these docs (Ollama / LM Studio, local or on another PC),
with grounding, MMR re-ranking, memory, streaming, token/cost + per-stage metrics, a semantic
cache, a **tool-calling agent** that operates the main Dojo API, an eval harness with
prompt-injection tests, and Compose/CI/K8s. It adds Python + LLMOps to the portfolio.
Its labs ([ai-assistant/labs](../ai-assistant/labs/)) run 01–08: foundations (01–05: local LLM,
RAG, guardrails+observability, evaluation, deploy) then LLMOps depth (06 tokens/cost/telemetry,
07 tool calling, 08 evaluation v2 + prompt versioning). The LLMOps interview Q&A is §7 of
[INTERVIEW_PREP.md](INTERVIEW_PREP.md).

## The three pillars of observability

Labs 10–12 deliberately build all three: **metrics** (Prometheus), **logs** (Loki), and
**traces** (Tempo), all viewed through one Grafana — plus **alerts** (Alertmanager). The
API is instrumented for real, so these are not toy dashboards.

## Stateless vs stateful (why it matters for scaling)

- **Stateless:** `api`, `worker`, `frontend` → safe to run many replicas (labs 21–22).
- **Stateful:** `db`, `redis` → need volumes, and special care to scale (StatefulSet, clustering).

Keep this distinction in mind from lab 04 onward; it is the backbone of labs 19, 21, and 22.
