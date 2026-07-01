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

One switch for the backend — **`OPENAI_BASE_URL`** — with three ways to run the model:

| Mode | `OPENAI_BASE_URL` | Start with |
|------|-------------------|------------|
| **Local** (Ollama in Compose) | `http://ollama:11434/v1` | `docker compose --profile local-llm up -d` |
| **Remote** Ollama on another PC | `http://<pc-ip>:11434/v1` | `docker compose up -d` |
| **Remote** LM Studio on another PC | `http://<pc-ip>:1234/v1` | `docker compose up -d` |

The local Ollama is behind the `local-llm` **profile**, so without it `docker compose up` starts
only Qdrant + the API and talks to whatever `OPENAI_BASE_URL` points at. Everything speaks the
OpenAI-compatible API, so the code is identical either way. See
[Connect to a model server on another PC](#connect-to-a-model-server-on-another-pc).

## Quickstart (local model, all on this machine)

From `ai-assistant/` (keep `OPENAI_BASE_URL=http://ollama:11434/v1` in `.env`):

```powershell
docker compose --profile local-llm up -d --build         # starts Ollama + Qdrant + rag-api
docker compose exec ollama ollama pull llama3.2:3b        # chat model
docker compose exec ollama ollama pull nomic-embed-text   # embedding model
docker compose run --rm ingest                            # index docs/ + labs/ into Qdrant
```

Open <http://localhost:8000> and ask *"How do I autoscale the worker with KEDA?"* — you get an
answer grounded in the labs, with source citations. Ask *"What's the capital of France?"* and it
**refuses** (out of scope) — that's the grounding guardrail working.

```powershell
# API directly (non-streaming and streaming):
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"How do backups work?\"}'
curl -N http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"How do backups work?\",\"stream\":true}'
# Multi-turn (send prior turns as history):
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"and how do I restore it?\",\"history\":[{\"role\":\"user\",\"content\":\"how do backups work?\"},{\"role\":\"assistant\",\"content\":\"Use db-backup...\"}]}'
```

## Connect to a model server on another PC

Don't want to run the model here? Point the assistant at an Ollama or LM Studio server running
on another machine (e.g. a GPU box on your LAN). Only Qdrant + the API run locally.

1. **Expose the model server on the network** (by default both bind to localhost only):
   - **Ollama** on the other PC: set `OLLAMA_HOST=0.0.0.0:11434` and restart Ollama, then allow
     port `11434` through its firewall. Pull the models *there*:
     `ollama pull llama3.2:3b` and `ollama pull nomic-embed-text`.
   - **LM Studio** on the other PC: in the **Developer/Server** tab enable **"Serve on Local
     Network"** (binds `0.0.0.0:1234`) and load a chat model **and** an embedding model.
2. **Point this app at it** — in `.env`:
   ```env
   OPENAI_BASE_URL=http://192.168.1.50:11434/v1   # that PC's IP (LM Studio: :1234)
   ```
3. **Start without the local model** and index:
   ```powershell
   docker compose up -d --build         # note: NO --profile local-llm
   docker compose run --rm ingest
   curl http://localhost:8000/readyz    # "llm":"ok" confirms the remote is reachable
   ```

> 🔒 **Security:** Ollama and LM Studio have **no authentication** and serve **plaintext HTTP** —
> fine on a trusted LAN, but never expose them to the internet directly. For remote access use a
> VPN / **Tailscale**, an **SSH tunnel**, or an authenticating reverse proxy in front. The models
> (chat + embedding) must exist on the remote server.

On Kubernetes, do the same by setting `OPENAI_BASE_URL` in
[k8s/configmap.yaml](k8s/configmap.yaml) to the remote and skipping `k8s/ollama.yaml`.

### Dashboards & nightly eval

```powershell
# LLMOps dashboard: Grafana at http://localhost:3002 (admin/admin), Prometheus at :9091
docker compose -f compose.yaml -f compose.observability.yaml up -d
```

The eval harness also runs on a schedule in CI
([ai-assistant-eval.yml](../.github/workflows/ai-assistant-eval.yml)) against a small CPU model.

## LLMOps you can point to

| Concern | How it's done here |
|---------|--------------------|
| Retrieval-augmented generation | chunk → embed → Qdrant → retrieve → prompt with context |
| Retrieval quality | **MMR re-ranking** (over-fetch `FETCH_K`, diversify to `TOP_K`) — relevance without redundancy |
| Conversation memory | multi-turn `history` in the chat request, folded into the prompt |
| Grounding / anti-hallucination | `MIN_SCORE` gate + "answer only from context, cite sources, else say you don't know" |
| Observability | Prometheus `/metrics` (latency, grounded ratio, retrieval score) + a provisioned **Grafana dashboard** overlay; `/healthz` `/readyz` |
| Evaluation | `eval/` harness scores retrieval + answer quality (incl. a must-refuse case), plus a **nightly CI** run |
| Backend portability | one env var swaps Ollama ↔ LM Studio (OpenAI-compatible) |
| Packaging & delivery | non-root Docker image, Compose stack, CI (unit tests + build), K8s manifests |
| Cost/latency | fully local (no token cost); metrics expose latency to reason about model size/GPU |

## Layout

```
api/app/       config, llm (OpenAI-compat), embeddings, vectorstore (Qdrant), chunk, rerank (MMR), rag, ingest, metrics, main
api/web/       minimal chat UI
api/tests/     unit tests (chunking, MMR re-rank, prompt/grounding/memory)
eval/          RAG evaluation harness + dataset
observability/ Prometheus + Grafana overlay (LLMOps dashboard)
k8s/           Kubernetes manifests (Ollama, Qdrant, rag-api, ingest Job, Ingress)
compose.yaml   local stack (Ollama + Qdrant + rag-api + ingest)
labs/          LLMOps labs (01–05)
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
