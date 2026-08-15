# Lab 25 — Capstone: EKS 1.35 through secure CI and GitOps

**Tier:** core · **Milestone:** portfolio-ready capstone

**Run from:** the repository root. Terraform commands run under `deploy/eks`; Kubernetes and
GitOps commands run from the root.

This is the interview centerpiece: a change moves through tested, scanned, attested, signed
images into Amazon EKS through Argo CD, and the application is exposed with Gateway API.

> **High cost:** EKS, EC2 nodes, NAT, and ALB are billable (roughly $5–10/day for this
> learning shape). Use a focused session, set a budget before starting, and perform the
> teardown/tag inventory before leaving it.

## Architecture

```text
commit → GitHub Actions → tests/scans → signed images + SBOM/provenance in GHCR
                                      ↓
Terraform → EKS 1.35 ← Argo CD watches Git → Helm → Gateway + HTTPRoute → AWS ALB
```

The supported EKS route is AWS Load Balancer Controller **v2.14.1** (Helm chart 1.14.0)
with its `ALBGatewayAPI` feature. The retired ingress-nginx controller is not installed.

## Steps

### 1. Publish immutable images

Complete lab 15 and merge a green change. Make the GHCR packages readable by the cluster (or
configure an image-pull Secret), then replace `OWNER/REPO` and the `sha-CHANGE_ME`
placeholders in [`application.yaml`](../../deploy/gitops/argocd/application.yaml) with your
image repository and tested commit-derived `sha-...` tag. Commit and push that GitOps change.

### 2. Provision EKS 1.35

Authenticate with SSO—not access keys—and apply the saved plan:

```powershell
aws sso login --profile devops-dojo
$env:AWS_PROFILE = "devops-dojo"

Set-Location deploy/eks
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out tfplan
terraform apply tfplan
./bootstrap-gateway.ps1
Set-Location ../..

kubectl get nodes
kubectl wait gatewayclass/aws-alb --for=condition=Accepted --timeout=120s
kubectl -n kube-system rollout status deployment/aws-load-balancer-controller --timeout=300s
```

The bootstrap installs pinned standard Gateway API CRDs, the LBC-specific Gateway CRDs,
the controller through IRSA, and an `aws-alb` GatewayClass whose public learning configuration
is explicit. Read [`deploy/eks/README.md`](../../deploy/eks/README.md) before running it.

### 3. Install Argo CD and hand ownership to Git

Follow [`deploy/gitops/README.md`](../../deploy/gitops/README.md) to install Argo CD and
bootstrap the namespace/migration ConfigMap. Repeat lab 26's sealing step against this EKS
controller and commit the generated
`deploy/secrets/capstone/sealed-dojo-secrets.yaml` before the first sync;
kind-cluster ciphertext cannot be reused. The Application keeps `secrets.create=false`, so
the capstone never falls back to a plaintext Helm value. Then:

```powershell
kubectl apply -f deploy/gitops/argocd/application.yaml
kubectl -n argocd get application devops-dojo -w

kubectl -n devops-dojo wait gateway/dojo --for=condition=Programmed --timeout=600s
kubectl -n devops-dojo get pods,svc,gateway,httproute
```

The Argo application overrides the chart's local `eg` class with `aws-alb`. Obtain the
address from Gateway status rather than guessing a controller Service name:

```powershell
$address = kubectl -n devops-dojo get gateway dojo `
  -o jsonpath="{.status.addresses[0].value}"
curl.exe --fail "http://$address/api/steps"
```

### 4. Prove reconciliation and rollback

- Self-heal: scale `deployment/api` by hand and watch Argo restore the Git value.
- Delivery: change the desired replica count or commit-derived image tag in Git, merge it, and observe
  Argo reconcile without a manual `kubectl apply`.
- Rollback: revert the Git change and confirm the prior rollout becomes healthy.

Save the diff, Argo history, Gateway conditions, and one sanitized CI provenance/signature
verification as portfolio evidence.

### 5. Practice lifecycle readiness

Before any upgrade, inspect AWS upgrade insights, deprecated APIs, and add-on compatibility:

```powershell
aws eks list-insights --cluster-name devops-dojo --region eu-north-1
aws eks list-addons --cluster-name devops-dojo --region eu-north-1
kubectl get --raw /metrics | Select-String apiserver_requested_deprecated_apis
```

Document the sequence: remove deprecated APIs; update/test add-ons; back up application data;
upgrade one supported control-plane minor at a time; upgrade managed nodes; drain/observe
workloads; validate SLOs; and only then continue. EKS control-plane downgrades are not a
rollback mechanism, so readiness and application/data rollback must be proven first.

Do not mutate the capstone cluster merely to tick an upgrade checkbox. The exercise is to
produce and defend the runbook, then use it on a deliberately disposable cluster/version
transition when AWS supports that path.

### 6. Tear down and verify

Delete controller-owned load balancers before destroying the VPC:

```powershell
kubectl delete -f deploy/gitops/argocd/application.yaml --ignore-not-found
kubectl delete gateway --all --all-namespaces --ignore-not-found
kubectl -n devops-dojo delete pvc --all --ignore-not-found
kubectl get pv # wait until no capstone-owned PV remains

aws elbv2 describe-load-balancers --region eu-north-1 `
  --query "LoadBalancers[].{Name:LoadBalancerName,State:State.Code}" --output table
# Wait until the capstone ALB is gone.

Set-Location deploy/eks
terraform destroy
Set-Location ../..

aws resourcegroupstaggingapi get-resources --region eu-north-1 `
  --tag-filters Key=Project,Values=devops-dojo
```

Also check the Billing/Cost Explorer view the next day. Investigate any load balancer, NAT
gateway, EBS volume/snapshot, or other tagged resource that remains.

## Checkpoint

- EKS reports Kubernetes 1.35 and the managed nodes are Ready.
- The LBC uses IRSA, `aws-alb` is Accepted, the application Gateway is Programmed, and its
  HTTPRoute serves `/api/steps` through an internet-facing ALB.
- Argo CD is Synced/Healthy, repairs manual drift, and rolls a Git revert back safely.
- The chart-created Secret is disabled; the committed SealedSecret produces `dojo-secrets`
  without plaintext credentials in Git.
- The pod's resolved `status.containerStatuses[].imageID` digest has a verified signature,
  SBOM, and provenance from the secure CI path.
- The upgrade-readiness runbook covers insights, deprecated APIs, add-ons, control plane,
  nodes, validation, and application/data rollback.
- Terraform destroy completes and tagged/billing verification finds no leftovers.

## Common failures

- GatewayClass unaccepted → LBC feature flag or LBC-specific Gateway CRDs are missing.
- Gateway remains unprogrammed → inspect its conditions and controller logs; confirm the
  GitOps values use `gateway.className: aws-alb`.
- Gateway has only a private address → the public `LoadBalancerConfiguration` is absent or
  not referenced by the GatewayClass.
- ALB returns 503 → inspect HTTPRoute `ResolvedRefs`, Service ports, EndpointSlices, and pod
  readiness.
- Image pull error → repository visibility, pull Secret, tag, or digest is wrong.
- Terraform destroy waits on VPC → find/delete controller-created ALB/target-group/security
  resources, then retry; do not abandon billable infrastructure.

➡️ Next: [Lab 40 Part B — RDS, IRSA, restore, and EKS operations](../40-aws-core-services/)
