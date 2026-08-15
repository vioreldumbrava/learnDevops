#!/usr/bin/env python3
"""Render every supported Compose overlay combination without starting containers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

# Some overlays depend on another overlay (for example scale needs the Caddy
# service from prod), so these are the supported combinations rather than a
# misleading base + one-file Cartesian product.
CONFIGURATIONS: dict[str, tuple[str, ...]] = {
    "app/base": ("deploy/compose/compose.yaml",),
    "app/dev": ("deploy/compose/compose.yaml", "deploy/compose/compose.dev.yaml"),
    "app/prod": ("deploy/compose/compose.yaml", "deploy/compose/compose.prod.yaml"),
    "app/scale": (
        "deploy/compose/compose.yaml",
        "deploy/compose/compose.prod.yaml",
        "deploy/compose/compose.scale.yaml",
    ),
    "app/python": ("deploy/compose/compose.yaml", "deploy/compose/compose.py.yaml"),
    "app/hardened": (
        "deploy/compose/compose.yaml",
        "deploy/compose/compose.hardening.yaml",
    ),
    "app/observability": (
        "deploy/compose/compose.yaml",
        "deploy/compose/compose.observability.yaml",
    ),
    "app/nexus": ("deploy/compose/compose.yaml", "deploy/compose/compose.nexus.yaml"),
    "app/jenkins": (
        "deploy/compose/compose.yaml",
        "deploy/compose/compose.jenkins.yaml",
    ),
    "app/postgres-tuning": (
        "deploy/compose/compose.yaml",
        "deploy/compose/compose.pgtune.yaml",
    ),
    "app/pgbouncer": (
        "deploy/compose/compose.yaml",
        "deploy/compose/compose.pgtune.yaml",
        "deploy/compose/compose.pgbouncer.yaml",
    ),
    "ai/base": ("ai-assistant/compose.yaml",),
    "ai/dojo-data": ("ai-assistant/compose.yaml", "ai-assistant/compose.dojo.yaml"),
    "ai/observability": (
        "ai-assistant/compose.yaml",
        "ai-assistant/compose.observability.yaml",
    ),
}


def main() -> int:
    configured_files = {compose_file for files in CONFIGURATIONS.values() for compose_file in files}
    discovered_files = {
        path.relative_to(ROOT).as_posix()
        for directory, pattern in (
            (ROOT / "deploy" / "compose", "compose*.y*ml"),
            (ROOT / "ai-assistant", "compose*.y*ml"),
        )
        for path in directory.glob(pattern)
    }
    uncovered = sorted(discovered_files - configured_files)
    if uncovered:
        print(
            "Compose files missing from a supported validation combination: "
            + ", ".join(uncovered),
            file=sys.stderr,
        )
        return 1

    failures: list[str] = []
    for name, files in CONFIGURATIONS.items():
        command = ["docker", "compose"]
        for compose_file in files:
            command.extend(("-f", compose_file))
        command.extend(("config", "--quiet"))

        print(f"==> {name}: {' + '.join(files)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        if result.returncode:
            failures.append(name)
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)

    if failures:
        print(f"Compose validation failed: {', '.join(failures)}", file=sys.stderr)
        return 1

    print(f"Validated {len(CONFIGURATIONS)} Compose configurations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
