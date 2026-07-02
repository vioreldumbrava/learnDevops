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
docker compose --profile local-llm up -d --build   # or omit the profile + set a remote OPENAI_BASE_URL
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
ingest; CI ([ai-assistant-ci.yml](../../.github/workflows/ai-assistant-ci.yml)) runs unit tests,
builds the image, and **Trivy-scans it with the same CRITICAL gate as the main app** (lab 41);
[k8s/](../../ai-assistant/k8s/) orchestrates the same stack.

## Exercise — apply the hardening you already know

This project ships the K8s baseline you built for the main app in labs 26–28. Apply and inspect it:

```powershell
kubectl apply -f k8s/          # now includes networkpolicy.yaml, pdb.yaml, hpa.yaml, secret.yaml
kubectl -n dojo-ai get networkpolicy,pdb,hpa
kubectl -n dojo-ai describe networkpolicy default-deny
```

Then reason about each: the **NetworkPolicy** is default-deny + explicit allows (rag-api→qdrant,
rag-api→ollama, ingress→rag-api) — the lab 28 pattern; the **PDB** keeps one rag-api serving
through a node drain; the **HPA** scales the stateless API tier on CPU (but *not* generation
throughput — that's bounded by the model server); the API key moved from the ConfigMap into a
**Secret** (config vs credentials). Enforcement of NetworkPolicies needs a real CNI (Calico) —
kindnet accepts but ignores them, exactly as in lab 28.

## Checkpoint

- ✅ The Compose stack serves grounded answers at :8000.
- ✅ (K8s) pods are Running and the app answers through the Ingress.
- ✅ `kubectl -n dojo-ai get networkpolicy,pdb,hpa` shows the hardening applied.
- ✅ You can name three ways operating an LLM service differs from a stateless web app.

## Common failures

- Pods `ImagePullBackOff` on kind → you didn't `kind load docker-image dojo-ai/rag-api:dev`
  (there's no registry), or the tag differs.
- `readyz` never passes → the model server is unreachable (`OPENAI_BASE_URL`/ollama not up)
  or the embed model isn't pulled; readiness checks both Qdrant and the LLM.
- With NetworkPolicies applied, rag-api can't reach Qdrant/Ollama → your CNI enforces them
  and a label doesn't match (`app: qdrant`/`app: ollama`); `kubectl describe networkpolicy`.
- HPA shows `<unknown>` targets → metrics-server isn't installed (see the main
  [deploy/k8s/README.md](../../deploy/k8s/README.md)).
- ingest Job can't clone → `OWNER/REPO` placeholder in `ingest-job.yaml` isn't set to your fork.

➡️ Next: [AI Lab 06 — Tokens, cost & telemetry](../06-tokens-cost-telemetry/)
(Milestone: LLMOps depth — the labs that turn a demo into an operable service.)
