# AI Lab 03 — Observability & guardrails

**Run from:** the [`ai-assistant/`](../../) folder — `cd ai-assistant` from the repo root first; every command and path in this lab is relative to it.

## Concept

LLM apps fail in fuzzy ways — hallucinations, slow responses, bad retrieval. You manage that
with **guardrails** (don't answer when you shouldn't) and **observability** (measure latency,
grounding, and retrieval quality). This is what makes an LLM demo into an LLM *product*.

## What you'll do

Watch the grounding guardrail refuse out-of-scope questions, and scrape the app's LLMOps metrics.

## Steps — guardrail

```powershell
# In scope -> grounded answer with sources:
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"How does Argo Rollouts do canary?\"}'

# Out of scope -> refusal (no sources), NOT a hallucination:
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"Who won the 1998 World Cup?\"}'
```

Tighten/loosen it by changing `MIN_SCORE` (the minimum retrieval cosine score to answer) and
re-running.

## Steps — metrics

```powershell
curl http://localhost:8000/metrics | Select-String "dojo_ai_"
```

You'll see `dojo_ai_chat_requests_total{grounded="true|false"}`, `dojo_ai_chat_latency_seconds`,
and `dojo_ai_retrieval_top_score`. Bring up the bundled dashboard overlay to chart them:

```powershell
docker compose --profile local-llm -f compose.yaml -f compose.observability.yaml up -d
# Grafana http://localhost:3002 (admin/admin) -> "DevOps Dojo · AI Assistant (LLMOps)"
```

It provisions Prometheus (scraping `rag-api:8000/metrics`) and a Grafana dashboard showing
grounded ratio, request rate, latency p50/p95, and retrieval score.

## How it works

[app/rag.py](../../api/app/rag.py) calls `is_grounded()` — if the best retrieved chunk scores
below `MIN_SCORE`, it returns a canned "I don't know" instead of prompting the model, which kills
the most common hallucination path. [app/metrics.py](../../api/app/metrics.py) records latency,
the grounded label, and the top retrieval score on every request.

## Exercise

Write a Prometheus **alert rule** for "grounded ratio below 80% for 15 minutes" — a proxy for
"our docs no longer cover what users ask" — and decide what you'd do when it fires (re-ingest?
extend the docs? revisit `MIN_SCORE`?). Token and cost telemetry get their full treatment in
[AI Lab 06](../06-tokens-cost-telemetry/).

## Checkpoint

- ✅ Out-of-scope questions are refused with no sources.
- ✅ `/metrics` exposes latency, grounded counter, and retrieval-score histogram.
- ✅ You can explain two ways this app fights hallucination (grounding gate + prompt instruction).

## Common failures

- *Everything* gets refused → `MIN_SCORE` is above what your embed model actually scores;
  look at the `dojo_ai_retrieval_top_score` buckets and lower it.
- *Nothing* gets refused → `MIN_SCORE` too low — the World Cup question must NOT be answered.
- No `dojo_ai_*` series in `/metrics` → counters appear on first use; ask a question first.
- Grafana dashboard is empty → the observability overlay isn't up, or Prometheus hasn't
  scraped yet (15s interval); check Prometheus targets at :9091.
- Port conflict on 3002 → the main project's Grafana is 3001, this one is 3002; `docker ps`.

➡️ Next: [AI Lab 04 — Evaluation](../04-evaluation/)
