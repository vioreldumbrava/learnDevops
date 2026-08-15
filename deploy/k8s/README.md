# Kubernetes (kind) — DevOps Dojo

Runs the whole stack on a local Kubernetes cluster. Mapping from Compose:

| Compose | Kubernetes |
|---------|------------|
| service | Deployment + Service |
| named volume | PersistentVolumeClaim (StatefulSet for Postgres) |
| `.env` / environment | ConfigMap + Secret |
| one-shot `migrate` | Job |
| Caddy / published ports | Gateway + HTTPRoute |
| `--scale` | `replicas` + HorizontalPodAutoscaler |

The supported local entry point is Gateway API with Envoy Gateway v1.8.3.
ingress-nginx is retained only under `deploy/k8s/legacy/` as a historical
migration comparison.

## 1. Create the cluster

The kind configuration maps host ports 80/443 to fixed Envoy NodePorts
30080/30443. Port 30443 is reserved for the HTTPS listener exercise.

```powershell
kind create cluster --config deploy/k8s/kind/kind-cluster.yaml
```

## 2. Install Envoy Gateway v1.8.3

The pinned chart installs both the compatible Gateway API CRDs and Envoy
Gateway CRDs. The local `GatewayClass` selects its controller.

```powershell
helm install eg oci://docker.io/envoyproxy/gateway-helm --version v1.8.3 `
  --namespace envoy-gateway-system --create-namespace
kubectl wait --namespace envoy-gateway-system --for=condition=Available `
  deployment/envoy-gateway --timeout=300s
kubectl apply -f deploy/k8s/gateway/gatewayclass.yaml
kubectl wait --for=condition=Accepted gatewayclass/eg --timeout=180s
```

## 3. Build and load images into kind

```powershell
docker build -t devops-dojo/api:dev ./app/api
docker build -t devops-dojo/frontend:dev ./app/frontend
kind load docker-image devops-dojo/api:dev devops-dojo/frontend:dev
```

## 4. Create the namespace, migration input, and application

```powershell
kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
kubectl apply -f deploy/k8s/base/
```

`base/gateway.yaml` configures Envoy's generated Service as NodePort 30080 so
the kind port mapping remains deterministic.

## 5. Verify routing

```powershell
kubectl -n devops-dojo wait --for=condition=Available `
  deployment/api deployment/frontend --timeout=180s
kubectl -n devops-dojo wait --for=condition=Programmed gateway/dojo --timeout=180s
kubectl -n devops-dojo wait `
  --for=jsonpath="{.status.parents[0].conditions[?(@.type=='Accepted')].status}"=True `
  httproute/dojo --timeout=180s
kubectl -n devops-dojo wait `
  --for=jsonpath="{.status.parents[0].conditions[?(@.type=='ResolvedRefs')].status}"=True `
  httproute/dojo --timeout=180s
kubectl -n devops-dojo get pods,svc,gateway,httproute
curl.exe --fail http://localhost/api/steps
```

Open <http://localhost/> and <http://localhost/api/steps>.

## Helm chart

The application chart also defaults to Gateway API. Its workloads satisfy the
Restricted Pod Security Standard. Install the `eg` GatewayClass first, create a
namespace with enforcement labels, then render or install the chart:

```powershell
kubectl create namespace devops-dojo
kubectl label namespace devops-dojo `
  pod-security.kubernetes.io/enforce=restricted `
  pod-security.kubernetes.io/enforce-version=v1.35 `
  pod-security.kubernetes.io/audit=restricted `
  pod-security.kubernetes.io/warn=restricted
helm lint deploy/k8s/helm/devops-dojo
helm template dojo deploy/k8s/helm/devops-dojo --namespace devops-dojo
```

The chart default also renders the local `EnvoyProxy` and fixed NodePort wiring.
Cloud releases set `gateway.localEnvoyProxy.enabled=false`; multi-environment
releases can set `gateway.create=false` plus `gateway.parentNamespace` to attach
only their HTTPRoute to a platform-owned Gateway.

For the historical migration exercise only, disable `gateway.enabled` and
enable `ingress.enabled`; that path requires an Ingress controller supplied by
the learner. Raw-manifest users apply `deploy/k8s/legacy/` to include the
Ingress and its narrowly scoped companion NetworkPolicies.

## Optional: HPA autoscaling

The HPA needs metrics-server (not installed by kind). The release URL is pinned
to v0.9.0 rather than tracking a moving `latest` asset:

```powershell
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml
# kind uses self-signed kubelet certificates:
kubectl -n kube-system patch deployment metrics-server --type=json `
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

## Teardown

```powershell
kind delete cluster
```

## Notes

- Images use `imagePullPolicy: IfNotPresent` and are side-loaded with `kind load`,
  so local learning needs no registry. For a real cluster, push immutable image
  tags to GHCR and override the chart values.
- The local Secret has a demo password. Use Sealed Secrets, External Secrets, or
  the cloud provider's secrets manager outside this learning cluster.
- Both application namespaces enforce the Restricted Pod Security Standard.
  Workloads run without privilege escalation or Linux capabilities, use the
  runtime-default seccomp profile, and use read-only root filesystems plus
  explicit writable volumes.
- Scheduling and storage drills intentionally use the cluster's `default`
  namespace so their existing commands and scheduler observations remain
  focused. Lab manifests still satisfy Restricted admission controls. The
  stock nginx scheduling fixture keeps a writable root filesystem because its
  entrypoint initializes runtime directories; this is the documented narrow
  exception to the read-only-root hardening used by application workloads.
