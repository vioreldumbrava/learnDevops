#!/usr/bin/env bash
# heal.sh — revert every fault the injectors here can cause. Safe to run at any time.
set -euo pipefail
NS=devops-dojo
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# drill 1: the patched-in command isn't in api.yaml, so `kubectl apply` won't remove it
kubectl -n "$NS" patch deploy api --type json \
  -p '[{"op":"remove","path":"/spec/template/spec/containers/0/command"}]' 2>/dev/null || true

# drills 2, 4, 5: re-applying the manifest resets image, resources, and the Service selector
kubectl apply -f "$ROOT/deploy/k8s/base/api.yaml"

# drill 3: bring Postgres back
kubectl -n "$NS" scale statefulset/db --replicas=1

# drill 7: let writes through again (only once db is back up)
kubectl -n "$NS" rollout status statefulset/db --timeout=120s
kubectl -n "$NS" exec db-0 -- psql -U dojo -d dojo \
  -c "ALTER SYSTEM RESET default_transaction_read_only; SELECT pg_reload_conf();" || true

kubectl -n "$NS" rollout status deploy/api --timeout=120s
echo "Healed. Verify: curl http://localhost/api/steps"
