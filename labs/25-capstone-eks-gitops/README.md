# Lab 25 — Capstone: DevOps Dojo on EKS via GitOps

**Maps to:** the whole path · **Milestone:** 3 (capstone) · *the interview centerpiece*

**Run from:** the **repo root** — the Terraform steps `cd deploy/eks` first (and come back with `cd ../..`); all `kubectl`/`helm` commands run from the repo root.

This is the lab you talk about in interviews. It takes everything from labs 00–24 and lands
it the way real teams run software: a managed **Kubernetes cluster on AWS (EKS)**, images
built and published by **CI** to a registry, and delivery through **GitOps (ArgoCD)** — no
`kubectl apply` by hand.

> 💸 **Real cloud cost.** EKS + nodes + NAT gateway is roughly **$5–10/day**. Do it in one
> focused session and **`terraform destroy` at the end**.

## The end-to-end flow

```
git push ─▶ GitHub Actions (lab 15) ─▶ build+scan+push images ─▶ GHCR
                                                                   │
Terraform (deploy/eks) ─▶ EKS cluster ◀── ArgoCD watches Git ──────┘
                                    │        (deploy/gitops)
                                    └─▶ reconciles the Helm chart ─▶ app live behind an Ingress/LB
```

You've built every box already; this lab connects them on real infrastructure.

## Steps

### 1. Publish images (CI)

Push to GitHub so Actions builds and pushes `api`/`frontend` to GHCR (lab 15), then make
those packages **public** (or configure an image pull secret). Set the image repos in
`deploy/gitops/argocd/application.yaml`.

### 2. Provision the cluster (Terraform)

```powershell
cd deploy/eks
copy terraform.tfvars.example terraform.tfvars
terraform init
terraform apply                       # ~15 min
terraform output -raw configure_kubectl | Invoke-Expression
kubectl get nodes
cd ../..
```

### 3. Install an ingress controller

```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/aws/deploy.yaml
kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=180s
```

### 4. Install ArgoCD + hand delivery to GitOps

Follow [deploy/gitops/README.md](../../deploy/gitops/README.md): install ArgoCD, create the
`devops-dojo` namespace + `dojo-migrations` ConfigMap (bootstrap), then:

```powershell
kubectl apply -f deploy/gitops/argocd/application.yaml
kubectl -n argocd get applications          # Synced / Healthy
kubectl -n devops-dojo get pods,svc,ingress
```

### 5. Open it

```powershell
kubectl -n ingress-nginx get svc ingress-nginx-controller   # note the EXTERNAL-IP (an AWS ELB hostname)
```

Open `http://<elb-hostname>/` and `/api/steps`. Your app is live on real cloud Kubernetes,
delivered by GitOps.

### 6. Prove GitOps

- **Self-heal:** `kubectl -n devops-dojo scale deploy/api --replicas=1` → ArgoCD reverts it.
- **Ship a change:** edit `api.replicas` in the chart's `values.yaml`, commit, push → ArgoCD
  syncs it, no `kubectl`.

### 7. Tear down (don't skip)

```powershell
kubectl delete -n devops-dojo ingress --all --ignore-not-found   # release the ELB first
kubectl delete -f deploy/gitops/argocd/application.yaml
cd deploy/eks; terraform destroy
```

## How it works (the pieces, connected)

- **Terraform** ([deploy/eks](../../deploy/eks/)) builds a 3-AZ VPC + EKS + managed nodes.
- **CI** ([ci.yml](../../.github/workflows/ci.yml)) produces versioned, scanned images in GHCR.
- **ArgoCD** ([deploy/gitops](../../deploy/gitops/)) reconciles the **Helm chart**
  ([deploy/k8s/helm/devops-dojo](../../deploy/k8s/helm/devops-dojo/)) from Git → the cluster,
  with prune + self-heal.
- **ingress-nginx** provisions an AWS load balancer as the public entrypoint.

## Checkpoint

- ✅ `kubectl get nodes` shows EKS worker nodes.
- ✅ ArgoCD reports the `devops-dojo` app **Synced / Healthy**.
- ✅ The app is reachable via the ELB hostname; `/api/steps` returns all 57 steps.
- ✅ Scaling a deployment by hand is auto-reverted by ArgoCD (self-heal).
- ✅ You destroyed the cluster afterward.

## Why this is the interview centerpiece

You can now tell a complete, senior-sounding story: *"I take a code change from commit →
tested, scanned, versioned image in a registry → deployed to Kubernetes on AWS through a
GitOps pipeline that self-heals and rolls back via Git."* That sentence, backed by a repo you
can screen-share and defend, is what separates "did a tutorial" from "can do the job."

See [docs/INTERVIEW_PREP.md](../../docs/INTERVIEW_PREP.md) for the full talk track.

## Common failures

- Pods `ImagePullBackOff` → GHCR packages aren't public / no pull secret, or the image repo in
  the Application is wrong.
- Ingress has no address → the AWS ingress-nginx manifest wasn't applied, or the ELB is still
  provisioning (wait a minute).
- `terraform destroy` hangs on the VPC → leftover ELBs; delete the ingress/services first.

➡️ Next: [Lab 26 — Production secrets management](../26-secrets-management/) — the one thing
this capstone still fakes (plaintext secrets) — then back to the map:
[docs/CURRICULUM.md](../../docs/CURRICULUM.md).
