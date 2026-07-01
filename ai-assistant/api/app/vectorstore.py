"""Qdrant vector store: collection management, upsert, and search."""
from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .config import cfg

_client: QdrantClient | None = None


def client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=cfg.QDRANT_URL, timeout=cfg.REQUEST_TIMEOUT)
    return _client


def ensure_collection(dim: int) -> None:
    c = client()
    existing = {col.name for col in c.get_collections().collections}
    if cfg.QDRANT_COLLECTION not in existing:
        c.create_collection(
            collection_name=cfg.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def upsert(vectors: list[list[float]], payloads: list[dict]) -> None:
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=v, payload=p)
        for v, p in zip(vectors, payloads)
    ]
    client().upsert(collection_name=cfg.QDRANT_COLLECTION, points=points)


def search(vector: list[float], top_k: int, with_vectors: bool = False) -> list[dict]:
    hits = client().search(
        collection_name=cfg.QDRANT_COLLECTION,
        query_vector=vector,
        limit=top_k,
        with_vectors=with_vectors,
    )
    out = []
    for h in hits:
        item = {"score": h.score, **(h.payload or {})}
        if with_vectors:
            item["vector"] = h.vector
        out.append(item)
    return out
