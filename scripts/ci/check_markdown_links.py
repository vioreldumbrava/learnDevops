#!/usr/bin/env python3
"""Fail when a repository-local Markdown link points at a missing path."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
# Check ordinary links and embedded images; both are repository-local references
# whose target can silently disappear during a refactor.
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^\n)]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
FENCE = re.compile(r"^\s*(```|~~~)")
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "data", "ftp", "app"}


def without_fenced_code(text: str) -> str:
    output: list[str] = []
    fence_marker: str | None = None
    for line in text.splitlines():
        match = FENCE.match(line)
        if match:
            marker = match.group(1)[0]
            fence_marker = None if fence_marker == marker else marker
            output.append("")
        elif fence_marker is None:
            output.append(line)
        else:
            output.append("")
    return "\n".join(output)


def link_target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    # An optional quoted title follows whitespace. Repository paths containing
    # spaces should use Markdown's <angle bracket> form.
    return raw.split(maxsplit=1)[0]


def missing_target(markdown_file: Path, target: str) -> Path | None:
    if not target or target.startswith("#"):
        return None

    parsed = urlsplit(target)
    if parsed.scheme.lower() in EXTERNAL_SCHEMES or parsed.netloc:
        return None

    raw_path = unquote(parsed.path).replace("\\", "/")
    if not raw_path or any(token in raw_path for token in ("${", "{{", "<", ">")):
        return None

    candidate = ROOT / raw_path.lstrip("/") if raw_path.startswith("/") else markdown_file.parent / raw_path
    candidate = candidate.resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return candidate
    return None if candidate.exists() else candidate


def main() -> int:
    failures: list[tuple[Path, str, Path]] = []
    markdown_files = sorted(
        path
        for path in ROOT.rglob("*.md")
        if not any(part in {".git", ".terraform", "node_modules", ".venv"} for part in path.parts)
    )

    for markdown_file in markdown_files:
        text = without_fenced_code(markdown_file.read_text(encoding="utf-8"))
        raw_targets = INLINE_LINK.findall(text) + REFERENCE_LINK.findall(text)
        for raw_target in raw_targets:
            target = link_target(raw_target)
            missing = missing_target(markdown_file, target)
            if missing is not None:
                failures.append((markdown_file.relative_to(ROOT), target, missing))

    if failures:
        print("Broken repository-local Markdown links:", file=sys.stderr)
        for source, target, missing in failures:
            try:
                display = missing.relative_to(ROOT)
            except ValueError:
                display = missing
            print(f"  {source}: {target} -> {display}", file=sys.stderr)
        return 1

    print(f"Checked local links in {len(markdown_files)} Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
