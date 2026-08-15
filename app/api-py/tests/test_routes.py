"""HTTP-contract tests with the DB and Redis faked out — the FastAPI equivalent
of testing the Go chi handlers. No real Postgres/Redis needed, so this runs in
CI in milliseconds. The assertions pin the SAME contract the Go API serves:
field names, status codes, X-Cache headers, the enqueue-on-progress behaviour.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import main
from app.store import Note, Progress, Step

PRACTICED_AT = datetime(2026, 7, 26, 8, 0, 0)


# --- in-memory fakes implementing the async Store/Cache interfaces -------------
class FakeStore:
    def __init__(self):
        self.steps = [
            Step(id="00-prerequisites", lab_no=0, title="Prerequisites", topic="Setup",
                 maps_to="—", milestone=1, doc_path="labs/00/", summary="", completed=False,
                 tier="core", tracks=["common-core"], requires=[], effort_minutes=60,
                 cost_class="free", drill_required=True, drilled=False, last_practiced_at=None),
            Step(id="01-docker-basics", lab_no=1, title="Docker basics", topic="Images",
                 maps_to="§1", milestone=1, doc_path="labs/01/", summary="", completed=False,
                 tier="core", tracks=["common-core"], requires=["00-prerequisites"],
                 effort_minutes=60, cost_class="local", drill_required=True, drilled=False,
                 last_practiced_at=None),
        ]
        self.progress: dict[str, tuple[bool, bool]] = {}
        self.notes: list[Note] = []

    async def ping(self):  # healthy
        return None

    async def list_steps(self):
        out = []
        for s in self.steps:
            completed, drilled = self.progress.get(s.id, (False, False))
            out.append(s.model_copy(update={
                "completed": completed,
                "drilled": drilled,
                "last_practiced_at": PRACTICED_AT if s.id in self.progress else None,
            }))
        return out

    async def step_exists(self, step_id):
        return any(s.id == step_id for s in self.steps)

    async def set_progress(self, step_id, completed, drilled):
        # None means "leave that flag alone" — mirrors the real COALESCE upsert.
        was_completed, was_drilled = self.progress.get(step_id, (False, False))
        now_completed = was_completed if completed is None else completed
        now_drilled = was_drilled if drilled is None else drilled
        self.progress[step_id] = (now_completed, now_drilled)
        return Progress(step_id=step_id, completed=now_completed, drilled=now_drilled,
                        last_practiced_at=PRACTICED_AT)

    async def list_notes(self, step_id):
        return [n for n in self.notes if n.step_id == step_id]

    async def add_note(self, step_id, body):
        n = Note(id=len(self.notes) + 1, step_id=step_id, body=body,
                 created_at=datetime(2026, 1, 1))
        self.notes.append(n)
        return n


class FakeCache:
    def __init__(self):
        self.kv: dict[str, str] = {}
        self.queue: list[str] = []

    async def ping(self):
        return None

    async def get(self, key):
        return self.kv.get(key)

    async def set(self, key, value, ttl_seconds):
        self.kv[key] = value

    async def delete(self, *keys):
        for k in keys:
            self.kv.pop(k, None)

    async def enqueue(self, queue, payload):
        self.queue.append(payload)


@pytest.fixture
def ctx(monkeypatch):
    store, cache = FakeStore(), FakeCache()
    # Inject the fakes directly; not using `with TestClient` means the real
    # lifespan (which would dial Postgres/Redis) never runs.
    monkeypatch.setattr(main, "_store", store)
    monkeypatch.setattr(main, "_cache", cache)
    return TestClient(main.app), store, cache


def test_healthz(ctx):
    client, _, _ = ctx
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_metrics_exposes_parity_names(ctx):
    client, _, _ = ctx
    client.get("/healthz")  # generate at least one observation
    r = client.get("/metrics")
    assert r.status_code == 200
    # The SAME names the Go API exports — dashboards/alerts work on either.
    assert "dojo_http_requests_total" in r.text
    assert "dojo_http_request_duration_seconds" in r.text
    assert "dojo_http_in_flight_requests" in r.text


def test_steps_cache_miss_then_hit(ctx):
    client, _, cache = ctx
    r1 = client.get("/api/steps")
    assert r1.status_code == 200
    assert r1.headers["x-cache"] == "MISS"
    data = r1.json()
    assert len(data) == 2
    # Go field names, including additive curriculum metadata and drill tracking.
    assert set(data[0]) >= {
        "id", "lab_no", "title", "tier", "tracks", "requires", "effort_minutes",
        "cost_class", "drill_required", "completed", "drilled", "last_practiced_at",
    }
    assert data[0]["tier"] == "core"
    assert data[0]["tracks"] == ["common-core"]
    assert data[0]["drill_required"] is True

    r2 = client.get("/api/steps")
    assert r2.headers["x-cache"] == "HIT"      # served from the fake cache
    assert r2.json() == data


def test_set_progress_persists_invalidates_and_enqueues(ctx):
    client, store, cache = ctx
    client.get("/api/steps")                    # prime the cache
    assert "steps:v2:all" in cache.kv

    r = client.post("/api/progress/01-docker-basics", json={"completed": True})
    assert r.status_code == 200
    assert r.json() == {
        "step_id": "01-docker-basics",
        "completed": True,
        "drilled": False,
        "last_practiced_at": PRACTICED_AT.isoformat(),
    }
    assert store.progress["01-docker-basics"] == (True, False)
    assert "steps:v2:all" not in cache.kv       # cache invalidated
    assert cache.queue == ["progress:01-docker-basics"]  # job enqueued


def test_set_drilled_leaves_completed_alone(ctx):
    """The whole point of the pointer/None fields: one flag at a time."""
    client, store, _ = ctx
    client.post("/api/progress/01-docker-basics", json={"completed": True})
    r = client.post("/api/progress/01-docker-basics", json={"drilled": True})
    assert r.status_code == 200
    assert r.json()["completed"] is True and r.json()["drilled"] is True
    assert store.progress["01-docker-basics"] == (True, True)


def test_set_progress_empty_body_400(ctx):
    client, _, _ = ctx
    r = client.post("/api/progress/01-docker-basics", json={})
    assert r.status_code == 400
    assert r.json() == {"error": "set completed and/or drilled"}


def test_set_progress_unknown_step_404(ctx):
    client, _, _ = ctx
    r = client.post("/api/progress/does-not-exist", json={"completed": True})
    assert r.status_code == 404
    assert r.json() == {"error": "unknown step"}


def test_notes_roundtrip(ctx):
    client, _, _ = ctx
    assert client.get("/api/notes").status_code == 400  # missing ?step
    created = client.post(
        "/api/notes", json={"step_id": "00-prerequisites", "body": "hello"}
    )
    assert created.status_code == 201
    assert created.json()["body"] == "hello"

    listed = client.get("/api/notes", params={"step": "00-prerequisites"})
    assert listed.status_code == 200
    assert [n["body"] for n in listed.json()] == ["hello"]


def test_add_note_requires_fields(ctx):
    client, _, _ = ctx
    r = client.post("/api/notes", json={"step_id": "", "body": ""})
    assert r.status_code == 400


def test_readyz_ok_then_degraded(ctx, monkeypatch):
    client, store, _ = ctx
    assert client.get("/readyz").status_code == 200

    async def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(store, "ping", boom)
    r = client.get("/readyz")
    assert r.status_code == 503
    assert "db down" in r.json()["db"]
