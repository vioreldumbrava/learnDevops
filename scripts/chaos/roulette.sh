#!/usr/bin/env bash
# roulette.sh — drill 8: inject one random fault without telling you which.
# The answer is written to scripts/chaos/.last_fault — no peeking until you've diagnosed.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FAULTS=(crashloop.sh oom.sh kill-db.sh break-selector.sh bad-image.sh readonly-db.sh)
PICK="${FAULTS[RANDOM % ${#FAULTS[@]}]}"

echo "$(date -u +%FT%TZ) $PICK" >> "$DIR/.last_fault"
bash "$DIR/$PICK" > /dev/null
echo "Something is broken. Start the timer, work the loop. (Answer in .last_fault)"
