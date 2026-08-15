# Lab 06 — Database & migrations

**Maps to:** original §7 · **Milestone:** 1

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Your schema must evolve in a **versioned, repeatable** way — not by hand-editing tables on a
live server. A migration tool applies ordered `.up.sql` files and records which versions are
applied, so every environment converges to the same schema. We use **golang-migrate** as a
one-shot Compose service.

## What you'll do

Inspect the migrations, run them, read the version table, and add a new migration.

## Steps

```powershell
# Start just the database
docker compose -f deploy/compose/compose.yaml up -d db

# Apply migrations explicitly (the api also waits on this on a full `up`)
docker compose -f deploy/compose/compose.yaml run --rm migrate

# What got created + the version ledger
docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "\dt"
docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "select * from schema_migrations;"
docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "select count(*) from steps;"
```

The files live in [db/migrations/](../../db/migrations/): `000001_init` creates the tables,
`000002_seed_steps` is the historical seed; later checked-in migrations extend it.
Treat the manifest/API integrity check below—not an old fixed row count—as authoritative.

## How it works

`migrate` mounts `db/migrations` read-only and runs `migrate -path ... -database ... up`. It
records the highest applied version in `schema_migrations`. Re-running `up` is a no-op, which
is why the api can safely depend on it every boot. Each migration ships an `.up.sql` (apply)
and a `.down.sql` (roll back).

## Exercise

Add the **next available** migration that adds a `difficulty` column, then apply it. Never
copy a migration number from a tutorial: this repository grows over time, and two files with
the same version make the migration source invalid.

1. Allocate the next sequence number and create the pair:
   ```powershell
   $latest = Get-ChildItem db/migrations/*.up.sql |
     ForEach-Object { [int](($_.BaseName -split '_')[0]) } |
     Measure-Object -Maximum
   $migration = '{0:D6}' -f ($latest.Maximum + 1)
   $up = "db/migrations/${migration}_add_difficulty.up.sql"
   $down = "db/migrations/${migration}_add_difficulty.down.sql"
   New-Item $up, $down -ItemType File
   "$migration -> $up / $down"
   ```
2. Put this in the generated `.up.sql` file:
   ```sql
   ALTER TABLE steps ADD COLUMN IF NOT EXISTS difficulty TEXT NOT NULL DEFAULT 'beginner';
   ```
3. Put this in the generated `.down.sql` file:
   ```sql
   ALTER TABLE steps DROP COLUMN IF EXISTS difficulty;
   ```
4. Apply and verify:
   ```powershell
   docker compose -f deploy/compose/compose.yaml run --rm migrate
   docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "select version, dirty from schema_migrations;"
   ```

## Checkpoint

- ✅ `\dt` lists `steps`, `progress`, `notes`, `schema_migrations`.
- ✅ `select count(*) from steps;` matches the number of numbered directories under `labs/`.
- ✅ After the exercise, `schema_migrations.version` matches `$migration` and `dirty` is false.

## Common failures

- "dirty" migration state → a migration failed midway; `migrate ... force <version>` then fix
  the SQL. (Investigate the failing SQL first.)
- Old data after changing `.env` credentials → an old `db-data` volume persists; `down -v` for a clean DB.

➡️ Next: [Lab 07 — Backups & restore](../07-backup-restore/)
