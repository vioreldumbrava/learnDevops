"""Semantic answer cache (lab 06): hit/miss threshold and failure tolerance."""
from types import SimpleNamespace

from app import cache


def _fake_client(monkeypatch, hits):
    fake = SimpleNamespace(
        search=lambda **kw: hits,
        get_collections=lambda: SimpleNamespace(collections=[]),
        create_collection=lambda **kw: None,
        upsert=lambda **kw: None,
        delete_collection=lambda name: None,
    )
    monkeypatch.setattr(cache.vectorstore, "client", lambda: fake)
    return fake


def test_lookup_hit_above_threshold(monkeypatch):
    _fake_client(
        monkeypatch,
        [SimpleNamespace(score=0.99, payload={"answer": "cached!", "sources": []})],
    )
    hit = cache.lookup([0.1, 0.2])
    assert hit is not None and hit["answer"] == "cached!"


def test_lookup_miss_below_threshold(monkeypatch):
    # 0.90 is a close paraphrase, not a repeat — must NOT be served from cache.
    _fake_client(monkeypatch, [SimpleNamespace(score=0.90, payload={"answer": "cached!"})])
    assert cache.lookup([0.1, 0.2]) is None


def test_lookup_miss_when_empty(monkeypatch):
    _fake_client(monkeypatch, [])
    assert cache.lookup([0.1, 0.2]) is None


def test_lookup_survives_missing_collection(monkeypatch):
    def boom(**kw):
        raise RuntimeError("collection does not exist")

    monkeypatch.setattr(cache.vectorstore, "client", lambda: SimpleNamespace(search=boom))
    assert cache.lookup([0.1, 0.2]) is None  # first request ever: miss, not crash
