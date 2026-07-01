# Lab 26 — Production secrets management

**Maps to:** deepens §17 (security) · **Milestone:** 3 · *closes the biggest "not production-grade" gap*

## Concept

Up to now the database password lived in `.env` / Helm `values.yaml` — fine for learning, but
you must **never commit real secrets to Git** or bake them into images. The production pattern:
the app consumes a Kubernetes `Secret` by name, and something **external** populates it, so the
plaintext never touches your repo. Two standard tools:

- **Sealed Secrets** — encrypt a Secret with the cluster's public key into a `SealedSecret`
  that's *safe to commit*; an in-cluster controller decrypts it. Fully GitOps.
- **External Secrets Operator (ESO)** — sync from a cloud store (AWS Secrets Manager, Vault)
  into a K8s Secret; Git holds only references. The common enterprise choice.

## What you'll do

Flip the chart to *not* render the Secret, then provide `dojo-secrets` externally — proving
the app is unchanged while the plaintext leaves your repo.

## Steps

Full commands for both tools are in [deploy/secrets/README.md](../../deploy/secrets/README.md).
The essence:

```bash
# The chart no longer creates the Secret:
helm upgrade --install dojo deploy/k8s/helm/devops-dojo -n devops-dojo --set secrets.create=false
```

**Sealed Secrets (recommended for this repo):**
```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/controller.yaml
kubectl create secret generic dojo-secrets -n devops-dojo \
  --from-literal=POSTGRES_PASSWORD='S3cure!' \
  --from-literal=DATABASE_URL='postgres://dojo:S3cure!@db:5432/dojo?sslmode=disable' \
  --dry-run=client -o yaml | kubeseal --format yaml > sealed-dojo-secrets.yaml
kubectl apply -f sealed-dojo-secrets.yaml   # controller creates the real dojo-secrets
```

**External Secrets + AWS (pairs with the EKS capstone):** install ESO, create the AWS secret,
then apply [cluster-secret-store.yaml](../../deploy/secrets/external-secrets/cluster-secret-store.yaml)
and [external-secret.yaml](../../deploy/secrets/external-secrets/external-secret.yaml).

## How it works

Setting `secrets.create=false` makes the Helm chart skip its `Secret` template (see the
`{{- if .Values.secrets.create }}` guard in `templates/config.yaml`). The workloads still do
`secretKeyRef: { name: dojo-secrets }`, so whoever creates that Secret — the Sealed Secrets
controller or ESO — satisfies them. The plaintext exists only in the cluster (and, for ESO, in
the cloud store), never in Git.

## Exercise

Wire it into GitOps (lab 25): commit `sealed-dojo-secrets.yaml` to the repo and let **ArgoCD**
apply it alongside the chart (with `secrets.create=false` in the Application values). Now even
your secret is delivered by GitOps — encrypted, auditable, and safe in Git.

## Checkpoint

- ✅ `helm template ... --set secrets.create=false` renders **no** `Secret` resource.
- ✅ With the app deployed that way, `kubectl -n devops-dojo get secret dojo-secrets` exists —
  created by the controller/operator, not the chart.
- ✅ The app runs normally; no plaintext secret is in your Git repo.

## Common failures

- Pods stuck `CreateContainerConfigError` → `dojo-secrets` doesn't exist yet; the
  controller/operator hasn't produced it (check its logs) or you forgot to seal/apply it.
- `kubeseal` can't reach the controller → it must be installed and running first.

Interview line: *"Secrets are never in Git — the chart references a Secret by name that's
produced in-cluster by Sealed Secrets (or synced from AWS Secrets Manager via the External
Secrets Operator), so rotation and least-privilege live outside the codebase."*

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md)
