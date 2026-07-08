"""PostgreSQL data layer — a port of the Go app's internal/store/store.go.

Same tables, same SQL (asyncpg uses ``$1`` placeholders exactly like pgx, so the
queries are byte-for-byte identical), same JSON field names — so this hits the
*same* database the Go API uses and the React frontend can't tell them apart.
The one idiomatic difference: this is async (asyncpg + a connection pool driven
by the event loop) where Go used a goroutine-safe pool; both give safe
concurrent access, the concurrency *model* differs (that's lab 50's comparison).
"""
from __future__ import annotations

from datetime import datetime

import asyncpg
from opentelemetry import trace
from pydantic import BaseModel

tracer = trace.get_tracer("devops-dojo/store")


class Step(BaseModel):
    id: str
    lab_no: int
    title: str
    topic: str
    maps_to: str
    milestone: int
    doc_path: str
    summary: str
    completed: bool


class Note(BaseModel):
    id: int
    step_id: str
    body: str
    created_at: datetime


class Store:
    """Owns the asyncpg pool. Construct with ``await Store.connect(url)``."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, url: str) -> "Store":
        # asyncpg parses libpq-style DSNs, including ?sslmode=disable.
        pool = await asyncpg.create_pool(dsn=url, min_size=1, max_size=10)
        return cls(pool)

    async def close(self) -> None:
        await self._pool.close()

    async def ping(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("SELECT 1")

    async def list_steps(self) -> list[Step]:
        with tracer.start_as_current_span("store.list_steps"):
            rows = await self._pool.fetch(
                """
                SELECT s.id, s.lab_no, s.title, s.topic, s.maps_to, s.milestone,
                       s.doc_path, s.summary, COALESCE(p.completed, false) AS completed
                FROM steps s
                LEFT JOIN progress p ON p.step_id = s.id
                ORDER BY s.sort_order
                """
            )
        return [Step(**dict(r)) for r in rows]

    async def set_progress(self, step_id: str, completed: bool) -> None:
        with tracer.start_as_current_span("store.set_progress"):
            completed_at = datetime.now() if completed else None
            await self._pool.execute(
                """
                INSERT INTO progress (step_id, completed, completed_at, updated_at)
                VALUES ($1, $2, $3, now())
                ON CONFLICT (step_id) DO UPDATE
                SET completed = EXCLUDED.completed,
                    completed_at = EXCLUDED.completed_at,
                    updated_at = now()
                """,
                step_id,
                completed,
                completed_at,
            )

    async def step_exists(self, step_id: str) -> bool:
        return bool(
            await self._pool.fetchval(
                "SELECT EXISTS(SELECT 1 FROM steps WHERE id=$1)", step_id
            )
        )

    async def list_notes(self, step_id: str) -> list[Note]:
        rows = await self._pool.fetch(
            "SELECT id, step_id, body, created_at FROM notes WHERE step_id=$1 ORDER BY created_at",
            step_id,
        )
        return [Note(**dict(r)) for r in rows]

    async def add_note(self, step_id: str, body: str) -> Note:
        row = await self._pool.fetchrow(
            """
            INSERT INTO notes (step_id, body) VALUES ($1, $2)
            RETURNING id, step_id, body, created_at
            """,
            step_id,
            body,
        )
        return Note(**dict(row))
