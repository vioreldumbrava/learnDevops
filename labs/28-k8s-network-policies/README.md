# Lab 28 — NetworkPolicies (zero-trust networking)

**Maps to:** deepens §17 · **Milestone:** K8s deep-dive · **Cert:** CKA/CKS

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

By default, **any pod can talk to any pod** in a cluster. **NetworkPolicies** change that to
**default-deny**, then explicitly allow only the flows you need — the network equivalent of the
firewall you already applied at the host level. Critical caveat: policies are only **enforced by
a CNI that supports them**. The default kind CNI (kindnet) does **not**, so this lab uses Calico.

## What you'll do

Lock the namespace to deny-all, then allow exactly: ingress→web, frontend→api, api→db/redis,
worker→redis, and DNS.

## Steps

```powershell
# Cluster with a policy-enforcing CNI:
kind create cluster --config deploy/k8s/kind/kind-calico.yaml
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml
kubectl -n kube-system rollout status ds/calico-node --timeout=180s

# (Re)deploy the app as in lab 22, then apply the policies:
kubectl apply -f deploy/k8s/network-policies/network-policies.yaml
```

Verify (exec into a pod and test allowed vs. denied flows):

```powershell
# api -> db is ALLOWED
kubectl -n devops-dojo exec deploy/api -- sh -c "nc -zv db 5432"       # (if the image had nc)
# frontend -> db is DENIED (only api may reach db). Prove denial by timeout:
kubectl -n devops-dojo exec deploy/frontend -- sh -c "wget -T3 -qO- db:5432; echo exit=$?"
```

(The distroless API has no shell; test denials from the frontend/nginx pod, which does.)

## How it works

[network-policies.yaml](../../deploy/k8s/network-policies/network-policies.yaml) starts with a
`default-deny-all` policy (empty podSelector, both Ingress and Egress), then adds one policy per
app selecting it by its `app` label. Remember the two-sided rule with default-deny **egress**:
a flow needs an egress allow on the *source* **and** an ingress allow on the *destination* — which
is why `frontend` has an egress-to-api rule and `api` has an ingress-from-frontend rule.

## Exercise

Delete the `allow-dns` policy and watch things break: pods can no longer resolve `db`/`redis`
by name. Re-apply it. That failure mode (DNS blocked by default-deny egress) is a classic
real-world NetworkPolicy gotcha.

## Checkpoint

- ✅ Calico is running and enforcing policy.
- ✅ `api → db:5432` works; `frontend → db:5432` is blocked.
- ✅ Removing `allow-dns` breaks name resolution (then restores when re-applied).

## Common failures

- Policies seem to do nothing → your CNI doesn't enforce them (kindnet). Use the Calico config.
- Everything breaks after default-deny → you forgot `allow-dns`, or a source is missing its
  egress rule.

➡️ Next: [Lab 29 — Policy-as-code with Kyverno](../29-k8s-kyverno/)
