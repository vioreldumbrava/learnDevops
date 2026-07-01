# AI Lab 01 — Run a local LLM (Ollama / LM Studio)

## Concept

You don't need a cloud API to build LLM apps. **Ollama** and **LM Studio** both run models
locally and expose an **OpenAI-compatible** HTTP API, so the same client code works against
either — and against OpenAI later. Local means private, free per-token, and offline.

## What you'll do

Start a local model and call it two ways: the native API and the OpenAI-compatible one.

## Steps — Ollama (via Compose)

```powershell
cd ai-assistant
docker compose up -d ollama
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

## How it works

Ollama serves both a native API (`/api/...`) and an OpenAI-compatible one (`/v1/...`). Our app
([app/llm.py](../../api/app/llm.py)) uses the `openai` SDK pointed at `OPENAI_BASE_URL`, so the
backend is a config choice, not a code change — the portability lesson that matters in real jobs.

## Checkpoint

- ✅ `ollama list` shows a chat model and `nomic-embed-text`.
- ✅ The `/v1/chat/completions` call returns text; `/v1/embeddings` returns a vector.
- ✅ You can explain why "OpenAI-compatible" lets you swap Ollama ↔ LM Studio ↔ OpenAI.

➡️ Next: [AI Lab 02 — Build the RAG pipeline](../02-rag-pipeline/)
