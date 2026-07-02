#!/usr/bin/env bash
# kill-db.sh — drill 3: take Postgres away and watch readiness drain the API.
# Recover: kubectl -n devops-dojo scale statefulset/db --replicas=1   (or ./heal.sh)
set -euo pipefail
NS=devops-dojo

kubectl -n "$NS" scale statefulset/db --replicas=0
echo "Injected: db is gone; api pods will go NotReady. Start diagnosing."
