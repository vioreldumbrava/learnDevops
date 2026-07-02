"""The RAG pipeline: retrieve → ground-check → build prompt → generate with citations.

Instrumented per stage (lab 06): embed / search / rerank / generate each get their
own latency histogram, streaming records time-to-first-token, token usage feeds
the cost counters, and one structured summary log line is emitted per request.
"""
from __future__ import annotations

import os
import time

from . import cache, llm, metrics, telemetry, vectorstore
from .config import cfg
from .rerank import mmr

_NO_ANSWER = (
    "I don't have enough information in the DevOps Dojo docs to answer that "
    "confidently. Try rephrasing, or check the relevant lab in docs/CURRICULUM.md."
)


def _load_system_prompt() -> str:
    # Versioned prompts (lab 08): the prompt is config, so a prompt change can be
    # A/B-tested by the eval harness before it reaches anyone.
    path = os.path.join(os.path.dirname(__file__), "prompts", f"{cfg.PROMPT_VERSION}.txt")
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


def embed_question(question: str) -> list[float]:
    t0 = time.time()
    qvec = llm.embed([question])[0]
    metrics.stage_latency.labels(stage="embed").observe(time.time() - t0)
    return qvec


def retrieve(question: str, qvec: list[float] | None = None) -> list[dict]:
    """Over-fetch, then MMR-rerank down to TOP_K for relevance + diversity."""
    if qvec is None:
        qvec = embed_question(question)
    t0 = time.time()
    hits = vectorstore.search(qvec, cfg.FETCH_K, with_vectors=True)
    metrics.stage_latency.labels(stage="search").observe(time.time() - t0)
    if len(hits) > cfg.TOP_K:
        t0 = time.time()
        order = mmr(qvec, [h["vector"] for h in hits], cfg.TOP_K, cfg.MMR_LAMBDA)
        hits = [hits[i] for i in order]
        metrics.stage_latency.labels(stage="rerank").observe(time.time() - t0)
    for h in hits:
        h.pop("vector", None)  # don't leak vectors past retrieval
    return hits


def _top_score(hits: list[dict]) -> float:
    return max((h.get("score", 0.0) for h in hits), default=0.0)


def _cache_active(history: list[dict] | None) -> bool:
    # Single-turn only: a cached answer keyed on the question alone would ignore
    # the conversation context.
    return cfg.CACHE_ENABLED and not history


def _log_summary(start: float, *, grounded: bool, top_score: float = 0.0,
                 usage: dict | None = None, cache_state: str = "off",
                 stream: bool = False) -> None:
    fields: dict = {
        "stream": stream,
        "grounded": grounded,
        "top_score": round(top_score, 3),
        "cache": cache_state,
        "duration_ms": int((time.time() - start) * 1000),
    }
    if usage:
        fields.update(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            tokens_estimated=usage.get("estimated", False),
        )
    telemetry.info("chat", **fields)


def answer(question: str, history: list[dict] | None = None) -> dict:
    start = time.time()
    qvec = embed_question(question)

    if _cache_active(history):
        cached = cache.lookup(qvec)
        metrics.cache_events.labels(result="hit" if cached else "miss").inc()
        if cached:
            metrics.chat_requests.labels(grounded="true").inc()
            metrics.chat_latency.observe(time.time() - start)
            _log_summary(start, grounded=True, cache_state="hit")
            return {
                "answer": cached["answer"],
                "sources": cached.get("sources", []),
                "grounded": True,
                "cached": True,
            }

    hits = retrieve(question, qvec)
    top = _top_score(hits)
    metrics.retrieval_top_score.observe(top)

    if not is_grounded(hits):
        metrics.chat_requests.labels(grounded="false").inc()
        metrics.chat_latency.observe(time.time() - start)
        _log_summary(start, grounded=False, top_score=top)
        return {"answer": _NO_ANSWER, "sources": [], "grounded": False}

    t0 = time.time()
    result = llm.chat(build_messages(question, hits, history), stream=False)
    metrics.stage_latency.labels(stage="generate").observe(time.time() - t0)
    metrics.record_usage(result["usage"])

    if _cache_active(history):
        cache.store(qvec, question, result["text"], _sources(hits))

    metrics.chat_requests.labels(grounded="true").inc()
    metrics.chat_latency.observe(time.time() - start)
    _log_summary(
        start, grounded=True, top_score=top, usage=result["usage"],
        cache_state="miss" if _cache_active(history) else "off",
    )
    return {
        "answer": result["text"],
        "sources": _sources(hits),
        "grounded": True,
        "usage": result["usage"],
    }


def answer_stream(question: str, history: list[dict] | None = None):
    """Yields event dicts: {'type':'token','text':..} then {'type':'done',..}."""
    start = time.time()
    qvec = embed_question(question)

    if _cache_active(history):
        cached = cache.lookup(qvec)
        metrics.cache_events.labels(result="hit" if cached else "miss").inc()
        if cached:
            metrics.chat_requests.labels(grounded="true").inc()
            metrics.time_to_first_token.observe(time.time() - start)
            metrics.chat_latency.observe(time.time() - start)
            _log_summary(start, grounded=True, cache_state="hit", stream=True)
            yield {"type": "token", "text": cached["answer"]}
            yield {"type": "done", "sources": cached.get("sources", []), "grounded": True, "cached": True}
            return

    hits = retrieve(question, qvec)
    top = _top_score(hits)
    metrics.retrieval_top_score.observe(top)

    if not is_grounded(hits):
        metrics.chat_requests.labels(grounded="false").inc()
        metrics.time_to_first_token.observe(time.time() - start)
        metrics.chat_latency.observe(time.time() - start)
        _log_summary(start, grounded=False, top_score=top, stream=True)
        yield {"type": "token", "text": _NO_ANSWER}
        yield {"type": "done", "sources": [], "grounded": False}
        return

    metrics.chat_requests.labels(grounded="true").inc()
    t_gen = time.time()
    usage: dict | None = None
    parts: list[str] = []
    seen_first = False
    for event in llm.chat(build_messages(question, hits, history), stream=True):
        if event["type"] == "token":
            if not seen_first:
                seen_first = True
                metrics.time_to_first_token.observe(time.time() - start)
            parts.append(event["text"])
            yield event
        elif event["type"] == "usage":
            usage = {k: v for k, v in event.items() if k != "type"}
    metrics.stage_latency.labels(stage="generate").observe(time.time() - t_gen)
    if usage:
        metrics.record_usage(usage)

    if _cache_active(history):
        cache.store(qvec, question, "".join(parts), _sources(hits))

    metrics.chat_latency.observe(time.time() - start)
    _log_summary(
        start, grounded=True, top_score=top, usage=usage, stream=True,
        cache_state="miss" if _cache_active(history) else "off",
    )
    yield {"type": "done", "sources": _sources(hits), "grounded": True, "usage": usage}
