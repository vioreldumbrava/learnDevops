"""Tools the agent may call (lab 07) — each wraps one endpoint of the MAIN
DevOps Dojo API (the Go service from the core labs), reached via DOJO_API_URL.

Two safety rules live here, not in the model:
  1. Read-only tools are always available; WRITE tools (set_progress, add_note)
     are only registered when AGENT_ALLOW_WRITES=true. The model decides which
     tool to *ask for*; this module decides what exists at all.
  2. Executor errors come back as tool-result strings, not exceptions — the
     main stack being down should produce "the Dojo API is unreachable", not a 500.
"""
from __future__ import annotations

import httpx

from .config import cfg

TIMEOUT = 5.0  # seconds — a tool that hangs would stall the whole agent turn


def _get(path: str) -> str:
    r = httpx.get(f"{cfg.DOJO_API_URL}{path}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _post(path: str, body: dict) -> str:
    r = httpx.post(f"{cfg.DOJO_API_URL}{path}", json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _list_steps(_args: dict) -> str:
    return _get("/api/steps")


def _get_notes(args: dict) -> str:
    step = args.get("step_id", "")
    if not step:
        return "error: step_id is required"
    return _get(f"/api/notes?step={step}")


def _set_progress(args: dict) -> str:
    step = args.get("step_id", "")
    if not step:
        return "error: step_id is required"
    return _post(f"/api/progress/{step}", {"completed": bool(args.get("completed", True))})


def _add_note(args: dict) -> str:
    step, body = args.get("step_id", ""), args.get("body", "")
    if not step or not body:
        return "error: step_id and body are required"
    return _post("/api/notes", {"step_id": step, "body": body})


def _spec(name: str, description: str, params: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": params, "required": required},
        },
    }


def registry() -> dict[str, dict]:
    """name -> {spec, run}. Write tools appear only when explicitly enabled."""
    tools = {
        "list_steps": {
            "spec": _spec(
                "list_steps",
                "List every step in the DevOps Dojo curriculum with its id, title and completion status.",
                {}, [],
            ),
            "run": _list_steps,
        },
        "get_notes": {
            "spec": _spec(
                "get_notes",
                "Get the learner's notes for one curriculum step.",
                {"step_id": {"type": "string", "description": "The step id, e.g. '04-docker-compose'."}},
                ["step_id"],
            ),
            "run": _get_notes,
        },
    }
    if cfg.AGENT_ALLOW_WRITES:
        tools["set_progress"] = {
            "spec": _spec(
                "set_progress",
                "Mark a curriculum step complete or incomplete.",
                {
                    "step_id": {"type": "string", "description": "The step id to update."},
                    "completed": {"type": "boolean", "description": "true = done, false = not done."},
                },
                ["step_id"],
            ),
            "run": _set_progress,
        }
        tools["add_note"] = {
            "spec": _spec(
                "add_note",
                "Attach a note to a curriculum step.",
                {
                    "step_id": {"type": "string", "description": "The step id to annotate."},
                    "body": {"type": "string", "description": "The note text."},
                },
                ["step_id", "body"],
            ),
            "run": _add_note,
        }
    return tools
