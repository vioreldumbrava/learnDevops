# Runbook — restore the database from backup

**Trigger:** data loss/corruption (bad migration, accidental delete, failed disk), or a
restore *drill* — run this quarterly even without an incident; an untested backup isn't one.
**Impact while running:** writes should be stopped; brief read staleness after restore.
**Prerequisite:** backups exist under `./backups/` (lab 07). Check **before** you need one.

## On Compose (labs 04–07 stack)

```powershell
# 1. What do we have? Pick the newest good backup.
Get-ChildItem backups\

# 2. Freshest possible copy of current state, even if damaged (you may need it for forensics)
docker compose -f deploy/compose/compose.yaml run --rm db-backup

# 3. Restore the chosen file
docker compose -f deploy/compose/compose.yaml run --rm -e BACKUP_FILE=<file>.sql db-restore

# 4. Verify — the whole point
docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "SELECT count(*) FROM steps;"
```

## On Kubernetes (lab 22 stack)

The Compose backup services don't exist here; use `psql`/`pg_dump` through the pod:

```powershell
# 1. Take a safety dump of current state
kubectl -n devops-dojo exec db-0 -- pg_dump -U dojo -d dojo > backups/pre-restore_$(Get-Date -Format yyyyMMdd_HHmmss).sql

# 2. Stop writers so the restore isn't racing the app
kubectl -n devops-dojo scale deploy/api deploy/worker --replicas=0

# 3. Restore (plain-format dump ≤ a few MB pipes fine through stdin)
Get-Content backups\<file>.sql | kubectl -n devops-dojo exec -i db-0 -- psql -U dojo -d dojo

# 4. Verify, then bring the app back
kubectl -n devops-dojo exec db-0 -- psql -U dojo -d dojo -c "SELECT count(*) FROM steps;"
kubectl -n devops-dojo scale deploy/api --replicas=2
kubectl -n devops-dojo scale deploy/worker --replicas=1
```

For whole-cluster/PVC disasters, Velero (lab 33) is the tool — this runbook covers logical
(SQL-level) restore only.

## Gotchas seen before

| Signature | Cause / handling |
|-----------|------------------|
| restore "succeeds" but data missing | restored into the wrong DB — verify `-d dojo` and count rows |
| duplicate-key errors during restore | restoring on top of live data — plain dumps aren't idempotent; restore into a clean DB or accept the errors knowingly |
| `schema_migrations` dirty after restore | backup taken mid-migration — see lab 35 drill 6 for the reset |

## After the incident

- Record: which backup was used, data window lost (time between backup and incident).
- If the loss window hurt, raise backup frequency (and revisit retention — lab 37's
  `backup_rotate.sh`).
- Postmortem: [../postmortem-template.md](../postmortem-template.md).
