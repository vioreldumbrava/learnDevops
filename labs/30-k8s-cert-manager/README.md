# Lab 30 — cert-manager with Gateway API

**Tier:** elective · **Track:** Platform · **Milestone:** Kubernetes depth

**Run from:** the **repo root** (`learnDevops/`). Complete lab 22 first.

## Concept

cert-manager reconciles a declared `Certificate`, obtains or creates the certificate through
an Issuer, stores it in a Secret, and renews it before expiry. Gateway API terminates TLS by
referencing that Secret from an HTTPS listener.

## What you'll do

Enable cert-manager's Gateway API integration, issue a local self-signed certificate, attach
it to the existing Gateway, and prove HTTPS works. The HTTP listener remains available for
ACME HTTP-01 challenges when you later use a public domain.

## Steps

The Gateway API CRDs already exist because Envoy Gateway was installed in lab 22. Install
cert-manager with its Gateway integration enabled:

```powershell
helm upgrade --install cert-manager `
  oci://quay.io/jetstack/charts/cert-manager `
  --namespace cert-manager --create-namespace `
  --set crds.enabled=true `
  --set config.gatewayAPI.enabled=true
kubectl -n cert-manager rollout status deployment/cert-manager --timeout=180s

kubectl apply -f deploy/k8s/cert-manager/issuers.yaml
kubectl apply -f deploy/k8s/cert-manager/certificate.yaml
kubectl -n devops-dojo wait certificate/dojo-tls --for=condition=Ready --timeout=120s
```

Add an HTTPS listener and attach the existing route to it:

```powershell
$listenerPatch = @'
[
  {
    "op": "add",
    "path": "/spec/listeners/-",
    "value": {
      "name": "https",
      "protocol": "HTTPS",
      "port": 443,
      "tls": {
        "mode": "Terminate",
        "certificateRefs": [{"kind": "Secret", "name": "dojo-tls"}]
      },
      "allowedRoutes": {"namespaces": {"from": "Same"}}
    }
  }
]
'@
kubectl -n devops-dojo patch gateway dojo --type=json -p $listenerPatch

$routePatch = @'
[
  {
    "op": "add",
    "path": "/spec/parentRefs/-",
    "value": {"name": "dojo", "sectionName": "https"}
  }
]
'@
kubectl -n devops-dojo patch httproute dojo --type=json -p $routePatch

kubectl -n devops-dojo wait gateway/dojo --for=condition=Programmed --timeout=180s
curl.exe --fail --insecure --resolve dojo.local:443:127.0.0.1 https://dojo.local/api/steps
```

`--insecure` is appropriate only because this exercise intentionally uses a self-signed
issuer. Do not normalize it as the fix for a production trust failure.

## How it works

[`certificate.yaml`](../../deploy/k8s/cert-manager/certificate.yaml) requests `dojo.local`
and stores the result in `dojo-tls`. The Gateway HTTPS listener terminates TLS using that
Secret. [`issuers.yaml`](../../deploy/k8s/cert-manager/issuers.yaml) also contains a staging
ACME issuer whose HTTP-01 solver creates a temporary HTTPRoute; use that only with a real,
publicly resolvable domain.

## Exercise

Record the current Secret resource version, delete `dojo-tls`, and watch cert-manager reissue
it. Then use `openssl s_client -connect localhost:443 -servername dojo.local` to inspect the
served subject, issuer, and expiry rather than trusting a browser icon.

## Checkpoint

- `Certificate/dojo-tls` reports `Ready=True`.
- `Gateway/dojo` has an HTTPS listener referencing `dojo-tls` and remains Programmed.
- The HTTPRoute is accepted by both listeners and the HTTPS API request succeeds.
- Deleting the Secret triggers reconciliation and reissuance.

## Common failures

- Certificate remains unready → inspect the CertificateRequest and cert-manager events.
- HTTPS listener has `ResolvedRefs=False` → Secret name/namespace does not match the Gateway.
- Port 443 refuses connections → recreate kind with the current config, which maps host 443
  to Envoy's fixed NodePort 30443.
- Public ACME challenge fails → DNS must resolve to a publicly reachable listener on port 80.

➡️ Next: [Lab 31 — KEDA event-driven autoscaling](../31-k8s-keda-autoscaling/)
