# Lab 36 — Multi-environment promotion (dev → staging → prod)

**Maps to:** extra · **Milestone:** 4 — Operate & Automate · **Platform**

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Real teams don't run one copy of an app — they run **dev** (newest approved build, cheap), **staging**
(pinned build, prod-shaped) and **prod** (reviewed, pinned, human-gated). The interview
question is *"how does a change get to production?"* and the strong answer is: **the same
chart everywhere, per-env values files, and promotion = a Git PR that bumps an image tag** —
never a hand-run `kubectl`/`helm` against prod.

An ArgoCD **ApplicationSet** stamps out one Application per environment from a single
template, so adding an env is one list entry, not a copy-pasted pipeline.

## What you'll do

Deploy three environments of DevOps Dojo onto your kind cluster from one Helm chart, then
promote a build dev → staging → prod using only Git commits (plus one deliberate manual sync
for prod). Everything works identically on EKS (lab 25) — kind just makes it free.

Prereqs: lab 22 (kind + Envoy Gateway), lab 15 (CI publishing images to your GHCR), lab 25's
ArgoCD install ([deploy/gitops/README.md](../../deploy/gitops/README.md)) — ArgoCD itself
runs fine on kind.

## Steps

### 1. Point the files at your fork

Replace `OWNER/REPO` in
[deploy/gitops/argocd/applicationset.yaml](../../deploy/gitops/argocd/applicationset.yaml) and
in the three overlays
([values-dev.yaml](../../deploy/k8s/helm/devops-dojo/values-dev.yaml),
[values-staging.yaml](../../deploy/k8s/helm/devops-dojo/values-staging.yaml),
[values-prod.yaml](../../deploy/k8s/helm/devops-dojo/values-prod.yaml)). Then open your GHCR
packages page and set the **dev, staging and prod tags to builds that actually exist** (e.g.
the `sha-…` tag CI printed, or a `v*` tag you've pushed). Commit and **push** — ArgoCD deploys
what's in Git, not what's on your disk.

### 2. Bootstrap what GitOps doesn't own

Migrations SQL is a ConfigMap created from files (as in labs 22/25), and prod's secret is
externally managed (`secrets.create=false` — the lab 26 pattern), so create both by hand once:

```powershell
foreach ($e in "dev","staging","prod") {
  kubectl create namespace dojo-$e
  kubectl label namespace dojo-$e gateway-access=dojo `
    pod-security.kubernetes.io/enforce=restricted `
    pod-security.kubernetes.io/enforce-version=v1.35 `
    pod-security.kubernetes.io/audit=restricted `
    pod-security.kubernetes.io/warn=restricted --overwrite
  kubectl create configmap dojo-migrations -n dojo-$e --from-file=db/migrations/
}

$pw = "pick-something-strong"
kubectl -n dojo-prod create secret generic dojo-secrets `
  --from-literal=POSTGRES_PASSWORD=$pw `
  --from-literal=DATABASE_URL="postgres://dojo:${pw}@db:5432/dojo?sslmode=disable"
```

### 3. Create the three Applications from one template

```powershell
kubectl apply -f deploy/gitops/argocd/applicationset.yaml
kubectl -n argocd get applications
```

Expect: `dojo-dev` and `dojo-staging` go **Synced/Healthy** on their own; `dojo-prod` sits
**OutOfSync** — that's the design, prod waits for a human:

```powershell
argocd app sync dojo-prod        # or press Sync in the UI
```

The ApplicationSet disables per-release Gateways and attaches each chart's HTTPRoute to the
platform-owned `devops-dojo/dojo` Gateway from lab 22. The namespace label is the explicit
opt-in matched by that Gateway's `allowedRoutes` selector. This role split—platform owns
listeners/data plane, application teams own routes—is a central Gateway API improvement.

```powershell
curl -H "Host: dev.dojo.localhost"     http://localhost/api/steps
curl -H "Host: staging.dojo.localhost" http://localhost/api/steps
curl -H "Host: dojo.localhost"         http://localhost/api/steps
```

### 4. Promote a build

1. Merge something to `main`; CI publishes new images. Open a PR that updates the two
   `values-dev.yaml` tags to that build's immutable `sha-…` tag; after merge, Argo syncs dev.
   A real platform may automate this Git update, but it should still leave an auditable commit.
2. **Promote to staging:** edit the two `tag:` lines in `values-staging.yaml` to the same
   build's `sha-…` tag, commit, push. Watch `dojo-staging` sync itself.
3. **Promote to prod:** open a PR bumping `values-prod.yaml` to the tag staging validated.
   After merge, `dojo-prod` shows OutOfSync with a visible diff — review it, then
   `argocd app sync dojo-prod`.

Rollback is the same move in reverse: `git revert` the bump and sync.

## How it works

- **One chart, layered values.** ArgoCD passes `valueFiles: [values.yaml, values-<env>.yaml]`
  — Helm merges them, so an overlay holds only the per-env differences (replicas, HPA, host,
  tags, secrets policy). No copy-pasted manifests to drift apart.
- **The generator.** The ApplicationSet's `list` generator emits
  `{env: dev|staging|prod, autosync: …}`; the template renders an Application per element
  (`dojo-{{ .env }}` → namespace `dojo-{{ .env }}`). `templatePatch` adds
  `syncPolicy.automated` only where `autosync: true` — which is how prod stays manual.
- **Promotion is data, not process.** The "pipeline" is a one-line diff in a values file.
  That makes every promotion reviewed, auditable (`git log values-prod.yaml` *is* the deploy
  history), and revertible.
- **Why every environment pins:** a moving tag means you cannot prove what was tested or roll
  back to "the previous one". The exercise uses CI's commit-derived `sha-…` tags; production
  charts commonly go further and render image digests (lab 13).

## Exercise

1. Add a **qa** environment: one new element in the ApplicationSet list + a
   `values-qa.yaml`. Count the lines it took — that's the ApplicationSet payoff.
2. Swap the `list` generator for the **git directory generator** (one directory per env under
   `deploy/gitops/envs/`) so adding an env doesn't even touch the ApplicationSet.
3. Compare with **Kustomize** overlays (`base/` + `overlays/<env>/`): same idea, patches
   instead of value merges. Be able to say when you'd pick which (Kustomize for raw YAML you
   don't template; Helm when you already ship a chart).

## Checkpoint

- ✅ `kubectl -n argocd get applications` shows `dojo-dev`/`dojo-staging` Synced and Healthy
  without manual action, `dojo-prod` only after an explicit sync.
- ✅ A one-line tag bump in `values-staging.yaml` redeploys staging by itself.
- ✅ All three hosts answer through their Gateway/HTTPRoute; you can explain the production
  shared-Gateway alternative and its namespace attachment policy.
- ✅ You can explain why prod is manual-sync + pinned-tag in two sentences.

## Common failures

- Applications stuck `Unknown`/`ComparisonError` → `OWNER/REPO` still unreplaced, or you
  edited files locally but didn't push (ArgoCD reads Git).
- Pods `ImagePullBackOff` → the pinned tag doesn't exist in your GHCR, or a
  `sha-CHANGE_ME` placeholder remains. Select a tag the CI run actually published.
- `migrate` Job failing in one env → that namespace is missing its `dojo-migrations`
  ConfigMap (step 2 creates one **per env**).
- prod pods `CreateContainerConfigError` → `dojo-secrets` missing: `secrets.create=false`
  means *you* own the Secret (step 2, or Sealed Secrets/ESO from lab 26).
- Wrong app answers on `/` → you curl'd without a `Host:` header; the envs are
  distinguished by host rule now.

➡️ Next: [Lab 37 — Bash & Python automation](../37-scripting-automation/)
