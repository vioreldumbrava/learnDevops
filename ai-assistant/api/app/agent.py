"""Bounded tool-calling loop (lab 07).

The whole "agent" is this: send the conversation plus tool schemas; if the model
answers with tool_calls, execute them, append the results as role:"tool"
messages, and go around again — at most AGENT_MAX_TURNS times. Every risky part
is bounded and observable: turn limit, per-tool timeout (tools.py), per-tool
metrics, and errors fed back to the model as text so it can explain failure.
"""
from __future__ import annotations

import json

from . import llm, metrics, telemetry, tools
from .config import cfg

_SYSTEM = (
    "You are the DevOps Dojo assistant. You can call tools to inspect (and, if "
    "available, update) the learner's progress in the live DevOps Dojo app. Use "
    "tools when the question concerns the learner's actual progress, steps, or "
    "notes; answer directly otherwise. Be concise."
)

_OUT_OF_TURNS = (
    "I stopped before finishing: the request needed more tool steps than I'm "
    "allowed to take. Try a more specific question."
)


def run(question: str, history: list[dict] | None = None, chat_fn=None) -> dict:
    """Answer using tools. `chat_fn` is injectable so tests can fake the LLM."""
    chat_fn = chat_fn or llm.chat_raw
    reg = tools.registry()
    specs = [t["spec"] for t in reg.values()]

    messages: list[dict] = [{"role": "system", "content": _SYSTEM}]
    if history:
        messages.extend(history[-cfg.HISTORY_TURNS:])
    messages.append({"role": "user", "content": question})

    invoked: list[str] = []
    for _ in range(cfg.AGENT_MAX_TURNS):
        msg = chat_fn(messages, tools=specs).choices[0].message
        if not msg.tool_calls:
            return {"answer": msg.content or "", "tools_used": invoked}

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            }
        )
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = None

            if name not in reg:
                result = f"error: no such tool: {name}"
                metrics.tool_calls.labels(tool=name, status="error").inc()
            elif args is None:
                result = "error: tool arguments were not valid JSON"
                metrics.tool_calls.labels(tool=name, status="error").inc()
            else:
                try:
                    result = reg[name]["run"](args)
                    metrics.tool_calls.labels(tool=name, status="ok").inc()
                except Exception as e:  # noqa: BLE001 — surfaced to the model as text
                    result = f"error: the Dojo API call failed: {e}"
                    metrics.tool_calls.labels(tool=name, status="error").inc()

            invoked.append(name)
            telemetry.info("tool_call", tool=name)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    telemetry.info("agent_out_of_turns", tools_used=invoked)
    return {"answer": _OUT_OF_TURNS, "tools_used": invoked}
