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

> 🎯 **Landing a job:** the capstone (lab 25) is your interview centerpiece, and
> [INTERVIEW_PREP.md](INTERVIEW_PREP.md) is the talk track — likely questions with strong,
> project-grounded answers for every concept above.

## The three pillars of observability

Labs 10–12 deliberately build all three: **metrics** (Prometheus), **logs** (Loki), and
**traces** (Tempo), all viewed through one Grafana — plus **alerts** (Alertmanager). The
API is instrumented for real, so these are not toy dashboards.

## Stateless vs stateful (why it matters for scaling)

- **Stateless:** `api`, `worker`, `frontend` → safe to run many replicas (labs 21–22).
- **Stateful:** `db`, `redis` → need volumes, and special care to scale (StatefulSet, clustering).

Keep this distinction in mind from lab 04 onward; it is the backbone of labs 19, 21, and 22.
