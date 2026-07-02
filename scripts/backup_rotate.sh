#!/usr/bin/env bash
# backup_rotate.sh — take a Postgres backup through the Compose stack, sanity-check it,
# and apply a retention policy (keep the newest N). Lab 37; extends lab 07.
#
# Usage: ./backup_rotate.sh [keep]     # default: keep 7
# Deep verification (actually restoring the dump) is verify_backup.py's job.
set -euo pipefail

KEEP="${1:-7}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$ROOT/backups"
COMPOSE=(docker compose -f "$ROOT/deploy/compose/compose.yaml")

[[ "$KEEP" =~ ^[0-9]+$ && "$KEEP" -ge 1 ]] || { echo "usage: $0 [keep>=1]" >&2; exit 2; }

echo "==> taking backup"
"${COMPOSE[@]}" run --rm db-backup

# newest first; mapfile is the safe way to read a list into an array (no word-splitting)
mapfile -t dumps < <(ls -1t "$BACKUP_DIR"/dojo_*.sql 2>/dev/null)
(( ${#dumps[@]} > 0 )) || { echo "ERROR: no dump found in $BACKUP_DIR" >&2; exit 1; }

newest="${dumps[0]}"
echo "==> newest: $newest ($(du -h "$newest" | cut -f1))"

# cheap integrity gate: an empty or truncated file is worse than no backup,
# because it makes you *feel* safe
head -n 5 "$newest" | grep -q "PostgreSQL database dump" \
  || { echo "ERROR: $newest does not look like a pg_dump" >&2; exit 1; }

if (( ${#dumps[@]} > KEEP )); then
  echo "==> pruning $(( ${#dumps[@]} - KEEP )) old backup(s), keeping newest $KEEP"
  printf '%s\n' "${dumps[@]:KEEP}" | xargs -r rm --
fi

echo "OK: $(ls -1 "$BACKUP_DIR"/dojo_*.sql | wc -l) backup(s) in $BACKUP_DIR"
