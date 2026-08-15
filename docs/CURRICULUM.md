# DevOps Dojo — curriculum

This curriculum targets a **generalist DevOps / Cloud role first**. The numbered folders are a
library, not a requirement to finish 57 topics before applying. Start with the common core,
apply from week 3, and select one specialization only after the core gates are demonstrated.

Every lab follows the same learning shape:

> **Concept → What you'll do → Steps → How it works → Exercise → Checkpoint → Common failures**

The machine-readable source of truth is [`curriculum/manifest.json`](../curriculum/manifest.json).
It defines order, prerequisites, effort, tracks, cost class and drill requirements; the table
below and dashboard metadata are generated from it. `✅ Authored` means the lab and its
references pass repository integrity checks—not that the learner has mastered it. Personal
progress remains `completed` and `drilled` in the dashboard.

## Job-first common core

> `00 → Git basics from 38 → 01–08 → 37 → 54 (local) → 10 → 13 → 15 → 16 → 39 →`
> `40 Part A → 17 → 18 → 22 → 23 → 26 → 35 → 25 → 40 Part B`

Lab 40 deliberately has two checkpoints: complete its standalone AWS fundamentals after lab
39, then return to the EKS/IRSA portion after lab 25. Mark guided completion after Part A so
the capstone prerequisite is visible; record Part B's restore/IRSA result in the existing
notes and require it for the Delivery/cloud learner gate.
The schedule and application cadence live in [WEEKLY.md](WEEKLY.md).

## Roadmap

