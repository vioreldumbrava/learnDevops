# AI Assistant on Kubernetes (reference)

Runs the Compose Ollama, Qdrant, and RAG API stack on Kubernetes. Treat this as
a reference: running LLMs on Kubernetes adds model-image, storage, and GPU
scheduling concerns. The Compose path remains the fully local path.

The HTTPRoute attaches to the main local `devops-dojo/dojo` Gateway, so install
Envoy Gateway and the base application by following `deploy/k8s/README.md`
first. The AI endpoint uses the hostname `ai.dojo.localhost`.

## Apply

```powershell
# Build and load the API image (kind), or push an immutable tag to a registry:
docker build -t dojo-ai/rag-api:dev ./ai-assistant/api
kind load docker-image dojo-ai/rag-api:dev

kubectl apply -f ai-assistant/k8s/namespace.yaml
# Apply the long-lived stack explicitly. Do not create the one-shot ingest Job
# until its repository URL is real and Ollama has the embedding model.
kubectl apply `
  -f ai-assistant/k8s/configmap.yaml `
  -f ai-assistant/k8s/secret.yaml `
  -f ai-assistant/k8s/qdrant.yaml `
  -f ai-assistant/k8s/ollama.yaml `
  -f ai-assistant/k8s/rag-api.yaml `
  -f ai-assistant/k8s/hpa.yaml `
  -f ai-assistant/k8s/pdb.yaml `
  -f ai-assistant/k8s/networkpolicy.yaml `
  -f ai-assistant/k8s/httproute.yaml

# Pull models once; the PVC retains them:
kubectl -n dojo-ai exec deploy/ollama -- ollama pull llama3.2:3b
kubectl -n dojo-ai exec deploy/ollama -- ollama pull nomic-embed-text

# Index the docs after replacing OWNER/REPO in ingest-job.yaml. Delete an old
# Job first because a Job's pod template is immutable and apply does not rerun it:
kubectl -n dojo-ai delete job ingest --ignore-not-found
kubectl apply -f ai-assistant/k8s/ingest-job.yaml
kubectl -n dojo-ai wait --for=condition=complete job/ingest --timeout=600s

kubectl -n dojo-ai get pods,svc,httproute
curl.exe --fail --header "Host: ai.dojo.localhost" http://localhost/healthz
```

Open <http://ai.dojo.localhost/>.

## Caveats

- **Model size and GPU:** CPU is adequate for small models such as
  `llama3.2:3b`; larger models need a GPU node, the NVIDIA device plugin, and a
  GPU resource limit on the Ollama pod.
- **Model storage:** models live on the `ollama-models` PVC so they survive
  restarts and are not baked into images.
- **Cold start:** the first request after a pull loads the model into memory and
  has higher latency.
- **Scaling:** `rag-api` is stateless and scales horizontally. Ollama is
  stateful-ish and GPU-bound, so it needs a deliberately designed inference
  tier before scaling.

## Teardown

```powershell
kubectl delete namespace dojo-ai
```
