# Kubernetes (kind) — DevOps Dojo

Runs the whole stack on a local Kubernetes cluster. Mapping from the Compose world:

| Compose | Kubernetes |
|---------|------------|
| service | Deployment + Service |
| named volume | PersistentVolumeClaim (StatefulSet for Postgres) |
| `.env` / environment | ConfigMap + Secret |
| one-shot `migrate` | Job |
| Caddy / published ports | Ingress |
| `--scale` | `replicas` + HorizontalPodAutoscaler |

## 1. Create the cluster

```powershell
kind create cluster --config deploy/k8s/kind/kind-cluster.yaml
```

## 2. Install the ingress-nginx controller

```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod `
  --selector=app.kubernetes.io/component=controller --timeout=120s
```

## 3. Build & load images into kind (no registry needed)

```powershell
docker build -t devops-dojo/api:dev ./app/api
docker build -t devops-dojo/frontend:dev ./app/frontend
kind load docker-image devops-dojo/api:dev devops-dojo/frontend:dev
```

## 4. Namespace, migrations ConfigMap, then apply

```powershell
kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
kubectl apply -f deploy/k8s/base/
```

## 5. Watch it come up

```powershell
kubectl -n devops-dojo get pods,svc,ingress
kubectl -n devops-dojo wait --for=condition=available deploy/api deploy/frontend --timeout=180s
```

Open <http://localhost/> and <http://localhost/api/steps>.

## Optional: HPA autoscaling

The HPA needs metrics-server (not in kind by default):

```powershell
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
# kind uses self-signed kubelet certs; allow them:
kubectl -n kube-system patch deployment metrics-server --type=json `
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

## Teardown

```powershell
kind delete cluster
```

## Notes

- Images use `imagePullPolicy: IfNotPresent` and are side-loaded with `kind load` — no
  registry required for local learning. For a real cluster, push to GHCR (lab 13/15) and set
  the image to `ghcr.io/<owner>/<repo>/api:<tag>`.
- The Secret here holds a demo password. In production use sealed-secrets / external-secrets
  or your cloud's secret manager.
