"""The RAG pipeline: retrieve → ground-check → build prompt → generate with citations."""
from __future__ import annotations

import os
import time

from . import llm, metrics, vectorstore
from .config import cfg
from .rerank import mmr

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
    """Pure grounding decision (unit-tested): best score must clear MIN_SCORE.

    Uses the max score across hits (MMR may reorder them), not hits[0].
    """
    return bool(hits) and max(h.get("score", 0.0) for h in hits) >= cfg.MIN_SCORE


def build_messages(question: str, hits: list[dict], history: list[dict] | None = None) -> list[dict]:
    """Pure prompt construction (unit-tested). Includes recent conversation turns."""
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(f"[{i}] source: {h.get('source', 'unknown')}\n{h.get('text', '')}")
    context = "\n\n".join(blocks) if blocks else "(no context found)"
    user = (
        "Answer the question using ONLY the context below, and cite sources as [n]. "
        "If the context does not contain the answer, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-cfg.HISTORY_TURNS:])
    messages.append({"role": "user", "content": user})
    return messages


def _sources(hits: list[dict]) -> list[dict]:
    return [
        {"n": i + 1, "source": h.get("source"), "score": round(h.get("score", 0.0), 3)}
        for i, h in enumerate(hits)
    ]


def retrieve(question: str) -> list[dict]:
    """Over-fetch, then MMR-rerank down to TOP_K for relevance + diversity."""
    qvec = llm.embed([question])[0]
    hits = vectorstore.search(qvec, cfg.FETCH_K, with_vectors=True)
    if len(hits) > cfg.TOP_K:
        order = mmr(qvec, [h["vector"] for h in hits], cfg.TOP_K, cfg.MMR_LAMBDA)
        hits = [hits[i] for i in order]
    for h in hits:
        h.pop("vector", None)  # don't leak vectors past retrieval
    return hits


def _top_score(hits: list[dict]) -> float:
    return max((h.get("score", 0.0) for h in hits), default=0.0)


def answer(question: str, history: list[dict] | None = None) -> dict:
    start = time.time()
    hits = retrieve(question)
    metrics.retrieval_top_score.observe(_top_score(hits))

    if not is_grounded(hits):
        metrics.chat_requests.labels(grounded="false").inc()
        metrics.chat_latency.observe(time.time() - start)
        return {"answer": _NO_ANSWER, "sources": [], "grounded": False}

    text = llm.chat(build_messages(question, hits, history), stream=False)
    metrics.chat_requests.labels(grounded="true").inc()
    metrics.chat_latency.observe(time.time() - start)
    return {"answer": text, "sources": _sources(hits), "grounded": True}


def answer_stream(question: str, history: list[dict] | None = None):
    """Yields event dicts: {'type':'token','text':..} then {'type':'done',..}."""
    hits = retrieve(question)
    metrics.retrieval_top_score.observe(_top_score(hits))

    if not is_grounded(hits):
        metrics.chat_requests.labels(grounded="false").inc()
        yield {"type": "token", "text": _NO_ANSWER}
        yield {"type": "done", "sources": [], "grounded": False}
        return

    metrics.chat_requests.labels(grounded="true").inc()
    for tok in llm.chat(build_messages(question, hits, history), stream=True):
        yield {"type": "token", "text": tok}
    yield {"type": "done", "sources": _sources(hits), "grounded": True}
