#!/usr/bin/env python3
"""Apply, roll back, and re-apply the complete migration baseline in Postgres."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "db" / "migrations"
PROJECT = "dojo-ci-migrations"
COMPOSE = [
    "docker",
    "compose",
    "-p",
    PROJECT,
    "-f",
    "deploy/compose/compose.yaml",
]
DATABASE_URL = "postgres://dojo:dojo@db:5432/dojo?sslmode=disable"


def run(*arguments: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    command = [*COMPOSE, *arguments]
    print(f"==> {' '.join(command)}", flush=True)
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=True,
    )


def validate_files() -> int:
    pattern = re.compile(r"^(\d+)_.+\.(up|down)\.sql$")
    directions: dict[int, set[str]] = {}
    files_by_key: dict[tuple[int, str], list[str]] = {}
    for path in MIGRATIONS.glob("*.sql"):
        match = pattern.match(path.name)
        if not match:
            raise RuntimeError(f"Unexpected migration filename: {path.name}")
        version = int(match.group(1))
        direction = match.group(2)
        directions.setdefault(version, set()).add(direction)
        files_by_key.setdefault((version, direction), []).append(path.name)

    if not directions:
        raise RuntimeError("No migrations found")
    incomplete = [version for version, found in directions.items() if found != {"up", "down"}]
    if incomplete:
        raise RuntimeError(f"Migration versions missing an up/down pair: {incomplete}")
    duplicates = [names for names in files_by_key.values() if len(names) > 1]
    if duplicates:
        raise RuntimeError(f"Duplicate migration version/direction entries: {duplicates}")
    versions = sorted(directions)
    expected = list(range(1, versions[-1] + 1))
    if versions != expected:
        raise RuntimeError(f"Migration versions must be contiguous from 1: found {versions}")
    return max(directions)


def migrate(direction: str, *extra: str) -> None:
    run(
        "run",
        "--rm",
        "migrate",
        "-path=/migrations",
        f"-database={DATABASE_URL}",
        direction,
        *extra,
    )


def assert_clean_version(expected: int) -> None:
    result = run(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "dojo",
        "-d",
        "dojo",
        "-Atc",
        "SELECT version::text || ':' || dirty::text FROM schema_migrations;",
        capture=True,
    )
    actual = result.stdout.strip()
    if actual != f"{expected}:false":
        raise RuntimeError(f"Expected clean migration version {expected}, got {actual!r}")


def main() -> int:
    latest = validate_files()
    try:
        run("up", "-d", "--wait", "db")
        migrate("up")
        assert_clean_version(latest)
        migrate("down", "-all")
        migrate("up")
        assert_clean_version(latest)
        print(f"Migration baseline rolls down and returns cleanly to version {latest}.")
        return 0
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Migration smoke test failed: {exc}", file=sys.stderr)
        return 1
    finally:
        subprocess.run(
            [*COMPOSE, "down", "-v", "--remove-orphans"],
            cwd=ROOT,
            check=False,
        )


if __name__ == "__main__":
    raise SystemExit(main())
