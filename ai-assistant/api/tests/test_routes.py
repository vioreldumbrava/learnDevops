"""Route tests: the HTTP contract, with the RAG pipeline faked out."""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main, rag

client = TestClient(main.app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_metrics_exposed():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "dojo_ai_chat_requests_total" in r.text
    assert "dojo_ai_app_info" in r.text


def test_readyz_degraded_returns_503(monkeypatch):
    class BoomQdrant:
        def get_collections(self):
            raise RuntimeError("qdrant down")

    class BoomModels:
        def list(self):
            raise RuntimeError("llm down")

    monkeypatch.setattr(main.vectorstore, "client", lambda: BoomQdrant())
    monkeypatch.setattr(main.llm.client, "models", BoomModels())
    r = client.get("/readyz")
    assert r.status_code == 503
    assert "qdrant down" in r.json()["qdrant"]


def test_chat_json(monkeypatch):
    monkeypatch.setattr(
        rag, "answer",
        lambda q, h: {"answer": "hi", "sources": [], "grounded": True},
    )
    r = client.post("/api/chat", json={"question": "hello"})
    assert r.status_code == 200
    assert r.json()["answer"] == "hi"


def test_chat_sse_framing(monkeypatch):
    def fake_stream(q, h):
        yield {"type": "token", "text": "he"}
        yield {"type": "token", "text": "llo"}
        yield {"type": "done", "sources": [], "grounded": True}

    monkeypatch.setattr(rag, "answer_stream", fake_stream)
    with client.stream("POST", "/api/chat", json={"question": "x", "stream": True}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())

    frames = [f for f in body.split("\n\n") if f]
    assert all(f.startswith("data: ") for f in frames)
    events = [json.loads(f[len("data: "):]) for f in frames]
    assert [e["type"] for e in events] == ["token", "token", "done"]
    assert "".join(e["text"] for e in events[:2]) == "hello"


def test_request_id_honored_and_echoed(monkeypatch):
    monkeypatch.setattr(
        rag, "answer", lambda q, h: {"answer": "", "sources": [], "grounded": False}
    )
    r = client.post(
        "/api/chat", json={"question": "x"}, headers={"X-Request-ID": "test123"}
    )
    assert r.headers["x-request-id"] == "test123"


def test_request_id_generated_when_absent(monkeypatch):
    monkeypatch.setattr(
        rag, "answer", lambda q, h: {"answer": "", "sources": [], "grounded": False}
    )
    r = client.post("/api/chat", json={"question": "x"})
    assert len(r.headers["x-request-id"]) >= 8


def test_agent_unconfigured_returns_501():
    # DOJO_API_URL defaults to "" in tests — the endpoint must refuse clearly.
    r = client.post("/api/agent", json={"question": "x"})
    assert r.status_code == 501
    assert "DOJO_API_URL" in r.json()["error"]
