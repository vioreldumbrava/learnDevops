"""Markdown-aware chunking. Pure functions (unit-tested, no I/O)."""
from __future__ import annotations


def split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n")]
    return [p for p in parts if p]


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Greedy pack paragraphs into ~size-char chunks with character overlap.

    Keeps paragraphs intact where possible; falls back to hard-splitting a single
    oversized paragraph.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    overlap = max(0, min(overlap, size - 1))

    chunks: list[str] = []
    current = ""
    for para in split_paragraphs(text):
        if len(para) > size:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(para), size - overlap):
                chunks.append(para[i : i + size])
            continue
        if not current:
            current = para
        elif len(current) + 2 + len(para) <= size:
            current += "\n\n" + para
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = (tail + "\n\n" + para).strip() if tail else para
    if current:
        chunks.append(current)
    return chunks
