# AI Lab 05 — Containerize & deploy

## Concept

An LLM app is still a normal service to operate — plus some LLM-specific wrinkles (large model
files, model pulls, GPU). You already know the DevOps: containerize, Compose, CI, Kubernetes.
This lab applies them to the assistant and names what's different.

## What you'll do

Run the whole stack via Compose (done in earlier labs), then deploy the same stack to Kubernetes.

## Steps — Compose (local, verified path)

```powershell
cd ai-assistant
docker compose up -d --build
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull nomic-embed-text
docker compose run --rm ingest
# http://localhost:8000
```

## Steps — Kubernetes

Follow [../k8s/README.md](../k8s/README.md):

```powershell
docker build -t dojo-ai/rag-api:dev ./api
kind load docker-image dojo-ai/rag-api:dev
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
kubectl -n dojo-ai exec deploy/ollama -- ollama pull llama3.2:3b
kubectl -n dojo-ai exec deploy/ollama -- ollama pull nomic-embed-text
kubectl apply -f k8s/ingest-job.yaml     # set REPO_URL first
```

## What's different from a normal service

- **Model artifacts** are large — keep them on a **PVC/volume**, pull once; don't bake into images.
- **GPU** for anything beyond small models: NVIDIA device plugin + `resources.limits: nvidia.com/gpu`.
- **Cold start**: first request loads the model into memory (latency spike) — warm it or accept it.
- **Stateless vs stateful**: `rag-api` scales freely; the inference tier (Ollama/GPU) is the
  bottleneck you scale deliberately.

## How it works

The [Dockerfile](../../ai-assistant/api/Dockerfile) is a slim, non-root Python image; the
[compose.yaml](../../ai-assistant/compose.yaml) wires Ollama + Qdrant + rag-api + a one-shot
ingest; CI ([ai-assistant-ci.yml](../../.github/workflows/ai-assistant-ci.yml)) runs unit tests
and builds the image; [k8s/](../../ai-assistant/k8s/) orchestrates the same stack.

## Checkpoint

- ✅ The Compose stack serves grounded answers at :8000.
- ✅ (K8s) pods are Running and the app answers through the Ingress.
- ✅ You can name three ways operating an LLM service differs from a stateless web app.

🎉 You now have a second, LLMOps-focused project. Pair it with the main DevOps Dojo in your
portfolio and the [interview talk track](../../docs/INTERVIEW_PREP.md).
