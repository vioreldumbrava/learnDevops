#!/usr/bin/env bash
# break-selector.sh — drill 4: one-letter typo in the api Service selector.
# Everything stays green; traffic just stops. Recover: fix the selector (or ./heal.sh).
set -euo pipefail
NS=devops-dojo

kubectl -n "$NS" patch svc api -p '{"spec":{"selector":{"app":"apy"}}}'
echo "Injected: api Service matches nothing. Pods look healthy. Start diagnosing."
