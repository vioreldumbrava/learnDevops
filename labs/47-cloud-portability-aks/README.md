# Lab 47 — Cloud portability: the same chart on Azure AKS

**Maps to:** proves labs 22/23/25 transfer · **Milestone:** 5 — Ecosystem breadth · 💸 ~€0.10/h, teardown same session

**Run from:** the **repo root** — the AKS Terraform steps `cd deploy/aks` first (and come back with `cd ../..`).

## Concept

The curriculum goes **one cloud deep** on purpose ([why](../../docs/CURRICULUM.md#intentionally-out-of-scope-and-why)).
This lab is the proof that the depth transfers: deploy the **unchanged** Helm chart to
Azure AKS. If the claim "Kubernetes is the portability layer" is true, only two things should
be Azure-specific: how the cluster gets created, and how you authenticate to it. Everything
after `kubectl get nodes` should feel like lab 22.

Why Azure and not GCP: EU job postings are full of AKS; the mapping doc covers GCP on paper
([CLOUD_PROVIDER_MAP.md](../../docs/CLOUD_PROVIDER_MAP.md) — read it before or after, it's
the other half of this lab).

## What you'll do

Provision AKS with Terraform (`deploy/aks/` — compare its size with `deploy/eks/`!), deploy
the existing chart without editing a single template, reach the app on a public IP, then tear
everything down with one command.

> 💸 An [Azure free account](https://azure.microsoft.com/free/) comes with credits; the AKS
> control plane is free (unlike EKS) and two `Standard_B2s` nodes are ~€0.10/hour. One
> session, then destroy.

## Steps

### 0. Prereqs

[Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) plus the usual suspects
(terraform, kubectl, helm), and images published to GHCR as **public** packages (lab 15/25).

```powershell
az login                    # browser flow; picks your subscription
az account show             # confirm which subscription pays
```

### 1. Provision the cluster

```powershell
cd deploy/aks
terraform init
terraform apply             # ~5-10 min
```

While it runs, diff [deploy/aks/main.tf](../../deploy/aks/main.tf) against
[deploy/eks/main.tf](../../deploy/eks/main.tf): no VPC module, no subnets, no NAT, no IAM —
a resource group and a cluster. Azure assembled the rest (into an auto-created `MC_*`
resource group — go find it in the portal).

### 2. Authenticate kubectl — the only new trick

```powershell
terraform output -raw get_credentials_command | Invoke-Expression
kubectl get nodes           # 2 nodes, Ready — from here on it's lab 22
kubectl config get-contexts # dojo-aks joined your kind/EKS contexts
```

### 3. Ingress controller

```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
kubectl -n ingress-nginx get svc ingress-nginx-controller -w   # EXTERNAL-IP: pending -> a real IP
```

Same controller as labs 22/25; the `LoadBalancer` Service materializes as an **Azure Load
Balancer with a public IP** this time (on EKS it was an ELB hostname) — the cloud provider
integration is the part that swapped, not your manifests.

### 4. Deploy the chart — unchanged

```powershell
cd ../..
kubectl create namespace devops-dojo
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/

helm install dojo deploy/k8s/helm/devops-dojo -n devops-dojo `
  -f deploy/k8s/helm/devops-dojo/values-dev.yaml --set ingress.host=""

kubectl -n devops-dojo get pods,svc,ingress
```

The same chart, the same values overlay you used on kind and EKS. (`ingress.host=""` just
means "answer on any host" — you're hitting a bare IP, not a domain.)

### 5. Open it

```powershell
kubectl -n ingress-nginx get svc ingress-nginx-controller   # note EXTERNAL-IP
```

Open `http://<external-ip>/` — the dashboard, on Azure. Count what you changed to get here:
zero templates, zero values files.

### 6. Tear down (don't skip)

```powershell
cd deploy/aks
terraform destroy           # removes the resource group => everything in it
az group list -o table      # confirm: no dojo-aks-rg, no MC_* group left
```

That's the resource-group lifecycle from the mapping doc: deletion is one motion, nothing
orphaned. (Compare with hunting stray EIPs/volumes after AWS labs.)

## How it works

- [deploy/aks/](../../deploy/aks/) is a full Terraform root in ~40 effective lines because
  AKS defaults the network, node images, and LB wiring that `deploy/eks/` assembles
  explicitly. Neither is "better": EKS showed you every part (which is why it was the
  capstone); AKS shows how much of that a provider will own if you let it.
- Cluster auth: `az aks get-credentials` writes a kubeconfig entry backed by Entra ID — the
  role `aws eks update-kubeconfig` + IAM plays on AWS. After that, kubectl/Helm neither know
  nor care which cloud they're talking to.
- What *would* change in production: LB/ingress annotations (static IP, WAF), storage classes
  (`managed-csi` vs `gp3`), pod→cloud identity (Workload Identity vs IRSA), and where images
  live (ACR vs ECR/GHCR). That short list **is** the migration estimate an interviewer wants
  when they ask "we're on Azure — problem?".

## Exercise

1. Point the app at **ACR** instead of GHCR: `az acr create` + `az acr import` (pull your
   GHCR images across), `az aks update --attach-acr` (grants the cluster's managed identity
   pull rights — no imagePullSecret needed), then `helm upgrade --set image.api.repository=...`.
   You've now touched the Azure counterpart of labs 13/40.
2. Skim [CLOUD_PROVIDER_MAP.md](../../docs/CLOUD_PROVIDER_MAP.md) and rehearse its 30-second
   interview answer out loud — with this lab done, every sentence in it is yours.

## Checkpoint

- ✅ `kubectl get nodes` shows the AKS pool — provisioned by Terraform, authenticated via az.
- ✅ The app answers on the ingress public IP with **zero chart changes**.
- ✅ `az group list` is clean after teardown.
- ✅ You can name the four things that would actually change in a real AWS→Azure move.

## Common failures

- `terraform apply` fails with quota/SKU errors → free subscriptions have low vCPU quotas per
  region and some regions lack `Standard_B2s`; try `-var location=northeurope` or request the
  (free) quota bump in the portal.
- `az login` picked the wrong subscription → `az account set --subscription <id>` before
  applying; Terraform inherits the CLI's active subscription.
- `EXTERNAL-IP` stuck on `<pending>` → the cloud LB takes a couple of minutes; if it persists,
  `kubectl -n ingress-nginx describe svc ingress-nginx-controller` (quota again, usually
  public IPs).
- `ImagePullBackOff` → GHCR packages are private (make them public, lab 25 step 1) or the
  `OWNER/REPO` placeholders in `values-dev.yaml` still point at nobody's registry.
- Login/auth loops in WSL → `az` and `kubectl` must agree on one kubeconfig; check
  `$env:KUBECONFIG`/`$KUBECONFIG` and that you ran `get-credentials` in the same shell.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md)
