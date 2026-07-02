# Lab 46 — Helm library chart + Helmfile

**Maps to:** deepens labs 23/36 · **Milestone:** 5 — Ecosystem breadth · *TWN Bootcamp Module 10*

## Concept

Two patterns from Helm-heavy shops:

1. **Library chart** — api, frontend and worker each carried a near-identical
   Deployment/Service. With 3 services that's tolerable; with 30 microservices it's a bug
   farm (fix a probe in 29 places, miss the 30th). A `type: library` chart renders nothing
   itself — it exports **named templates** that app charts `include`, so the Deployment shape
   is written once. This is TWN's "1 shared Helm chart for all microservices", done the
   idiomatic way.
2. **Helmfile** — `helm install/upgrade` is imperative: *you* remember the release name, the
   namespace, which values file. **Helmfile** declares releases as data and `helmfile apply`
   converges the cluster. It's the **push-based** counterpart of what ArgoCD ApplicationSet
   (lab 36) does pull-based — many shops without a GitOps controller run exactly this from CI.

## What you'll do

Read the refactored chart (the app templates shrank to `include` calls), prove the refactor
changed *nothing* in the output, then drive dev/staging/prod with Helmfile on the kind
cluster.

## Steps

Prereqs: kind cluster with ingress + images loaded (lab 22 steps 1–3), Helm (lab 23), and
[helmfile](https://github.com/helmfile/helmfile/releases) (single binary; also needs the
diff plugin: `helm plugin install https://github.com/databus23/helm-diff`).

### 1. Read the library chart

- [charts/dojo-lib/templates/_deployment.tpl](../../deploy/k8s/helm/devops-dojo/charts/dojo-lib/templates/_deployment.tpl)
  — *the* Deployment, written once; optional blocks (`command`, `port`, probes) render only
  when passed.
- [templates/api.yaml](../../deploy/k8s/helm/devops-dojo/templates/api.yaml) — what an app
  template looks like now: an `include` plus a dict of the service's specifics. Compare
  worker/frontend: same shape, different dict.

### 2. Prove the refactor is invisible

```powershell
helm template dojo deploy/k8s/helm/devops-dojo | kubectl apply --dry-run=client -f -
```

If the release from lab 23 is still installed, the stronger proof:

```powershell
helm upgrade dojo deploy/k8s/helm/devops-dojo -n devops-dojo --dry-run
# or with the diff plugin: helm diff upgrade dojo deploy/k8s/helm/devops-dojo -n devops-dojo
```

The diff is empty — a pure refactor. (This is also how you *safely* adopt a library chart in
a real team: template-diff before/after in CI, byte-for-byte.)

### 3. Drive environments with Helmfile

```powershell
cd deploy/k8s/helm
kubectl create namespace dojo-dev
kubectl create configmap dojo-migrations -n dojo-dev --from-file=../../../db/migrations/

helmfile -e dev diff       # preview: everything is "to be created"
helmfile -e dev apply      # converge: install/upgrade only what differs
helm list -A               # dojo-dev release, dojo-dev namespace
```

Run `helmfile -e dev apply` **again**: no changes, nothing applied — it converges rather than
re-installs. Then look at [helmfile.yaml](../../deploy/k8s/helm/helmfile.yaml): three
environments, one release definition, the env name templated into release, namespace and
values file. `-e staging` / `-e prod` give you the other environments (each needs its
namespace + migrations ConfigMap first).

> ⚠️ Same namespaces as lab 36's ApplicationSet on purpose — they are two answers to the same
> question. Run one *or* the other against a cluster: two controllers converging one
> namespace fight forever.

## How it works

- **Library chart mechanics:** `dojo-lib` sits unpacked in the parent's `charts/` folder
  (a *vendored* dependency — no `helm dependency build` needed) and is declared in
  [Chart.yaml](../../deploy/k8s/helm/devops-dojo/Chart.yaml). Its templates all start with
  `_`, so Helm loads their `define`s but renders no output; `type: library` makes that
  contract explicit. The parent's templates call
  `{{ include "dojo-lib.deployment" (dict ...) }}` — the dict *is* the interface, and
  everything a service doesn't pass simply doesn't render.
- **Where's the line?** postgres/redis (StatefulSet-ish, volumes) deliberately stay
  hand-written: forcing the odd ones into the shared template is how library charts rot
  into a second values.yaml. Abstract the *repeated* shape, keep the exceptions explicit.
- **Helmfile mechanics:** environments are declared, then the release list is templated per
  environment (`{{ .Environment.Name }}`). `helmfile apply` = render → diff against the
  cluster → apply only drifted releases; `helmfile diff` is the review step you'd wire into CI.
- **Helmfile vs ArgoCD ApplicationSet (the interview question):** both template
  "env × (chart + values)". Helmfile **pushes** from wherever it runs (a laptop, a CI job) —
  simple, no cluster controller, but nothing reconciles drift between runs. ArgoCD **pulls**
  inside the cluster and continuously reconciles git → cluster (lab 25/36). GitOps wins for
  production fleets; Helmfile wins for simplicity, local dev, and shops that don't want a
  controller. Knowing *why you'd pick each* is the answer.

## Exercise

1. Add a `pushgateway`-style dummy service: copy `worker.yaml`, change the dict (name,
   image `busybox`, command `["sleep", "3600"]`, no env). One include, one dict — that's the
   payoff. Delete it after.
2. In `helmfile.yaml`, pin `prod` to `installed: false` (a release you *declare but gate*),
   run `helmfile -e prod apply`, and explain when a team would ship config ahead of enabling it.

## Checkpoint

- ✅ `helm template` output is unchanged by the library-chart refactor (empty diff).
- ✅ api/frontend/worker templates contain no Deployment boilerplate, only includes + dicts.
- ✅ `helmfile -e dev apply` converges the dev environment; a second apply changes nothing.
- ✅ You can give the push-vs-pull (Helmfile vs ArgoCD) trade-off in three sentences.

## Common failures

- `no template "dojo-lib.deployment"` → the library chart isn't under
  `devops-dojo/charts/dojo-lib/`, or its template files don't start with `_` (non-underscore
  files in a library chart are ignored as output but their defines must still load — keep the
  `_` convention).
- `helm lint`: *chart metadata is missing these dependencies* → vendored subcharts must be
  declared in the parent `Chart.yaml` `dependencies:` list (name + version is enough).
- Weird `---apiVersion:` parse errors → a `{{-` left-trim directly after a `---` separator
  eats the newline and glues the documents together; use `{{ include` (no dash) after `---`.
- `helmfile: environment "default" not found` → pass `-e dev|staging|prod`; this helmfile
  defines no default environment on purpose.
- Pods pending in `dojo-dev` → missing `dojo-migrations` ConfigMap in that namespace, or kind
  doesn't have the images (`kind load docker-image ...`, lab 22).

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md)
