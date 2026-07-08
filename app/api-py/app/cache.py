"""Redis: read cache + a list-based job queue — a port of the Go app's
internal/cache/cache.go. Same keys (``steps:all``) and same queue (``dojo:jobs``),
so the Go worker and this Python worker are interchangeable consumers of the
exact same queue.
"""
from __future__ import annotations

import redis.asyncio as redis
from redis.exceptions import TimeoutError as RedisTimeoutError


class Cache:
    def __init__(self, url: str) -> None:
        # decode_responses=True -> str in/out (matches the Go string API).
        self._r = redis.from_url(url, decode_responses=True)

    async def close(self) -> None:
        await self._r.aclose()

    async def ping(self) -> None:
        await self._r.ping()

    async def get(self, key: str) -> str | None:
        """Return the cached value, or None on a miss (redis-py returns None,
        the same signal the Go code models as ok=false)."""
        return await self._r.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self._r.set(key, value, ex=ttl_seconds)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self._r.delete(*keys)

    async def enqueue(self, queue: str, payload: str) -> None:
        await self._r.lpush(queue, payload)

    async def dequeue(self, queue: str, timeout_seconds: int) -> str | None:
        """Block up to timeout for the next job. Returns None when no job arrives.
        BRPOP + LPUSH = FIFO, exactly as in the Go worker. A client-side socket
        read timeout is treated the same as an empty-queue timeout — the worker
        just polls again (redis-py's async socket timeout can fire on a blocking
        BRPOP before the server-side nil arrives; either way there was no job)."""
        try:
            res = await self._r.brpop([queue], timeout=timeout_seconds)
        except RedisTimeoutError:
            return None
        if res is None:
            return None
        _, value = res  # (queue, value)
        return value
