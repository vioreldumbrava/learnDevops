"""The RAG pipeline: retrieve → ground-check → build prompt → generate with citations."""
from __future__ import annotations

import os
import time

from . import llm, metrics, vectorstore
from .config import cfg

_NO_ANSWER = (
    "I don't have enough information in the DevOps Dojo docs to answer that "
    "confidently. Try rephrasing, or check the relevant lab in docs/CURRICULUM.md."
)


def _load_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "prompts", "system.txt")
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


SYSTEM_PROMPT = _load_system_prompt()


def is_grounded(hits: list[dict]) -> bool:
    """Pure grounding decision (unit-tested): best score must clear MIN_SCORE."""
    return bool(hits) and hits[0].get("score", 0.0) >= cfg.MIN_SCORE


def build_messages(question: str, hits: list[dict]) -> list[dict]:
    """Pure prompt construction (unit-tested)."""
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(f"[{i}] source: {h.get('source', 'unknown')}\n{h.get('text', '')}")
    context = "\n\n".join(blocks) if blocks else "(no context found)"
    user = (
        "Answer the question using ONLY the context below, and cite sources as [n]. "
        "If the context does not contain the answer, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _sources(hits: list[dict]) -> list[dict]:
    return [
        {"n": i + 1, "source": h.get("source"), "score": round(h.get("score", 0.0), 3)}
        for i, h in enumerate(hits)
    ]


def retrieve(question: str) -> list[dict]:
    qvec = llm.embed([question])[0]
    return vectorstore.search(qvec, cfg.TOP_K)


def answer(question: str) -> dict:
    start = time.time()
    hits = retrieve(question)
    metrics.retrieval_top_score.observe(hits[0]["score"] if hits else 0.0)

    if not is_grounded(hits):
        metrics.chat_requests.labels(grounded="false").inc()
        metrics.chat_latency.observe(time.time() - start)
        return {"answer": _NO_ANSWER, "sources": [], "grounded": False}

    text = llm.chat(build_messages(question, hits), stream=False)
    metrics.chat_requests.labels(grounded="true").inc()
    metrics.chat_latency.observe(time.time() - start)
    return {"answer": text, "sources": _sources(hits), "grounded": True}


def answer_stream(question: str):
    """Yields event dicts: {'type':'token','text':..} then {'type':'done',..}."""
    hits = retrieve(question)
    metrics.retrieval_top_score.observe(hits[0]["score"] if hits else 0.0)

    if not is_grounded(hits):
        metrics.chat_requests.labels(grounded="false").inc()
        yield {"type": "token", "text": _NO_ANSWER}
        yield {"type": "done", "sources": [], "grounded": False}
        return

    metrics.chat_requests.labels(grounded="true").inc()
    for tok in llm.chat(build_messages(question, hits), stream=True):
        yield {"type": "token", "text": tok}
    yield {"type": "done", "sources": _sources(hits), "grounded": True}
