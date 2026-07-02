"""Semantic answer cache (lab 06): near-duplicate questions skip generation.

Reuses the query embedding ALREADY computed for retrieval and a second Qdrant
collection — no new infrastructure. The threshold is deliberately strict
(CACHE_MIN_SCORE, default 0.97): only near-identical repeats hit; a paraphrase
with a possibly different intent still runs the full pipeline.

Multi-turn requests must bypass this cache entirely — a cached answer keyed on
the question alone would ignore the conversation context (rag.py enforces it).
"""
from __future__ import annotations

import uuid

from qdrant_client.models import Distance, PointStruct, VectorParams

from . import vectorstore
from .config import cfg


def _ensure(dim: int) -> None:
    c = vectorstore.client()
    existing = {col.name for col in c.get_collections().collections}
    if cfg.CACHE_COLLECTION not in existing:
        c.create_collection(
            collection_name=cfg.CACHE_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def lookup(qvec: list[float]) -> dict | None:
    """Return the cached payload if a near-identical question was answered before."""
    try:
        hits = vectorstore.client().search(
            collection_name=cfg.CACHE_COLLECTION, query_vector=qvec, limit=1
        )
    except Exception:  # noqa: BLE001 — collection may simply not exist yet
        return None
    if hits and hits[0].score >= cfg.CACHE_MIN_SCORE:
        return dict(hits[0].payload or {})
    return None


def store(qvec: list[float], question: str, answer: str, sources: list[dict]) -> None:
    _ensure(len(qvec))
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=qvec,
        payload={"question": question, "answer": answer, "sources": sources},
    )
    vectorstore.client().upsert(collection_name=cfg.CACHE_COLLECTION, points=[point])


def clear() -> None:
    """Drop the whole cache. MUST run on re-ingest — cached answers were
    generated from the OLD documents and would silently outlive them."""
    try:
        vectorstore.client().delete_collection(cfg.CACHE_COLLECTION)
    except Exception:  # noqa: BLE001 — nothing to clear is fine
        pass