<!-- BEGIN GENERATED CURRICULUM ROADMAP -->
| Order | Lab | Tier | Track | Requires | Guided time | Shell | Account and tools | Cost | Teardown |
|---:|---|---|---|---|---:|---|---|---|---|
| 1 | [00 — Prerequisites and repo tour](../labs/00-prerequisites/) | Common core | Common core | — | 60 min | PowerShell + Bash/WSL | none; Git, Docker, curl | free | — |
| 2 | [38 — Git workflows](../labs/38-git-workflows/) | Common core | Common core | 00 | 120 min | Bash/WSL | GitHub; Git, GitHub CLI | free | — |
| 3 | [01 — Docker basics](../labs/01-docker-basics/) | Common core | Common core | 00, 38 | 60 min | PowerShell | none; Docker, Go | local | remove the practice containers and images |
| 4 | [02 — Containerize the API](../labs/02-containerize-api/) | Common core | Common core | 01 | 90 min | PowerShell | none; Docker, Go | local | remove the practice image |
| 5 | [03 — Containerize the frontend](../labs/03-containerize-frontend/) | Common core | Common core | 01 | 75 min | PowerShell | none; Docker, Node.js | local | remove the practice container and image |
| 6 | [04 — Docker Compose](../labs/04-docker-compose/) | Common core | Common core | 02, 03 | 90 min | PowerShell | none; Docker Compose | local | docker compose down -v |
| 7 | [05 — Development and production Compose](../labs/05-dev-prod-compose/) | Common core | Common core | 04 | 75 min | PowerShell | none; Docker Compose | local | docker compose down -v |
| 8 | [06 — Database migrations](../labs/06-database-migrations/) | Common core | Common core | 04 | 90 min | PowerShell | none; Docker Compose, PostgreSQL, golang-migrate | local | docker compose down -v |
| 9 | [07 — Backup and restore](../labs/07-backup-restore/) | Common core | Common core | 06 | 90 min | PowerShell | none; Docker Compose, PostgreSQL | local | docker compose down -v and remove scratch backups |
| 10 | [08 — Health checks](../labs/08-health-checks/) | Common core | Common core | 04 | 75 min | PowerShell | none; Docker Compose, curl | local | docker compose down -v |
| 11 | [37 — Scripting and automation](../labs/37-scripting-automation/) | Common core | Common core | 07 | 150 min | Bash/WSL | none; Bash, Python, jq, awk, shellcheck | local | stop the local stack and remove scratch files |
| 12 | [54 — Linux server operations](../labs/54-linux-server-ops/) | Common core | Common core | 37 | 180 min | Bash/WSL | none; Linux VM, systemd, SSH | local | destroy the local VM or revert its snapshot |
| 13 | [10 — Monitoring](../labs/10-monitoring/) | Common core | Common core | 08 | 120 min | PowerShell | none; Docker Compose, Prometheus, Grafana | local | docker compose down -v |
| 14 | [13 — Image registry](../labs/13-image-registry/) | Common core | Common core | 02 | 90 min | PowerShell | GitHub; Docker, Syft | free | stop the local registry and remove practice packages if desired |
| 15 | [15 — CI/CD with GitHub Actions](../labs/15-cicd/) | Common core | Common core | 13 | 180 min | PowerShell + Bash/WSL | GitHub; GitHub Actions, Docker, Trivy, Cosign | free | — |
| 16 | [16 — Infrastructure as code](../labs/16-terraform/) | Common core | Common core | 00 | 180 min | PowerShell | AWS; Terraform, AWS CLI | cloud-low | terraform destroy and confirm tagged resources are gone |
| 17 | [39 — Terraform state and modules](../labs/39-terraform-state-and-modules/) | Common core | Common core | 16 | 180 min | PowerShell | AWS; Terraform, AWS CLI, tflint | cloud-low | destroy workloads, then remove the state backend only when no longer needed |
| 18 | [40 — AWS core services, Parts A and B](../labs/40-aws-core-services/) | Common core | Common core | 39 | 240 min | PowerShell | AWS; Terraform, AWS CLI | cloud-high | terraform destroy and run the tagged-resource cost check |
| 19 | [17 — Configuration management](../labs/17-ansible/) | Common core | Common core | 16 | 150 min | Bash/WSL | AWS; Ansible, SSH, AWS CLI | cloud-low | destroy the Terraform-managed host |
| 20 | [18 — Deploy with HTTPS](../labs/18-deploy-https/) | Common core | Common core | 17 | 180 min | Bash/WSL | AWS and a DNS provider; Ansible, dig, curl, openssl | cloud-low | terraform destroy and remove temporary DNS records |
| 21 | [22 — Kubernetes on kind](../labs/22-kubernetes/) | Common core | Common core | 08 | 180 min | PowerShell | none; kind, kubectl, Envoy Gateway | local | kind delete cluster --name devops-dojo |
| 22 | [23 — Helm packaging](../labs/23-helm/) | Common core | Common core | 22 | 150 min | PowerShell | none; Helm, kubectl, kind | local | helm uninstall and delete the kind cluster |
| 23 | [26 — Production secrets](../labs/26-secrets-management/) | Common core | Common core | 23 | 120 min | PowerShell | none; kubectl, Helm, Sealed Secrets or External Secrets | local | remove controllers and delete the kind cluster |
| 24 | [35 — Incident response](../labs/35-incident-response/) | Common core | Common core | 22 | 180 min | Bash/WSL | none; kubectl, kind, Bash | local | heal all injected faults and delete the kind cluster |
| 25 | [25 — Capstone: EKS and GitOps](../labs/25-capstone-eks-gitops/) | Common core | Common core | 15, 23, 26, 39, 40 | 300 min | PowerShell + Bash/WSL | AWS and GitHub; Terraform, AWS CLI, kubectl, Helm, Argo CD | cloud-high | destroy EKS and verify no tagged billable resources remain |
| 26 | [27 — Kubernetes RBAC](../labs/27-k8s-rbac/) | Specialization | Platform/CKA | 22 | 90 min | PowerShell | none; kubectl, kind | local | delete practice RBAC objects or the kind cluster |
| 27 | [28 — Kubernetes NetworkPolicies](../labs/28-k8s-network-policies/) | Specialization | Platform/CKA | 22 | 120 min | PowerShell | none; kubectl, kind, Calico | local | delete the policy-enabled kind cluster |
| 28 | [52 — Kubernetes storage](../labs/52-k8s-storage/) | Specialization | Platform/CKA | 22 | 120 min | Bash/WSL | none; kubectl, kind | local | delete PVCs, PVs, and the kind cluster |
| 29 | [53 — Kubernetes scheduling](../labs/53-k8s-scheduling/) | Specialization | Platform/CKA | 22 | 150 min | Bash/WSL | none; kubectl, kind | local | delete the multi-node kind cluster |
| 30 | [48 — CKA exam readiness](../labs/48-cka-exam-readiness/) | Specialization | Platform/CKA | 27, 28, 52, 53 | 240 min | Bash/WSL | CKA simulator when ready; kubectl, kubeadm-compatible lab cluster | local | destroy the disposable exam cluster |
| 31 | [11 — Centralized logging](../labs/11-logging/) | Specialization | SRE | 10 | 120 min | PowerShell | none; Docker Compose, Grafana Alloy, Loki | local | docker compose down -v |
| 32 | [12 — Tracing and alerting](../labs/12-tracing-and-alerting/) | Specialization | SRE | 10, 11 | 150 min | PowerShell | none; Docker Compose, OpenTelemetry, Tempo, Alertmanager | local | docker compose down -v |
| 33 | [55 — PostgreSQL operations](../labs/55-postgres-operations/) | Specialization | SRE | 06 | 180 min | Bash/WSL | none; PostgreSQL, pgbench, PgBouncer | local | docker compose down -v |
| 34 | [56 — SLOs and error budgets](../labs/56-slo-and-error-budgets/) | Specialization | SRE | 10, 12 | 180 min | Bash/WSL | none; Prometheus, Alertmanager, Grafana | local | docker compose down -v |
| 35 | [29 — Kubernetes policy as code](../labs/29-k8s-kyverno/) | Specialization | Platform/CKA | 27 | 120 min | PowerShell | none; kubectl, Helm, Kyverno | local | uninstall Kyverno or delete the kind cluster |
| 36 | [30 — cert-manager](../labs/30-k8s-cert-manager/) | Specialization | Platform/CKA | 22 | 90 min | PowerShell | none; kubectl, Helm, cert-manager | local | uninstall cert-manager or delete the kind cluster |
| 37 | [31 — KEDA autoscaling](../labs/31-k8s-keda-autoscaling/) | Specialization | Platform/CKA | 22 | 90 min | PowerShell | none; kubectl, Helm, KEDA | local | uninstall KEDA or delete the kind cluster |
| 38 | [32 — Argo Rollouts](../labs/32-k8s-argo-rollouts/) | Specialization | Platform/CKA | 23 | 120 min | PowerShell | none; kubectl, Helm, Argo Rollouts | local | uninstall Argo Rollouts or delete the kind cluster |
| 39 | [33 — Velero backup and recovery](../labs/33-k8s-velero-backup/) | Specialization | Platform/CKA | 22 | 150 min | PowerShell | none; kubectl, Helm, Velero, MinIO | local | remove backups, uninstall Velero, and delete the kind cluster |
| 40 | [34 — Kubernetes monitoring stack](../labs/34-k8s-kube-prometheus-stack/) | Specialization | Platform/CKA | 10, 22 | 150 min | PowerShell | none; kubectl, Helm, kube-prometheus-stack | local | helm uninstall the stack and delete the kind cluster |
| 41 | [49 — Kubernetes networking deep dive](../labs/49-k8s-networking-deep-dive/) | Specialization | Platform/CKA | 22 | 180 min | Bash/WSL | none; kubectl, kind, iproute2, iptables | local | delete the instrumented kind cluster |
| 42 | [41 — Admission-time supply-chain security](../labs/41-supply-chain-security/) | Specialization | Platform/CKA | 15, 29 | 120 min | PowerShell | GitHub; Cosign, Kyverno, kubectl | local | remove admission policies and delete the kind cluster |
| 43 | [09 — Cache and background worker](../labs/09-cache-and-worker/) | Elective | Electives | 04 | 90 min | PowerShell | none; Docker Compose, Redis | local | docker compose down -v |
| 44 | [14 — Artifact repository](../labs/14-artifact-repository/) | Elective | Electives | 13 | 120 min | PowerShell | none; Docker Compose, Nexus | local | docker compose down -v |
| 45 | [19 — Security hardening](../labs/19-security/) | Elective | Electives | 15 | 120 min | PowerShell | none; Docker Compose, Trivy | local | docker compose down -v |
| 46 | [20 — Load testing](../labs/20-load-testing/) | Elective | Electives | 10 | 90 min | PowerShell | none; k6, Docker Compose, Grafana | local | docker compose down -v |
| 47 | [21 — Horizontal scaling](../labs/21-scaling/) | Elective | Electives | 20 | 75 min | PowerShell | none; Docker Compose, k6 | local | docker compose down -v |
| 48 | [24 — Self-hosted CI/CD with Jenkins](../labs/24-jenkins/) | Elective | Electives | 15 | 150 min | PowerShell | GitHub; Docker Compose, Jenkins | local | docker compose down -v |
| 49 | [36 — Multi-environment promotion](../labs/36-multi-env-promotion/) | Elective | Electives | 25 | 120 min | PowerShell | AWS and GitHub; Argo CD, Helm, kubectl | cloud-high | destroy all promoted cloud environments |
| 50 | [42 — GitLab CI](../labs/42-gitlab-ci/) | Elective | Electives | 15 | 120 min | PowerShell | GitLab; GitLab CI, Docker | free | — |
| 51 | [43 — Jenkins Shared Library](../labs/43-jenkins-shared-library/) | Elective | Electives | 24 | 150 min | PowerShell | GitHub; Jenkins, GitHub, smee | local | stop Jenkins and the webhook relay |
| 52 | [44 — Ansible at scale](../labs/44-ansible-at-scale/) | Elective | Electives | 17 | 150 min | Bash/WSL | AWS; Ansible, AWS CLI | cloud-low | destroy all inventory hosts |
| 53 | [45 — Boto3 operations automation](../labs/45-boto3-ops-automation/) | Elective | Electives | 40 | 120 min | Bash/WSL | AWS; Python, boto3, AWS CLI | cloud-low | remove practice snapshots and instances |
| 54 | [46 — Helm library chart and Helmfile](../labs/46-helm-library-chart/) | Elective | Electives | 23 | 150 min | PowerShell | none; Helm, Helmfile, kind | local | helmfile destroy and delete the kind cluster |
| 55 | [47 — Cloud portability with AKS](../labs/47-cloud-portability-aks/) | Elective | Electives | 25 | 180 min | PowerShell | Azure; Terraform, Azure CLI, kubectl, Helm | cloud-high | terraform destroy and verify the resource group is empty |
| 56 | [50 — Go and Python API parity](../labs/50-go-vs-python-parity/) | Elective | Electives | 08 | 120 min | PowerShell | none; Go, Python, Docker Compose | local | docker compose down -v |
| 57 | [51 — Cilium and eBPF](../labs/51-k8s-cilium-ebpf/) | Elective | Electives | 28, 49 | 240 min | Bash/WSL | none; kind, Cilium CLI, Hubble CLI | local | delete the Cilium kind cluster |
<!-- END GENERATED CURRICULUM ROADMAP -->

