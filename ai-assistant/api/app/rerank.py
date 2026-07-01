"""Maximal Marginal Relevance re-ranking — pure functions, no extra deps.

MMR re-orders retrieved chunks to balance relevance to the query against
diversity, so the context isn't three near-duplicate paragraphs. Works from the
embeddings we already have (no cross-encoder model needed).
"""
from __future__ import annotations

import math


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def mmr(query_vec: list[float], doc_vecs: list[list[float]], k: int, lambda_: float = 0.6) -> list[int]:
    """Return indices of doc_vecs selected by MMR, most relevant first.

    lambda_=1 -> pure relevance; lambda_=0 -> pure diversity.
    """
    n = len(doc_vecs)
    if n == 0 or k <= 0:
        return []
    k = min(k, n)
    sim_q = [cosine(query_vec, d) for d in doc_vecs]

    selected: list[int] = []
    candidates = list(range(n))
    while len(selected) < k and candidates:
        best_idx, best_score = candidates[0], float("-inf")
        for c in candidates:
            diversity = max((cosine(doc_vecs[c], doc_vecs[s]) for s in selected), default=0.0)
            score = lambda_ * sim_q[c] - (1 - lambda_) * diversity
            if score > best_score:
                best_score, best_idx = score, c
        selected.append(best_idx)
        candidates.remove(best_idx)
    return selected
