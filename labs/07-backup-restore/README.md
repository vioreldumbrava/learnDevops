# Lab 07 — Backups & restore

**Maps to:** original §8 · **Milestone:** 1

## Concept

Containers are disposable; **data is not**. Database state lives in a named volume, and a
backup must live **outside** the database container (here: the host's `./backups/` folder).
A restore must be explicit and repeatable — you should be able to prove a backup actually
works, not just that it was created.

## What you'll do

Take a backup, simulate data loss, and restore it.

## Steps

```powershell
# Make sure the DB is up and migrated
docker compose -f deploy/compose/compose.yaml up -d db
docker compose -f deploy/compose/compose.yaml run --rm migrate

# Add a note so we have data to lose, then back up
docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "insert into notes(step_id, body) values ('00-prerequisites','backup me');"
docker compose -f deploy/compose/compose.yaml run --rm db-backup
Get-ChildItem backups
```

Now simulate disaster and restore:

```powershell
# Destroy the note
docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "delete from notes;"

# Restore from your backup (use the filename printed above)
docker compose -f deploy/compose/compose.yaml run --rm -e BACKUP_FILE=dojo_YYYYmmdd_HHMMSS.sql db-restore

# Verify the note is back
docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "select body from notes;"
```

## How it works

`db-backup` and `db-restore` are short-lived `postgres` containers (in the `backup` profile
so they don't run on `up`). Backup runs `pg_dump` to a timestamped `.sql` file in the
host-mounted `./backups/`; restore runs `psql -f` on a file you name with `BACKUP_FILE`.
Because the dump is on the host, it survives even `docker compose down -v`.

## Exercise

Do a **full** disaster drill: `docker compose ... down -v` (wipes the volume), then `up -d db`,
`run --rm migrate`, and restore your backup. Confirm the note returns from nothing.

## Checkpoint

- ✅ A `dojo_*.sql` file appears under `./backups/`.
- ✅ After deleting the note and restoring, `select body from notes;` shows `backup me`.
- ✅ (Exercise) The restore works even after `down -v`.

## Common failures

- `Set BACKUP_FILE=...` message → you didn't pass `-e BACKUP_FILE=<file>` (the name only, it
  resolves under `./backups/`).
- Restore before the DB is healthy → `up -d db` and wait for the healthcheck first.

➡️ Next: [Lab 08 — Health checks](../08-health-checks/)
