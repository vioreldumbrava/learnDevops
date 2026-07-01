# AI Lab 03 — Observability & guardrails

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

Add a **token/cost** metric: record the response length (or usage if your backend returns it) as
a histogram, and reason about how model size affects latency. Then write a Prometheus alert for
"grounded ratio dropped" — a proxy for "our docs no longer cover what users ask."

## Checkpoint

- ✅ Out-of-scope questions are refused with no sources.
- ✅ `/metrics` exposes latency, grounded counter, and retrieval-score histogram.
- ✅ You can explain two ways this app fights hallucination (grounding gate + prompt instruction).

➡️ Next: [AI Lab 04 — Evaluation](../04-evaluation/)
