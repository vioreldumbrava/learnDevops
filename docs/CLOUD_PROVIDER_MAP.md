# Cloud provider map — AWS ↔ Azure ↔ GCP

The Dojo goes **one cloud deep** (AWS — labs 16/25/40) because concepts transfer and syntax
doesn't matter until you're hired. This map is the transfer table: what each thing you built
on AWS is called on Azure and GCP, plus the differences that actually bite. Lab 47 proves the
point hands-on by deploying the unchanged Helm chart to AKS.

## Service mapping

| What you built (lab) | AWS | Azure | GCP |
|----------------------|-----|-------|-----|
| Managed Kubernetes (25) | EKS | AKS | GKE |
| VMs (16/18) | EC2 | Virtual Machines | Compute Engine |
| Container registry (13/40) | ECR | ACR (Container Registry) | Artifact Registry |
| Object storage (39/40) | S3 | Blob Storage | Cloud Storage (GCS) |
| Managed Postgres (40) | RDS | Azure Database for PostgreSQL | Cloud SQL |
| Network boundary (40) | VPC | VNet | VPC |
| Firewalling (16) | Security Groups | Network Security Groups | Firewall rules |
| Identity & access (27/40) | IAM (users/roles/policies) | Entra ID + RBAC roles | Cloud IAM |
| Pod → cloud identity (40) | IRSA | Workload Identity | Workload Identity |
| L7 load balancer (22/25) | ALB | Application Gateway | Cloud Load Balancing |
| Metrics/logs (10/34) | CloudWatch | Azure Monitor | Cloud Operations (Stackdriver) |
| Secrets (26) | Secrets Manager / SSM | Key Vault | Secret Manager |
| Serverless containers | Fargate | Container Apps / ACI | Cloud Run |
| Snapshots/DR policy (45) | EBS snapshots + DLM | Azure Backup | PD snapshots + schedules |
| IaC state locking (39) | S3 (native lockfile) | Blob Storage (lease-based lock) | GCS (native locking) |
| CLI | `aws` | `az` | `gcloud` |
| Cloud-native CI/CD (15/42) | CodePipeline (rare) | Azure DevOps / GitHub Actions | Cloud Build |

## Differences that actually bite

- **Grouping & teardown.** Azure's **resource group** is a hard container: everything lives
  in one, and deleting the group deletes it all — there is no AWS equivalent (tags +
  `terraform destroy` approximate it). GCP's **project** plays the same role, even harder
  (billing and APIs attach to it).
- **Who pays for the control plane.** EKS charges per cluster-hour; AKS and GKE control
  planes are free (GKE has a free-tier zonal cluster) — why throwaway clusters feel cheaper
  off-AWS.
- **Identity model.** AWS IAM is account-scoped users/roles/policies. Azure puts *people* in
  Entra ID (tenant-wide) and grants **RBAC roles on scopes** (subscription → resource group →
  resource) — closer to K8s RBAC (lab 27) than to AWS IAM. GCP IAM is role bindings on
  projects/resources.
- **Networking defaults.** On EKS *you* bring the VPC (that's most of `deploy/eks/main.tf`);
  AKS/GKE default to creating and managing the network for you. Less assembly, less control —
  the same managed-vs-self-hosted trade as lab 24 vs 15.
- **K8s itself is the portability layer.** kubectl, Helm charts, manifests, probes, HPA,
  RBAC, NetworkPolicies — labs 22–36 transfer *unchanged*. What changes per cloud: how you
  authenticate to the cluster, the ingress/LB annotations, storage classes, and pod→cloud
  identity.

## The interview answer (30 seconds)

> "I went deep on AWS — VPC, IAM/IRSA, EKS with Terraform and GitOps — because depth
> transfers. The Kubernetes layer is identical across clouds: to prove it I deployed the same
> Helm chart to AKS without changing it; only cluster auth and the LB in front differed. On
> Azure I'd map IAM to Entra + RBAC scopes, S3 to Blob, RDS to Azure Database, and expect the
> resource-group lifecycle to simplify teardown. The concepts are the skill; the names are a
> lookup table."

GCP hands-on is deliberately skipped (same reasoning — see
[CURRICULUM.md](CURRICULUM.md#intentionally-out-of-scope-and-why)); if a target role names
GKE, do a one-day AKS-style pass with `gcloud container clusters create`.

➡️ Hands-on: [labs/47-cloud-portability-aks](../labs/47-cloud-portability-aks/)