## Tracks and boundaries

### Common core — Generalist / Cloud

The core moves Linux, Git, Bash, network diagnosis and AWS fundamentals ahead of specialist
Kubernetes add-ons. It ends in three portfolio proofs: a secure delivery pipeline, a blind
incident/postmortem, and an EKS/GitOps capstone.

Supply-chain essentials belong in the core CI lab: immutable action references, short-lived
AWS authentication, vulnerability gating, SBOM, provenance and signing. Admission-time
verification remains the advanced half of lab 41.

### Platform / CKA specialization

Required route: `27 → 28 → 52 → 53 → 48` after the core Kubernetes labs. It covers RBAC,
network isolation, storage, scheduling and cluster operations. Labs 29–34, 49 and 51 add policy
engines, controllers and data-plane depth, but do not block CKA booking.

Booking gate: pass lab 48's 10-task internal mock at 8/10 within 45 minutes on two different
weeks. Book four to six weeks out, then pass one 120-minute full simulator using that
simulator's scoring rule before the exam.

### SRE specialization

Required route: `11 → 12 → 55 → 56`, alongside recurring blind incidents from lab 35. This
adds centralized logs, tracing, Postgres diagnosis, SLOs and error-budget alerting after the
common monitoring foundation.

### Electives

Nexus, Jenkins/GitLab alternatives, advanced Kubernetes controllers, AKS portability,
Cilium/eBPF, the polyglot API, the operator project and the LLMOps companion are portfolio
specializations. Pick one because a target role asks for it—not to raise a completion count.

