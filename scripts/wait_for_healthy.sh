#!/usr/bin/env bash
# wait_for_healthy.sh — block until an HTTP endpoint answers 2xx, or time out.
# The building block of every "deploy, then smoke-test" pipeline step. Lab 37.
#
# Usage: ./wait_for_healthy.sh [url] [timeout_seconds]
#   ./wait_for_healthy.sh                                  # api readiness, 60s
#   ./wait_for_healthy.sh http://localhost/healthz 120
set -euo pipefail

URL="${1:-http://localhost:8080/readyz}"
TIMEOUT="${2:-60}"
start="$(date +%s)"

# trap runs on ANY exit (success, failure, Ctrl-C) — cleanup/reporting lives here,
# so no exit path can skip it
report() { echo " (waited $(( $(date +%s) - start ))s)"; }
trap report EXIT

until curl --fail --silent --show-error --max-time 2 "$URL" > /dev/null 2>&1; do
  if (( $(date +%s) - start >= TIMEOUT )); then
    echo -n "TIMEOUT: $URL not healthy after ${TIMEOUT}s" >&2
    exit 1
  fi
  printf '.'
  sleep 2
done

echo -n "OK: $URL is healthy"
