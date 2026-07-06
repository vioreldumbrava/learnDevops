# Lab 32 — Progressive delivery with Argo Rollouts

**Maps to:** deepens §12/§15 · **Milestone:** K8s deep-dive · **SRE**

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

A plain Deployment rolls out all-at-once (or a simple rolling update). **Argo Rollouts**
replaces the Deployment with a `Rollout` that supports **canary** and **blue-green**: shift a
small % of traffic to the new version, **pause** to observe (optionally gated by automated
metric analysis), then proceed — or **abort** and instantly roll back. This is how you ship to
production with confidence and a small blast radius.

## What you'll do

Convert the API to a canary Rollout, trigger an update, and watch it progress step by step.

## Steps

```powershell
# Controller + kubectl plugin
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
# (install the `kubectl argo rollouts` plugin from the Argo Rollouts releases page)

# Replace the Deployment with the Rollout (same name/selector)
kubectl -n devops-dojo delete deployment api --ignore-not-found
kubectl apply -f deploy/k8s/rollouts/rollout-api.yaml

# Trigger a new revision (any pod-template change), then watch the canary steps
kubectl -n devops-dojo set image rollout/api api=devops-dojo/api:dev
kubectl argo rollouts -n devops-dojo get rollout api --watch
```

Promote or abort mid-canary:

```powershell
kubectl argo rollouts -n devops-dojo promote api     # skip remaining pauses
kubectl argo rollouts -n devops-dojo abort   api     # roll back to stable instantly
```

## How it works

[rollout-api.yaml](../../deploy/k8s/rollouts/rollout-api.yaml) uses a `canary` strategy with
`setWeight`/`pause` steps (25% → pause → 50% → pause → 75% → pause → 100%). The controller
manages stable vs. canary ReplicaSets and the ratio between them; a `pause` holds the rollout so
you (or an `AnalysisTemplate` querying Prometheus) can decide to continue or abort. Full traffic-
percentage routing uses an ingress/mesh integration; the replica-weighted canary here works with
plain Services.

## Exercise

Add an automated gate: create an `AnalysisTemplate` that queries your Prometheus error-rate
metric (`dojo_http_requests_total{status=~"5.."}`) and reference it in a canary step so a bad
release **auto-aborts**. That closes the loop between observability (labs 10/12) and delivery.

## Checkpoint

- ✅ `kubectl argo rollouts get rollout api` shows canary steps progressing.
- ✅ `promote` advances it; `abort` rolls back to the stable version.
- ✅ You can explain canary vs. blue-green and why you'd pause on metrics.

## Common failures

- `Rollout` won't apply → a Deployment named `api` still exists (same selector); delete it first.
- Steps never advance → they're paused by design; `promote` or wait out the `pause` durations.
- **HPA stops working** → `deploy/k8s/base/hpa.yaml` targets `Deployment/api`, which no longer
  exists once `api` is a Rollout. Either point the HPA's `scaleTargetRef` at
  `kind: Rollout` (`apiVersion: argoproj.io/v1alpha1`), or delete the HPA and let the Rollout
  (and KEDA, lab 31) handle scaling.

➡️ Next: [Lab 33 — Velero backup & DR](../33-k8s-velero-backup/)
