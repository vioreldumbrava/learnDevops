# AI Lab 02 — Build the RAG pipeline

## Concept

An LLM only knows its training data. **Retrieval-Augmented Generation (RAG)** gives it *your*
knowledge at query time: split docs into **chunks**, turn each into an **embedding** (a vector),
store them in a **vector DB**, then for each question retrieve the most similar chunks and put
them in the prompt. The model answers from *your* content — and cites it.

## What you'll do

Index the DevOps Dojo docs/labs and ask grounded, cited questions.

## Steps

```powershell
cd ai-assistant
docker compose --profile local-llm up -d --build   # ollama, qdrant, rag-api
# (models pulled in lab 01; for a REMOTE model omit --profile local-llm and set OPENAI_BASE_URL)
docker compose run --rm ingest        # chunk + embed docs/ + labs/ into Qdrant

# Ask via the API:
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"How do I run migrations?\"}'
```

Inspect what was stored:

```powershell
curl http://localhost:6333/collections/dojo_docs      # Qdrant collection info + point count
```

Open <http://localhost:8000> and try a few questions; note the **source citations** under each answer.

## How it works

- [app/ingest.py](../../api/app/ingest.py): reads markdown, [app/chunk.py](../../api/app/chunk.py)
  packs paragraphs into ~900-char chunks with overlap, [app/llm.py](../../api/app/llm.py) embeds
  them, [app/vectorstore.py](../../api/app/vectorstore.py) upserts into Qdrant.
- [app/rag.py](../../api/app/rag.py): embeds the question, retrieves `FETCH_K` candidates,
  **MMR-reranks** them ([app/rerank.py](../../api/app/rerank.py)) down to `TOP_K` for relevance
  *and* diversity, builds a prompt that says *"answer only from this context and cite [n]"*, and
  calls the model. It also folds in recent conversation `history` for multi-turn follow-ups.

## Exercise

Tune retrieval: change `TOP_K` (e.g., 2 vs 8) and `CHUNK_SIZE`, re-ingest, and compare answer
quality. Too few chunks → misses; too many → noise and slower/longer prompts. That trade-off is
the heart of RAG tuning.

## Checkpoint

- ✅ `docker compose run --rm ingest` reports chunks indexed from many files.
- ✅ Qdrant's `dojo_docs` collection has points.
- ✅ Answers include citations pointing at real `docs/`/`labs/` files.

## Common failures

- Every answer is "I don't know" → the collection is empty: run
  `docker compose run --rm ingest` and confirm it printed indexed chunk counts.
- `ingest` fails immediately → the embed model isn't pulled (lab 01), or
  `OPENAI_BASE_URL` points at nothing.
- Qdrant 404 on the collection URL → ingest never ran, or it wrote to a different
  Qdrant (check `QDRANT_URL`).
- Re-ingesting doubles the point count → upserts use random IDs, so re-runs append;
  `docker compose down -v` wipes for a clean index.
- Citations look irrelevant → tune `CHUNK_SIZE`/`TOP_K` — and use lab 08's eval to
  measure the change instead of eyeballing it.

➡️ Next: [AI Lab 03 — Observability & guardrails](../03-observability-guardrails/)
