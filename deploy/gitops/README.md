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

- **Bootstrap (imperative):** the cluster itself (Terraform), ArgoCD, the migrations
  ConfigMap, and image pull access.
- **GitOps-managed (declarative):** the app — every workload in the Helm chart, reconciled by
  ArgoCD from Git.

## Prerequisites

- An EKS cluster reachable via `kubectl` (see [../eks/README.md](../eks/README.md)).
- Your `api`/`frontend` images published to GHCR by CI (labs 13/15), and the packages made
  **public** (Repo → Packages → package → visibility). For private images, create an
  `imagePullSecret` instead.
- Edit `argocd/application.yaml`: replace `OWNER/REPO` in `repoURL` and the image repositories.

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

## Bootstrap the app's namespace + migrations, then hand over to GitOps

```powershell
kubectl create namespace devops-dojo
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/

kubectl apply -f deploy/gitops/argocd/application.yaml
```

ArgoCD now syncs the chart. Watch it:

```powershell
kubectl -n argocd get applications
kubectl -n devops-dojo get pods,svc,ingress
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
# then destroy the cluster from deploy/eks (terraform destroy)
```