## Mastery model

Core and selected specialization labs use four stages:

1. **Guided checkpoint** with the repository open.
2. **Independent variation** with official documentation allowed.
3. **Delayed timed drill** from [DRILLS.md](DRILLS.md); only this marks `drilled`.
4. **Novel transfer** 21–42 days later through a changed scenario or mock interview.

Optional labs may be reference-only. The manifest explicitly says whether a drill is required,
so the repository no longer claims that every authored topic has a timed drill.

## Learner gates

- **Foundation:** reconstruct Compose, migrate/restore data and diagnose readiness.
- **Delivery / cloud:** take a PR through secure CI and complete a repeatable Terraform
  apply/destroy using short-lived AWS credentials.
- **Kubernetes:** deploy and roll back via Helm + Gateway API and repair an unseen incident.
- **Portfolio-ready:** demonstrate the capstone, one runbook, one postmortem and two clean mock
  interviews.

## Deliberately out of the common core

- **Multiple clouds:** AWS remains the deep implementation. Lab 47 and
  [CLOUD_PROVIDER_MAP.md](CLOUD_PROVIDER_MAP.md) prove transfer to AKS without duplicating the
  whole path.
- **Service mesh:** Gateway API, NetworkPolicies, certificate automation and progressive
  delivery cover the current workload. Add a mesh only when workload identity, east-west mTLS
  or traffic policy creates a concrete need.
- **HA everywhere:** single-AZ or single-instance choices keep learning affordable. Each cloud
  lab must state the production delta and end with tagged-resource teardown verification.

## Companion projects

- [`ai-assistant/`](../ai-assistant/) is an optional LLMOps specialization: local/private RAG,
  evaluation, guardrails, observability and deployment.
- [`dojo-operator/`](../dojo-operator/) is an optional Platform specialization: CRD,
  reconciliation, status, finalizers, RBAC and controller tests.

Neither project blocks applications or common-core completion.
