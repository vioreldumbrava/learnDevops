# Production secrets management

The chart's built-in `dojo-secrets` Secret (`secrets.create=true`) is fine for local/dev/CI,
but it puts the password in `values.yaml` — you'd never commit that for real. The fix: set
**`secrets.create=false`** and let the workloads consume a `dojo-secrets` Secret that is
**managed externally**. Nothing in the app changes — the Deployments/StatefulSet still
reference `dojo-secrets` by name.

Two standard approaches, both included here:

## Option A — Sealed Secrets (GitOps-native, no external store)

You encrypt a Secret with the cluster's public key into a `SealedSecret` custom resource that
is **safe to commit to Git**; the in-cluster controller decrypts it into a real Secret. Perfect
for the ArgoCD/GitOps flow (lab 25) because the encrypted secret lives in the repo.

```bash
# 1. Install the controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.38.4/controller.yaml

# 2. Install the kubeseal CLI (see the sealed-secrets releases page), then create a normal
#    Secret locally and seal it (never commit the plaintext one):
kubectl create secret generic dojo-secrets -n devops-dojo \
  --from-literal=POSTGRES_PASSWORD='S3cure!' \
  --from-literal=DATABASE_URL='postgres://dojo:S3cure!@db:5432/dojo?sslmode=disable' \
  --dry-run=client -o yaml \
  | kubeseal --format yaml > deploy/secrets/capstone/sealed-dojo-secrets.yaml

# 3. Apply (or let ArgoCD sync it); the controller creates the real dojo-secrets Secret
kubectl apply -f deploy/secrets/capstone/sealed-dojo-secrets.yaml

# 4. Deploy the chart with the built-in Secret disabled
helm upgrade --install dojo deploy/k8s/helm/devops-dojo -n devops-dojo --set secrets.create=false
```

## Option B — External Secrets Operator + AWS Secrets Manager (cloud-native, pairs with EKS)

The **External Secrets Operator (ESO)** syncs secrets from an external store (AWS Secrets
Manager here) into a K8s Secret. The source of truth is your cloud secret store; Git holds
only *references*, never values.

```bash
# 1. Install ESO
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace

# 2. Put the real secret in AWS Secrets Manager (JSON with the keys ESO will map)
aws secretsmanager create-secret --name devops-dojo/postgres \
  --secret-string '{"password":"S3cure!","database_url":"postgres://dojo:S3cure!@db:5432/dojo?sslmode=disable"}'

# 3. Grant access via IRSA (the ClusterSecretStore's service account needs
#    secretsmanager:GetSecretValue), then apply the store + external secret:
kubectl apply -f deploy/secrets/external-secrets/cluster-secret-store.yaml
kubectl apply -f deploy/secrets/external-secrets/external-secret.yaml   # creates dojo-secrets

# 4. Deploy the chart with the built-in Secret disabled
helm upgrade --install dojo deploy/k8s/helm/devops-dojo -n devops-dojo --set secrets.create=false
```

## Which to use?

- **Sealed Secrets** — simplest, fully GitOps, no cloud dependency. Great default for this repo.
- **External Secrets + a cloud store / Vault** — the source of truth lives outside the cluster,
  supports rotation and central governance. The common enterprise choice.

Either way you've closed the gap: **no plaintext secret in Git**, and the app is unchanged.

SealedSecret ciphertext is bound to the target controller key, Secret name, and namespace.
Regenerate the file after moving from kind to EKS unless you deliberately restore the same
controller sealing key. The capstone Argo Application has `secrets.create=false`; it expects
this encrypted template (or the ESO resource) to be committed before its first sync.
