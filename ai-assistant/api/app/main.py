"""FastAPI app: RAG chat + agent + operational endpoints + a minimal web UI."""
from __future__ import annotations

import json
import os
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from . import agent, llm, metrics, rag, telemetry, vectorstore
from .config import cfg

app = FastAPI(title="DevOps Dojo — AI Assistant")

# Static app facts as a Prometheus 'info' metric — lets dashboards/alerts see
# which prompt version and model produced any change in the other metrics.
metrics.app_info.labels(prompt_version=cfg.PROMPT_VERSION, chat_model=cfg.CHAT_MODEL).set(1)


@app.middleware("http")
async def request_id(request: Request, call_next):
    # Honor an upstream ID (proxy, caller) or mint one; every log line emitted
    # while handling this request carries it (telemetry.py ContextVar).
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    telemetry.request_id_var.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


class Turn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    stream: bool = False
    history: list[Turn] = []


class AgentRequest(BaseModel):
    question: str
    history: list[Turn] = []


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    checks = {"qdrant": "ok", "llm": "ok"}
    ok = True
    try:
        vectorstore.client().get_collections()
    except Exception as e:  # noqa: BLE001
        checks["qdrant"], ok = str(e), False
    try:
        llm.client.models.list()
    except Exception as e:  # noqa: BLE001
        checks["llm"], ok = str(e), False
    return JSONResponse(checks, status_code=200 if ok else 503)


@app.get("/metrics")
def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/chat")
def chat(req: ChatRequest):
    history = [t.model_dump() for t in req.history]
    if req.stream:
        def sse():
            for event in rag.answer_stream(req.question, history):
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")
    return rag.answer(req.question, history)


@app.post("/api/agent")
def agent_chat(req: AgentRequest):
    if not cfg.DOJO_API_URL:
        return JSONResponse(
            {"error": "agent not configured: set DOJO_API_URL (see compose.dojo.yaml, lab 07)"},
            status_code=501,
        )
    history = [t.model_dump() for t in req.history]
    return agent.run(req.question, history)


# Serve the minimal chat UI at "/". Registered last so API routes take precedence.
_web = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(_web):
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
