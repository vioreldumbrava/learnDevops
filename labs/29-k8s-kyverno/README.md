# Lab 29 — Policy-as-code with Kyverno

**Maps to:** deepens §17 · **Milestone:** K8s deep-dive · **Cert:** CKS

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

RBAC controls *who* can act; **admission policy** controls *what* is allowed to be created,
regardless of who. **Kyverno** runs as an admission controller and validates (or mutates/
generates) resources against cluster-wide policies written as YAML — e.g. "no `:latest` tags",
"every container must set resource limits", "must run as non-root". This is guardrails at the
gate, enforced consistently across all teams.

## What you'll do

Install Kyverno, apply a policy set in Audit mode, see violations, then enforce.

## Steps

```powershell
# Install Kyverno
kubectl create -f https://github.com/kyverno/kyverno/releases/latest/download/install.yaml
kubectl -n kyverno rollout status deploy/kyverno-admission-controller --timeout=180s

kubectl apply -f deploy/k8s/policies/kyverno-policies.yaml

# See which existing workloads violate policy (Audit mode reports, doesn't block)
kubectl get policyreport -n devops-dojo
kubectl describe policyreport -n devops-dojo | Select-String -Pattern "fail|Policy"

# Try to create a bad pod (uses :latest, no limits) and switch a policy to Enforce to block it:
kubectl patch clusterpolicy disallow-latest-tag --type=merge -p '{\"spec\":{\"validationFailureAction\":\"Enforce\"}}'
kubectl -n devops-dojo run bad --image=nginx:latest   # now REJECTED at admission
```

## How it works

[kyverno-policies.yaml](../../deploy/k8s/policies/kyverno-policies.yaml) defines three
`ClusterPolicy` resources: disallow `:latest`, require CPU/memory requests+limits, and require
an `app` label. `validationFailureAction: Audit` generates `PolicyReport`s without blocking;
flipping to `Enforce` makes Kyverno reject violating resources at admission — CI-style checks,
but enforced in-cluster for everything.

## Exercise

Write a fourth policy that **requires `runAsNonRoot: true`** on every container, apply it in
Audit, and check the report against your own workloads (the API is already non-root; try a
deliberately root pod and watch it flagged).

## Checkpoint

- ✅ Kyverno is running and `PolicyReport`s list pass/fail per policy.
- ✅ With `disallow-latest-tag` in Enforce, `run --image=nginx:latest` is rejected.
- ✅ You can explain admission policy vs. RBAC.

## Common failures

- No reports appear → Kyverno isn't ready, or `background: true` scan hasn't run yet; wait a moment.
- Enforce blocks your own deploys → that's the point; fix the workload (add limits, pin tags) or
  scope the policy with `match`/`exclude`.

➡️ Next: [Lab 30 — cert-manager (in-cluster TLS)](../30-k8s-cert-manager/)
