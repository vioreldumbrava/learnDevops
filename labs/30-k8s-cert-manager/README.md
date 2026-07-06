# Lab 30 — cert-manager (in-cluster TLS)

**Maps to:** deepens §16 · **Milestone:** K8s deep-dive

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

**cert-manager** automates X.509 certificates in Kubernetes. You declare a `Certificate`; it
talks to an `Issuer` (self-signed, a private CA, or Let's Encrypt via ACME) and stores the
result in a Secret that your Ingress consumes — issuing *and renewing* automatically. It's the
in-cluster equivalent of what Caddy did for you in Compose (lab 18).

## What you'll do

Install cert-manager, issue a certificate, and serve the app over HTTPS through the Ingress.

## Steps

```powershell
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
kubectl -n cert-manager rollout status deploy/cert-manager-webhook --timeout=180s

kubectl apply -f deploy/k8s/cert-manager/issuers.yaml
kubectl apply -f deploy/k8s/cert-manager/certificate.yaml

# cert-manager creates/populates the Secret:
kubectl -n devops-dojo get certificate,secret dojo-tls

# Attach the cert to the Ingress (TLS termination at ingress-nginx):
kubectl -n devops-dojo patch ingress dojo --type=merge -p '{\"spec\":{\"tls\":[{\"hosts\":[\"dojo.local\"],\"secretName\":\"dojo-tls\"}]}}'
```

## How it works

[issuers.yaml](../../deploy/k8s/cert-manager/issuers.yaml) defines a `selfsigned` ClusterIssuer
(works offline) and a `letsencrypt-staging` one (real ACME via an HTTP-01 challenge through the
ingress). [certificate.yaml](../../deploy/k8s/cert-manager/certificate.yaml) requests a cert for
`dojo.local` into the `dojo-tls` Secret; the Ingress references that Secret for TLS. For a real
public domain, switch `issuerRef` to `letsencrypt-staging` (then production) and use the domain.

## Exercise

Delete the `dojo-tls` Secret and watch cert-manager **re-issue** it automatically within
seconds — the same reconciliation loop that handles renewals before expiry.

## Checkpoint

- ✅ `kubectl get certificate dojo-tls` shows `READY=True`.
- ✅ The `dojo-tls` Secret exists and is referenced by the Ingress `tls` block.
- ✅ Deleting the Secret triggers automatic re-issue.

## Common failures

- Certificate stuck `False` → describe it and the `CertificateRequest`/`Order`; for Let's
  Encrypt the HTTP-01 challenge needs a reachable public domain on port 80.
- Webhook errors right after install → give cert-manager's webhook a moment to become ready.

➡️ Next: [Lab 31 — KEDA event-driven autoscaling](../31-k8s-keda-autoscaling/)
