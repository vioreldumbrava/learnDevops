#!/usr/bin/env python3
"""Prove a pg_dump backup actually restores. Lab 37; closes the loop from lab 07.

Loads the dump into a throwaway Postgres container, runs sanity checks, and always
cleans up. Exit codes: 0 = verified, 1 = verification failed, 2 = bad usage.

Usage:
    python scripts/verify_backup.py backups/dojo_20260701_120000.sql
    python scripts/verify_backup.py backups/latest.sql --min-steps 24
"""

import argparse
import os
import pathlib
import subprocess
import sys
import time

IMAGE = "postgres:16-alpine"
USER = DB = "dojo"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run with sane defaults; never silently ignore a failure."""
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)


def wait_ready(container: str, timeout: int = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready = subprocess.run(
            ["docker", "exec", container, "pg_isready", "-U", USER, "-d", DB],
            capture_output=True,
        )
        if ready.returncode == 0:
            return
        time.sleep(1)
    raise TimeoutError(f"postgres in {container} not ready after {timeout}s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", type=pathlib.Path, help="plain-format pg_dump file")
    parser.add_argument(
        "--min-steps",
        type=int,
        default=1,
        help="fail unless the steps table has at least this many rows (default 1)",
    )
    args = parser.parse_args()

    if not args.dump.is_file():
        parser.error(f"{args.dump} is not a file")

    container = f"verify-backup-{os.getpid()}"
    print(f"==> restoring {args.dump} into a scratch {IMAGE}")
    run(
        ["docker", "run", "-d", "--name", container,
         "-e", f"POSTGRES_USER={USER}", "-e", "POSTGRES_PASSWORD=scratch",
         "-e", f"POSTGRES_DB={DB}", IMAGE]
    )
    try:
        wait_ready(container)

        with args.dump.open("rb") as dump:
            restore = subprocess.run(
                ["docker", "exec", "-i", container, "psql",
                 "-v", "ON_ERROR_STOP=1", "-U", USER, "-d", DB],
                stdin=dump, capture_output=True, text=True,
            )
        if restore.returncode != 0:
            print(f"FAIL: restore errored:\n{restore.stderr}", file=sys.stderr)
            return 1

        count = int(
            run(["docker", "exec", container, "psql", "-U", USER, "-d", DB,
                 "-tAc", "SELECT count(*) FROM steps;"]).stdout.strip()
        )
        if count < args.min_steps:
            print(f"FAIL: steps has {count} rows, expected >= {args.min_steps}",
                  file=sys.stderr)
            return 1

        print(f"OK: backup restores cleanly; steps has {count} rows")
        return 0
    finally:
        # cleanup must run on every path — success, failure, or exception
        subprocess.run(["docker", "rm", "-f", container], capture_output=True)


if __name__ == "__main__":
    sys.exit(main())
