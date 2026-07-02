# AI Lab 07 — Tool calling: the assistant operates the Dojo

## Concept

RAG lets the assistant *answer questions about* your docs. **Tool calling** lets it *act on
your live platform*. In this lab the assistant calls the **DevOps Dojo's own API** — the Go
service you built in the main project — to read (and optionally update) real curriculum
progress. One candidate, two systems, wired together: that's the differentiator.

An "agent" is less magic than it sounds. It's a **bounded loop**: give the model tool schemas;
if it responds with `tool_calls`, execute them, feed the results back as `role:"tool"`
messages, and repeat — at most N times. Every risky part is bounded and observable.

## What you'll do

Connect the AI stack to the main Dojo stack and let the agent answer questions that require
live data ("how many steps have I completed?").

## Steps — connect the two stacks

```powershell
# 1. Start the MAIN Dojo stack first (it creates the shared network). From the repo root:
docker compose -f deploy/compose/compose.yaml up -d

# 2. Start the AI stack joined to it, with the agent configured. From ai-assistant/:
docker compose -f compose.yaml -f compose.dojo.yaml --profile local-llm up -d
docker compose run --rm ingest
```

[compose.dojo.yaml](../../compose.dojo.yaml) attaches `rag-api` to the main stack's network
and sets `DOJO_API_URL=http://api:8080`.

## Steps — call the agent

```powershell
# Read-only tools are always available:
curl -s http://localhost:8000/api/agent -H "Content-Type: application/json" -d '{\"question\":\"How many curriculum steps are there, and how many are complete?\"}'
```

The response includes the answer and `tools_used` (e.g. `["list_steps"]`). Watch it work the
loop: `docker compose logs rag-api --tail=20` shows a `tool_call` log line.

## Steps — enable writes (deliberately gated)

```powershell
# Writes are OFF by default. Turn them on explicitly:
docker compose -f compose.yaml -f compose.dojo.yaml up -d -e AGENT_ALLOW_WRITES=true rag-api
curl -s http://localhost:8000/api/agent -H "Content-Type: application/json" -d '{\"question\":\"Mark step 04-docker-compose complete, then tell me my progress.\"}'
```

With writes off, the agent can't even *see* `set_progress`/`add_note` — they aren't registered.
With them on, it marks the step via `POST /api/progress/{id}` and confirms.

## How it works

- [app/tools.py](../../api/app/tools.py) defines tool **schemas** (OpenAI function format) and
  **executors** that call the Dojo API. Read tools (`list_steps`, `get_notes`) are always
  registered; write tools (`set_progress`, `add_note`) only when `AGENT_ALLOW_WRITES=true`.
  The *model* asks for a tool; this module decides what exists at all — safety lives in code,
  not the prompt. Executor errors return as strings, so the main stack being down produces
  "the Dojo API is unreachable", not a 500.
- [app/agent.py](../../api/app/agent.py) is the loop: send messages + schemas → if `tool_calls`,
  run each, append results, repeat up to `AGENT_MAX_TURNS` (3). It's **non-streaming** — local
  OpenAI-compatible backends don't deliver tool calls reliably over streams. Every call
  increments `dojo_ai_tool_calls_total{tool,status}`. The LLM call is injectable so the loop is
  unit-tested with a fake model (no GPU in CI).
- [app/main.py](../../api/app/main.py) exposes `POST /api/agent`, which returns **501** when
  `DOJO_API_URL` is unset — the AI stack stays useful standalone.

## Exercise

1. Add a `search_docs` tool that runs the existing RAG retrieval — now the agent chooses
   between "look it up in the docs" and "check the live app", which is real routing.
2. Force the failure modes: stop the main stack and ask a live-data question (graceful "tool
   unavailable"); lower `AGENT_MAX_TURNS` to 1 and ask something needing two steps.
3. **MCP (read, don't build):** the tool schemas you wrote are exactly what an **MCP server**
   would expose. Skim the Model Context Protocol spec and sketch how `list_steps` becomes an
   MCP tool — same idea, standardized transport. (Why it's an exercise, not a lab: MCP is a
   protocol wrapper around the loop you just built, and it moves fast.)

## Checkpoint

- ✅ With both stacks up, `/api/agent` answers a live-data question and reports `tools_used`.
- ✅ `dojo_ai_tool_calls_total` increments per tool call.
- ✅ Write tools are refused (absent) with the flag off, and work with it on.
- ✅ You can explain the agent loop and name three ways it's bounded (turns, timeouts, write gate).

## Common failures

- `501 agent not configured` → `DOJO_API_URL` is unset; you started without
  `-f compose.dojo.yaml`.
- `docker compose up` errors on the external network → the main stack isn't running (it owns
  `devops-dojo_default`); start it first.
- Agent invents step IDs or calls tools for chit-chat → small models over-eager to use tools;
  nudge the system prompt, lower temperature, or ask more specific questions.
- Infinite-looking tool use → it's capped at `AGENT_MAX_TURNS`; the capped answer says it ran
  out of steps.
- Tool calls silently missing → you tried to stream the agent; tool calling here is
  non-streaming on purpose.

➡️ Next: [AI Lab 08 — Evaluation v2 & prompt versioning](../08-eval-v2-prompt-versioning/)
