"""Background worker — Python twin of the Go cmd/worker.

Consumes the SAME Redis queue (``dojo:jobs``) the API enqueues to, so you can
run the Go API with this Python worker or vice-versa — they only share the queue
contract. Being stateless, it's what you scale in lab 21 (and what KEDA scales on
queue depth in lab 31). Run it with:  python -m app.worker
"""
from __future__ import annotations

import asyncio
import logging
import signal

from .cache import Cache
from .config import cfg

JOB_QUEUE = "dojo:jobs"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("dojo-worker")


async def run() -> None:
    cache = Cache(cfg.redis_url)
    await cache.ping()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    # Graceful shutdown on SIGTERM/SIGINT (Compose/K8s send SIGTERM).
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover - Windows dev
            pass

    log.info('{"msg":"worker started","queue":"%s"}', JOB_QUEUE)
    try:
        while not stop.is_set():
            job = await cache.dequeue(JOB_QUEUE, timeout_seconds=5)
            if job is None:
                continue  # timed out, poll again (lets us re-check stop)
            log.info('{"msg":"processing job","job":"%s"}', job)
            await asyncio.sleep(0.5)  # stand in for report/certificate generation
            log.info('{"msg":"job done","job":"%s"}', job)
    finally:
        log.info('{"msg":"worker stopping"}')
        await cache.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
