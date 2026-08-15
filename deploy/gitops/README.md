# GitOps with ArgoCD

**GitOps** makes Git the single source of truth for what runs in the cluster: instead of
`kubectl apply` / `helm install` by hand, an in-cluster controller (**ArgoCD**) watches a Git
path and **continuously reconciles** the cluster to match it — auto-syncing new commits and
reverting manual drift. Deployments become `git push`; rollbacks become `git revert`.

Here ArgoCD deploys the DevOps Dojo **Helm chart** ([../k8s/helm/devops-dojo](../k8s/helm/devops-dojo/))
onto the EKS cluster from [../eks](../eks/).

## Bootstrap vs. GitOps-managed

A useful distinction to be able to explain: some things are **bootstrap** (imperative, done
once to get GitOps going) and everything after is **GitOps-managed** (declarative, in Git):

- **Bootstrap (imperative):** the cluster itself (Terraform), ArgoCD, the Sealed Secrets
  controller, the migrations ConfigMap, and image pull access.
- **GitOps-managed (declarative):** the app and encrypted SealedSecret — every resource in
  the Helm chart, reconciled by ArgoCD from Git.

Lab 40's RDS transfer follows the same boundary: bootstrap a distinct, externally managed
`dojo-rds-secrets`, then commit `secrets.create=false`, `secrets.name=dojo-rds-secrets`, and
`postgres.enabled=false` in the Application values. The distinct name prevents Argo's prune
of its old `dojo-secrets` from deleting the new credentials. Never manually scale the
Argo-managed database and expect it to stay scaled; self-heal restores what Git declares.

## Prerequisites

- An EKS cluster reachable via `kubectl` (see [../eks/README.md](../eks/README.md)).
- Your `api`/`frontend` images published to GHCR by CI (labs 13/15), and the packages made
  **public** (Repo → Packages → package → visibility). For private images, create an
  `imagePullSecret` instead.
- Edit `argocd/application.yaml`: replace `OWNER/REPO` in `repoURL` and the image repositories.
- Complete lab 26 and install the `kubeseal` CLI. Ciphertext from a kind controller cannot be
  reused on a new EKS controller; the commands below regenerate it for this cluster.

## Install ArgoCD

```powershell
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server --timeout=180s

# Admin password + UI (port-forward):
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | %{[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_))}
kubectl -n argocd port-forward svc/argocd-server 8081:443
# open https://localhost:8081  (user: admin)
```

## Bootstrap namespace, migrations and the sealing controller

```powershell
kubectl create namespace devops-dojo --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace devops-dojo gateway-access=dojo `
  pod-security.kubernetes.io/enforce=restricted `
  pod-security.kubernetes.io/enforce-version=v1.35 `
  pod-security.kubernetes.io/audit=restricted `
  pod-security.kubernetes.io/audit-version=v1.35 `
  pod-security.kubernetes.io/warn=restricted `
  pod-security.kubernetes.io/warn-version=v1.35 --overwrite
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/ `
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.38.4/controller.yaml
kubectl -n kube-system rollout status deployment/sealed-secrets-controller --timeout=180s
```

Generate desired-state ciphertext against this cluster. The password is read interactively
instead of committed; use at least 16 URI-safe letters/digits/punctuation without `:/?#@%`:

```powershell
$password = Read-Host "Local Postgres password" -MaskInput
if ($password.Length -lt 16 -or $password -match '[:/?#@%]') {
  throw "Use 16+ URI-safe characters without : / ? # @ or %"
}
$databaseUrl = "postgres://dojo:${password}@db:5432/dojo?sslmode=disable"
kubectl create secret generic dojo-secrets -n devops-dojo `
  --from-literal="POSTGRES_PASSWORD=$password" `
  --from-literal="DATABASE_URL=$databaseUrl" `
  --dry-run=client -o yaml | kubeseal --format yaml `
  > deploy/secrets/capstone/sealed-dojo-secrets.yaml

git add deploy/secrets/capstone/sealed-dojo-secrets.yaml `
  deploy/gitops/argocd/application.yaml
git commit -m "feat: add EKS-sealed database credentials"
git push

# application.yaml has secrets.create=false; Argo applies the encrypted
# SealedSecret and the controller creates dojo-secrets.
kubectl apply -f deploy/gitops/argocd/application.yaml
```

ArgoCD now syncs the chart. Watch it:

```powershell
kubectl -n argocd get applications
kubectl -n devops-dojo get sealedsecret,secret
kubectl -n devops-dojo get pods,svc,gateway,httproute
```

## See GitOps in action

- **Self-heal:** `kubectl -n devops-dojo scale deploy/api --replicas=1` — ArgoCD detects the
  drift and scales it back to the Git-declared value within seconds.
- **Deploy via commit:** bump `api.replicas` in the chart's `values.yaml`, push to `main`;
  ArgoCD syncs the change with no `kubectl`.
- **Rollback:** `git revert` the commit (or use ArgoCD's History → Rollback).

## Teardown

```powershell
kubectl delete -f deploy/gitops/argocd/application.yaml   # removes the app (prune)
# StatefulSet PVCs are retained by design; after confirming the backup, delete
# them explicitly and wait for dynamically provisioned PVs/EBS volumes to go.
kubectl -n devops-dojo delete pvc --all --ignore-not-found
kubectl get pv
# then destroy the cluster from deploy/eks (terraform destroy)
```
