# DevOps Dojo — AI Assistant 🤖

A **local, private RAG assistant** that answers questions about the DevOps Dojo project by
retrieving from its own docs and labs — with **no cloud API and no data leaving your machine**.
It runs a local LLM via **Ollama** (or **LM Studio**), embeds and stores chunks in **Qdrant**,
and serves grounded, cited answers from a **FastAPI** service.

This is the portfolio's **LLMOps** project: it shows you can build, operate, observe, evaluate,
containerize, and deploy an LLM application — the skills employers now ask for — on top of the
same DevOps foundations as the main project.

## Architecture

```
Browser ──▶ FastAPI (rag-api)
                │   1. embed(question) ─────────▶ Ollama / LM Studio   (OpenAI-compatible API)
                │   2. search top-k ───────────▶ Qdrant (vector DB)
                │   3. ground-check (MIN_SCORE) → refuse if weak
                │   4. chat(context+question) ─▶ Ollama / LM Studio ──▶ grounded answer + [citations]
                └── /metrics (Prometheus)  /healthz  /readyz
    (ingest: docs/ + labs/  ──chunk──embed──▶ Qdrant)
```

One switch for the backend — **`OPENAI_BASE_URL`**:
- Ollama (default): `http://ollama:11434/v1`
- LM Studio: start its local server, then `http://host.docker.internal:1234/v1`

Both expose the OpenAI-compatible API, so the code is identical either way.

## Quickstart (Ollama, all local)

From `ai-assistant/`:

```powershell
docker compose up -d --build
docker compose exec ollama ollama pull llama3.2:3b      # chat model
docker compose exec ollama ollama pull nomic-embed-text  # embedding model
docker compose run --rm ingest                           # index docs/ + labs/ into Qdrant
```

Open <http://localhost:8000> and ask *"How do I autoscale the worker with KEDA?"* — you get an
answer grounded in the labs, with source citations. Ask *"What's the capital of France?"* and it
**refuses** (out of scope) — that's the grounding guardrail working.

```powershell
# API directly (non-streaming and streaming):
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"How do backups work?\"}'
curl -N http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"How do backups work?\",\"stream\":true}'
```

## LLMOps you can point to

| Concern | How it's done here |
|---------|--------------------|
| Retrieval-augmented generation | chunk → embed → Qdrant → retrieve → prompt with context |
| Grounding / anti-hallucination | `MIN_SCORE` gate + "answer only from context, cite sources, else say you don't know" |
| Observability | Prometheus `/metrics`: latency, grounded ratio, retrieval score; `/healthz` `/readyz` |
| Evaluation | `eval/` harness scores retrieval + answer quality (incl. a must-refuse case) |
| Backend portability | one env var swaps Ollama ↔ LM Studio (OpenAI-compatible) |
| Packaging & delivery | non-root Docker image, Compose stack, CI (unit tests + build), K8s manifests |
| Cost/latency | fully local (no token cost); metrics expose latency to reason about model size/GPU |

## Layout

```
api/app/      config, llm (OpenAI-compat), embeddings, vectorstore (Qdrant), chunk, rag, ingest, metrics, main
api/web/      minimal chat UI
api/tests/    unit tests (chunking, prompt/grounding)
eval/         RAG evaluation harness + dataset
k8s/          Kubernetes manifests (Ollama, Qdrant, rag-api, ingest Job, Ingress)
compose.yaml  local stack (Ollama + Qdrant + rag-api + ingest)
labs/         LLMOps labs (01–05)
```

## Labs

Work through [labs/](labs/) 01→05: run a local model, build the RAG pipeline, add observability
& guardrails, evaluate, then containerize & deploy (Compose → Kubernetes).

## Deploy on Kubernetes

See [k8s/README.md](k8s/README.md) — reference manifests with GPU/model-pull caveats. The
Compose path is the fully-local, verified-runnable one; K8s shows the same stack orchestrated.

## Interview framing

> "I built a private RAG assistant over internal docs: local LLM via Ollama (LM Studio-
> compatible), Qdrant for vectors, a FastAPI service with grounding guardrails so it refuses
> out-of-scope questions, Prometheus metrics for latency and retrieval quality, an eval harness
> in the loop, and it ships as a container/Compose/K8s stack. Swapping the model backend is one
> env var." That's an end-to-end LLMOps story most candidates can't demonstrate.
