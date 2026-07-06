# AI Lab 01 — Run a local LLM (Ollama / LM Studio)

**Run from:** the [`ai-assistant/`](../../) folder — `cd ai-assistant` from the repo root first; every command and path in this lab is relative to it.

## Concept

You don't need a cloud API to build LLM apps. **Ollama** and **LM Studio** both run models
locally and expose an **OpenAI-compatible** HTTP API, so the same client code works against
either — and against OpenAI later. Local means private, free per-token, and offline.

## What you'll do

Start a local model and call it two ways: the native API and the OpenAI-compatible one.

## Steps — Ollama (via Compose)

```powershell
cd ai-assistant
docker compose --profile local-llm up -d ollama    # local model is opt-in via the profile
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull nomic-embed-text

# OpenAI-compatible chat (what our app uses):
curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" -d '{\"model\":\"llama3.2:3b\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hi in 5 words\"}]}'

# OpenAI-compatible embeddings:
curl http://localhost:11434/v1/embeddings -H "Content-Type: application/json" -d '{\"model\":\"nomic-embed-text\",\"input\":\"hello world\"}'
```

## Steps — LM Studio (alternative)

1. Install LM Studio, download a chat model + an embedding model, and start its **local server**
   (Developer tab). It serves the OpenAI API at `http://localhost:1234/v1`.
2. Point our app at it instead of the container: set `OPENAI_BASE_URL=http://host.docker.internal:1234/v1`.

## Steps — a model server on ANOTHER PC

You don't have to run the model locally at all. Point at Ollama/LM Studio on another machine
(e.g. a GPU box on your LAN): expose it on the network and set `OPENAI_BASE_URL` to its IP — full
walkthrough + security notes in the [project README](../../README.md#connect-to-a-model-server-on-another-pc).
Then start **without** the profile: `docker compose up -d` (only Qdrant + the API run here).

## How it works

Ollama serves both a native API (`/api/...`) and an OpenAI-compatible one (`/v1/...`). Our app
([app/llm.py](../../api/app/llm.py)) uses the `openai` SDK pointed at `OPENAI_BASE_URL`, so the
backend is a config choice, not a code change — the portability lesson that matters in real jobs.

## Checkpoint

- ✅ `ollama list` shows a chat model and `nomic-embed-text`.
- ✅ The `/v1/chat/completions` call returns text; `/v1/embeddings` returns a vector.

- ✅ You can explain why "OpenAI-compatible" lets you swap Ollama ↔ LM Studio ↔ OpenAI.

## Common failures

- `/v1/chat/completions` 404s or errors → the model isn't pulled yet
  (`docker compose exec ollama ollama list`) or the model name in the request is typo'd.
- `connection refused` on :11434 → the `ollama` service isn't up — it's opt-in:
  `--profile local-llm`.
- LM Studio answers in your browser but not from the container → inside a container
  `localhost` is the container; use `host.docker.internal:1234`.
- A remote server works with curl from your PC but not from the stack → remote Ollama binds
  127.0.0.1 by default; set `OLLAMA_HOST=0.0.0.0` on that machine (and mind the security notes).
- First response is very slow → cold start: the model loads into RAM on first use.

➡️ Next: [AI Lab 02 — Build the RAG pipeline](../02-rag-pipeline/)
