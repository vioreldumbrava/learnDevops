# AI Assistant on Kubernetes (reference)

Runs the same stack as Compose — Ollama, Qdrant, rag-api — on Kubernetes. Treat this as a
**reference**: running LLMs on K8s adds real concerns (large model images, a models PVC, and
GPU scheduling for anything beyond small models). The Compose path is the fully-local,
verified-runnable one; this shows the orchestrated equivalent.

## Apply

```powershell
# Build + load the API image (kind) or push it to a registry first:
docker build -t dojo-ai/rag-api:dev ./ai-assistant/api
kind load docker-image dojo-ai/rag-api:dev        # if using kind

kubectl apply -f ai-assistant/k8s/namespace.yaml
kubectl apply -f ai-assistant/k8s/           # config, qdrant, ollama, rag-api, ingress

# Pull models into the Ollama pod (once; stored on the PVC):
kubectl -n dojo-ai exec deploy/ollama -- ollama pull llama3.2:3b
kubectl -n dojo-ai exec deploy/ollama -- ollama pull nomic-embed-text

# Index the docs (set REPO_URL in ingest-job.yaml first):
kubectl apply -f ai-assistant/k8s/ingest-job.yaml
kubectl -n dojo-ai wait --for=condition=complete job/ingest --timeout=600s

kubectl -n dojo-ai get pods,svc,ingress
```

Open the Ingress address (http://localhost/ on kind with ingress-nginx).

## Caveats (say these in interviews — they show maturity)

- **Model size & GPU:** CPU is fine for small models (llama3.2:3b); larger models need a GPU
  node (NVIDIA device plugin + `resources.limits: nvidia.com/gpu: 1` on the Ollama pod).
- **Model storage:** models live on the `ollama-models` PVC so they survive restarts and aren't
  baked into images. Pull once.
- **Cold start:** the first request after a pull loads the model into memory (latency spike).
- **Scaling:** `rag-api` is stateless → scale freely. Ollama is stateful-ish (model cache) and
  GPU-bound → scale carefully / use a dedicated inference tier.

## Teardown

```powershell
kubectl delete namespace dojo-ai
```
