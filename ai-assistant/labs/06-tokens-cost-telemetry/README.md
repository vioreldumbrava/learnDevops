# AI Lab 06 — Tokens, cost & telemetry

**Run from:** the [`ai-assistant/`](../../) folder — `cd ai-assistant` from the repo root first; every command and path in this lab is relative to it.

## Concept

You can't operate an LLM service you can't see into. Lab 03 gave you latency, grounding, and
retrieval score — the *demo* signals. Production adds three questions those don't answer:
**where does the time actually go?** (embed vs retrieve vs generate), **what does each request
cost?** (tokens), and **which request was that?** (a slow one at 3am, with a request ID you can
grep). Then, once you can measure, you **optimize**: a semantic cache so near-duplicate
questions skip generation entirely.

The arc is one loop every ops engineer runs: **measure → observe → optimize**.

## What you'll do

Turn on token accounting, per-stage timing, structured logs, and the answer cache; watch them
all in Grafana; prove the cache changes the numbers.

## Steps — see the new signals

```powershell
cd ai-assistant
docker compose --profile local-llm up -d --build
docker compose run --rm ingest
# ask a few questions (web UI at :8000 or curl), then:
curl http://localhost:8000/metrics | Select-String "dojo_ai_(tokens|stage|time_to_first|cache|app_info)"
```

You'll see `dojo_ai_tokens_total{kind,source}`, `dojo_ai_stage_latency_seconds{stage}`,
`dojo_ai_time_to_first_token_seconds`, `dojo_ai_cache_events_total{result}`, and
`dojo_ai_app_info{prompt_version,chat_model}`.

## Steps — request IDs in the logs

```powershell
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -H "X-Request-ID: demo-42" -d '{\"question\":\"How do I run migrations?\"}' | Out-Null
docker compose logs rag-api --tail=5
```

The response carries `X-Request-ID: demo-42` back, and the JSON log line for that request
includes `"request_id":"demo-42"` alongside `duration_ms`, `grounded`, token counts, and the
cache state. Send no header and the server mints one — either way every log line for a request
is correlated.

## Steps — turn on the semantic cache

```powershell
$env:CACHE_ENABLED="true"; docker compose up -d rag-api    # restart with cache on
# ask the SAME question twice:
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"How do I autoscale the worker with KEDA?\"}'
curl -s http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"question\":\"How do I autoscale the worker with KEDA?\"}'
```

The second response comes back near-instantly with `"cached": true`, and
`dojo_ai_cache_events_total{result="hit"}` increments.

## Steps — the dashboard

```powershell
docker compose --profile local-llm -f compose.yaml -f compose.observability.yaml up -d
# Grafana http://localhost:3002 (admin/admin): tokens/min, stage-latency p95, TTFT, cache hit
# ratio, and an "estimated cost at hosted-API prices" panel.
```

## How it works

- **Tokens.** [app/llm.py](../../api/app/llm.py) reads the `usage` block the OpenAI-compatible
  API returns (Ollama reports it; for streaming it's requested via
  `stream_options={"include_usage": true}`). If a backend omits it, we fall back to a
  `len(text)//4` estimate, **labeled `source="estimated"`** so dashboards never confuse a
  guess with a real count. A tokenizer library would be *wrong* here — token counts are the
  serving backend's to define, not tiktoken's (which only matches OpenAI's models).
- **Stages.** [app/rag.py](../../api/app/rag.py) times `embed`, `search`, `rerank`, and
  `generate` into `dojo_ai_stage_latency_seconds{stage}`, and records time-to-first-token in
  the streaming path — the metric users actually feel.
- **Logs.** [app/telemetry.py](../../api/app/telemetry.py) emits one JSON line per request; a
  `ContextVar` set by the middleware in [app/main.py](../../api/app/main.py) carries the
  request ID into every line. Same JSON-logs convention as the main Go API, so one Loki
  pipeline (lab 11) parses both.
- **Cache.** [app/cache.py](../../api/app/cache.py) reuses the query embedding *already*
  computed for retrieval and a second Qdrant collection — no new infrastructure. A hit needs
  cosine ≥ `CACHE_MIN_SCORE` (0.97, deliberately strict). Single-turn only: a cached answer
  keyed on the question alone would ignore conversation context. Re-ingest clears it
  ([app/ingest.py](../../api/app/ingest.py)) — cached answers were generated from the *old*
  docs.
- **Cost.** There's no cost *metric* — local inference is free. The Grafana panel *derives*
  cost from `dojo_ai_tokens_total` × price variables, answering "what would this workload cost
  on a hosted API?" That framing (free locally, priced for comparison) is a strong interview line.

## Exercise

1. Set the dashboard's price variables to a model you know (e.g. GPT-4o-mini) and read the
   $/hour panel under load — then halve `HISTORY_TURNS` and watch prompt tokens drop.
2. Add a Prometheus alert: TTFT p95 > 5s for 10m. Which stage would you check first? (The
   stage-latency panel is the answer.)
3. Break the cache on purpose: lower `CACHE_MIN_SCORE` to 0.5, ask two *different* questions,
   and observe a wrong cache hit — then explain why the default is 0.97.

## Checkpoint

- ✅ `/metrics` shows token, stage-latency, TTFT, and cache series.
- ✅ A request with `X-Request-ID` produces one correlated JSON log line and echoes the header.
- ✅ Asking the same question twice (cache on) returns `"cached": true` and increments the hit counter.
- ✅ You can point at the stage-latency panel and say which stage dominates your latency.

## Common failures

- Token counts are always `estimated` → your backend didn't return `usage`; older Ollama or
  LM Studio versions omit it for streaming. Upgrade, or accept the estimate (it's labeled).
- Streaming crashes with `list index out of range` → the `include_usage` final chunk has an
  **empty `choices` list**; the guard in `llm.py` handles it — this is the classic bug the
  lab exists to teach.
- Cache never hits → `CACHE_ENABLED` isn't `true` in the running container (restart rag-api),
  the questions aren't similar enough (≥0.97), or you're sending `history` (multi-turn bypasses
  the cache by design).
- Stale answers after editing docs → you re-ingested but an old process kept the cache; the
  ingest clears it, so re-run ingest through the same stack.
- Grafana cost panel reads 0 → no tokens counted yet (ask questions), or the price variables
  are empty.

➡️ Next: [AI Lab 07 — Tool calling](../07-tool-calling/)
