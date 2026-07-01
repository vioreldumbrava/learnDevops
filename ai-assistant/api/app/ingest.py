"""Index markdown docs into Qdrant: read -> chunk -> embed -> upsert.

Run: python -m app.ingest   (Compose runs this as a one-shot `ingest` service).
"""
from __future__ import annotations

import glob
import os

from . import llm, vectorstore
from .chunk import chunk_text
from .config import cfg

BATCH = 32


def _iter_markdown(paths: list[str]):
    for raw in paths:
        p = raw.strip()
        if not p:
            continue
        if os.path.isfile(p) and p.endswith(".md"):
            yield p
        elif os.path.isdir(p):
            yield from glob.glob(os.path.join(p, "**", "*.md"), recursive=True)


def run() -> None:
    files = sorted(set(_iter_markdown(cfg.DOCS_PATHS.split(","))))
    if not files:
        print(f"No markdown found in {cfg.DOCS_PATHS}")
        return

    dim = len(llm.embed(["dimension probe"])[0])
    vectorstore.ensure_collection(dim)
    print(f"embedding dim={dim}, collection='{cfg.QDRANT_COLLECTION}'")

    total = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            chunks = chunk_text(fh.read(), cfg.CHUNK_SIZE, cfg.CHUNK_OVERLAP)
        if not chunks:
            continue
        source = os.path.relpath(f)
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i : i + BATCH]
            vectors = llm.embed(batch)
            payloads = [{"text": c, "source": source} for c in batch]
            vectorstore.upsert(vectors, payloads)
        total += len(chunks)
        print(f"indexed {len(chunks):4d} chunks  {source}")

    print(f"done: {total} chunks from {len(files)} files")


if __name__ == "__main__":
    run()
