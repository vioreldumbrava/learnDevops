"""FastAPI app: RAG chat + operational endpoints + a minimal web UI."""
from __future__ import annotations

import json
import os

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from . import llm, rag, vectorstore

app = FastAPI(title="DevOps Dojo — AI Assistant")


class ChatRequest(BaseModel):
    question: str
    stream: bool = False


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
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.stream:
        def sse():
            for event in rag.answer_stream(req.question):
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")
    return rag.answer(req.question)


# Serve the minimal chat UI at "/". Registered last so API routes take precedence.
_web = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(_web):
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
