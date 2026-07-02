#!/usr/bin/env bash
# readonly-db.sh — drill 7: make Postgres reject writes (the disk-full failure signature,
# without actually filling the kind node's disk). Reads and probes stay green.
# Recover: ALTER SYSTEM RESET default_transaction_read_only   (or ./heal.sh)
set -euo pipefail
NS=devops-dojo

kubectl -n "$NS" exec db-0 -- psql -U dojo -d dojo \
  -c "ALTER SYSTEM SET default_transaction_read_only = on; SELECT pg_reload_conf();"
echo "Injected: reads work, writes fail. Probes stay green. Start diagnosing."
