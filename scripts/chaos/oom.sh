#!/usr/bin/env bash
# oom.sh — drill 2: starve the API of memory so the kernel OOM-kills it.
# Recover: kubectl -n devops-dojo rollout undo deploy/api   (or ./heal.sh)
set -euo pipefail
NS=devops-dojo

kubectl -n "$NS" patch deploy api --type json -p '[
  {"op":"replace","path":"/spec/template/spec/containers/0/resources/requests/memory","value":"8Mi"},
  {"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"8Mi"}
]'
echo "Injected: api will be OOMKilled (exit 137). Start diagnosing."
