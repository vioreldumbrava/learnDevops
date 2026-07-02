#!/usr/bin/env bash
# crashloop.sh — drill 1: point the API container at a binary that doesn't exist.
# Recover: kubectl -n devops-dojo rollout undo deploy/api   (or ./heal.sh)
set -euo pipefail
NS=devops-dojo

kubectl -n "$NS" patch deploy api --type json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/command","value":["/does-not-exist"]}]'
echo "Injected: api will CrashLoopBackOff. Start diagnosing."
