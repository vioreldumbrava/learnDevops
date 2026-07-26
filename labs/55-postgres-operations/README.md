# Lab 55 — Postgres under load

**Maps to:** extra · **Milestone:** 4 — Operate & Automate · **Generalist DevOps / SRE**

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

"The site is slow" is, more often than any other single cause, "the database is slow". Lab 06
taught you to *change* a schema and lab 07 to *back it up*; neither teaches you what to do when
a running database is the problem — which is the incident you are most likely to actually meet.

The method is always the same four steps, and it is worth memorising in this order:

1. **Which query?** — `pg_stat_statements`, ranked by *total* time, not mean. A 2 ms query run
   500,000 times beats a 400 ms query run twice.
2. **Why is it slow?** — `EXPLAIN (ANALYZE, BUFFERS)`. Read the actual rows vs estimated rows,
   and the buffer counts. Not the cost number.
3. **Fix it** — usually an index, sometimes a rewritten query, occasionally more memory.
4. **Prove it** — the same `EXPLAIN`, and the p95 panel in Grafana. A fix you didn't measure is
   a guess you got attached to.

Then there are the three failure modes that aren't about query plans at all, and that people
consistently can't diagnose: **lock contention**, **connection exhaustion**, and **bloat**.
This lab does all of it against the Dojo's real Postgres.

## What you'll do

Enable `pg_stat_statements`, load 200k rows, find and fix a sequential scan with a migration
you write yourself, then manufacture a lock and a connection storm and survive both.

---

## Steps

### 0. A diagnosable database

```powershell
$dc = "docker","compose","-f","deploy/compose/compose.yaml","-f","deploy/compose/compose.pgtune.yaml"
& $dc up -d --build
& $dc exec db psql -U dojo -d dojo -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
```

Read [`compose.pgtune.yaml`](../../deploy/compose/compose.pgtune.yaml) before you run it —
it also sets `max_connections=25` (for step 5), `log_min_duration_statement=200`, and
`log_lock_waits=on`.

> `shared_preload_libraries` is one of the settings that needs a **restart**, not a reload.
> Knowing which settings need which is a real interview question: `SELECT name, context FROM
> pg_settings WHERE name IN ('shared_preload_libraries','work_mem','max_connections');` —
> `postmaster` means restart, `user` means you can `SET` it in a session.

Load the drill data:

```powershell
Get-Content db/seed/notes_bulk.sql | & $dc exec -T db psql -U dojo -d dojo
```

```bash
# bash equivalent
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.pgtune.yaml \
  exec -T db psql -U dojo -d dojo -f - < db/seed/notes_bulk.sql
```

### 1. Which query? (`pg_stat_statements`)

Drive database-shaped load — [`db-load.js`](../../deploy/load-test/db-load.js) reads notes
across many steps and writes 20% of the time, so the Redis cache can't absorb it:

```powershell
& $dc exec db psql -U dojo -d dojo -c "SELECT pg_stat_statements_reset();"
& $dc run --rm -e VUS=30 -e DURATION=2m load-test run /scripts/db-load.js
```

Then rank by **total** time:

```sql
SELECT calls,
       round(total_exec_time::numeric, 1) AS total_ms,
       round(mean_exec_time::numeric, 2)  AS mean_ms,
       rows,
       left(query, 90) AS query
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 10;
```

Now find the query nobody wrote an index for — recent activity across *all* steps:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, step_id, body, created_at FROM notes ORDER BY created_at DESC LIMIT 20;
```

### 2. Why is it slow? (reading `EXPLAIN`)

You should see a `Seq Scan on notes` feeding a sort, with a large `Buffers: shared read=…`.
Read it in this order — and practise saying it out loud:

| What to look at | What it tells you |
|---|---|
| The **innermost** node | Plans read bottom-up; that's where time is actually spent |
| `Seq Scan` vs `Index Scan` | Is Postgres reading the whole table? |
| `rows=N` **estimated** vs `actual rows=N` | An order-of-magnitude gap means stale stats — `ANALYZE` |
| `Buffers: shared hit=` vs `read=` | `hit` is cache, `read` is disk. Lots of `read` = I/O bound |
| `Sort Method: external merge Disk:` | `work_mem` is too small; it spilled to disk |
| `actual time=first..last` | First-row vs total time — matters a lot with `LIMIT` |

Ignore `cost=`. It's the planner's *internal, unitless* estimate, useful only for comparing two
plans of the same query. Interviewers ask about it precisely because most people quote it as if
it were milliseconds.

### 3. Fix it — write the migration yourself

**Do not** hand-create the index in psql. Schema changes belong in
[`db/migrations/`](../../db/migrations/) (lab 06), including performance ones, because an index
that exists only on your laptop is the classic "it was fast in staging" incident.

Write `db/migrations/000005_notes_created_at_index.up.sql` and its `.down.sql`, apply with
`& $dc run --rm migrate`, then re-run the `EXPLAIN` from step 1.

Three things to decide while writing it, each of which is an interview answer:

- Which column, and **which direction**? (`ORDER BY created_at DESC LIMIT 20` — does a plain
  ascending index serve it?)
- `CREATE INDEX` or `CREATE INDEX CONCURRENTLY`? What does the plain form lock, and for how
  long, on a table with 200 million rows instead of 200 thousand?
- What does this index **cost** you? (Every `INSERT` into `notes` now maintains it — measure
  the write path in the k6 summary before and after.)

### 4. Lock contention (two terminals)

The drill people can't do. Terminal A:

```powershell
& $dc exec db psql -U dojo -d dojo
```
```sql
BEGIN;
UPDATE steps SET title = title WHERE id = '04-docker-compose';
-- and now just... sit here. This is "idle in transaction", the most expensive way to do
-- nothing in a database.
```

Terminal B, same command, then:

```sql
UPDATE steps SET title = title WHERE id = '04-docker-compose';   -- hangs
```

Terminal C — diagnose without guessing:

```sql
SELECT pid, state, wait_event_type, wait_event,
       now() - xact_start AS xact_age,
       left(query, 60) AS query
FROM pg_stat_activity
WHERE datname = 'dojo' AND state <> 'idle'
ORDER BY xact_start;

-- The one function to remember:
SELECT pid, pg_blocking_pids(pid) AS blocked_by, left(query, 60) AS query
FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

Resolve it:

```sql
SELECT pg_cancel_backend(<blocker_pid>);      -- polite: cancels the query
SELECT pg_terminate_backend(<blocker_pid>);   -- forceful: kills the connection
```

Try `pg_cancel_backend` on the idle-in-transaction session first and watch it do **nothing** —
there's no running query to cancel. That surprise is the lesson: `idle in transaction` holds
locks while executing nothing, which is why `idle_in_transaction_session_timeout` exists.

### 5. Connection exhaustion, then a pooler

`max_connections=25`, and every API replica holds a pool. Storm it:

```powershell
& $dc run --rm -e BURST=1 load-test run /scripts/db-load.js
& $dc logs api --tail 30      # expect: "sorry, too many clients already"
```

Save that k6 summary. Then put PgBouncer in front — no application change:

```powershell
$dcp = $dc + @("-f","deploy/compose/compose.pgbouncer.yaml")
& $dcp up -d
& $dcp run --rm -e BURST=1 load-test run /scripts/db-load.js
& $dcp exec pgbouncer psql -h 127.0.0.1 -p 6432 -U dojo pgbouncer -c "SHOW POOLS;"
```

Compare the two summaries. Then read
[`compose.pgbouncer.yaml`](../../deploy/compose/compose.pgbouncer.yaml) for what transaction
pooling **costs** — the DSN disables prepared statements for a reason.

### 6. Bloat and autovacuum

```sql
-- Churn: 200k dead tuples, no rows added.
UPDATE notes SET body = body WHERE id % 2 = 0;

SELECT relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       last_autovacuum, autovacuum_count
FROM pg_stat_user_tables WHERE relname = 'notes';

SELECT pg_size_pretty(pg_total_relation_size('notes')) AS size_now;
VACUUM (VERBOSE, ANALYZE) notes;
```

Note that `VACUUM` does **not** shrink the file — it marks space reusable. Only
`VACUUM FULL` (which takes an `ACCESS EXCLUSIVE` lock and rewrites the table, so: never on a
busy production table) returns disk to the OS. Say both halves of that in an interview.

### 7. Watch it in Grafana

The observability overlay (lab 10) is already scraping the API. Bring it up alongside and
capture the p95 panel across step 3's before/after — the screenshot is the artifact.

## How it works

- **`pg_stat_statements`** normalises queries (literals become `$1`) and aggregates them, so
  ten million distinct-looking statements collapse into the handful of shapes your app runs.
- **An index turns a sort into a walk.** `ORDER BY created_at DESC LIMIT 20` without an index
  must read *every* row and sort them to find twenty. With a matching index Postgres walks the
  B-tree backwards and stops after twenty.
- **Locks are held for the length of the transaction, not the statement.** That's why an
  open `BEGIN` with no active query still blocks writers.
- **A connection is a whole backend process** in Postgres (not a thread), which is why the
  ceiling is low and why a pooler — multiplexing many clients onto few backends — is the
  standard answer rather than "raise `max_connections`".

## Exercise

Two, both small and both interview-grade:

1. **Make the k6 threshold catch the regression.** Drop your index
   (`& $dc run --rm migrate down 1`), then set a `p(95)` threshold in `db-load.js` that the
   un-indexed build breaches and the indexed one passes. That's a **performance gate** — wire
   it into CI (lab 15) and the regression can never merge again.
2. **Add `idle_in_transaction_session_timeout`** to `compose.pgtune.yaml`, re-run the step-4
   drill, and watch the blocker get killed automatically. Then argue with yourself about
   whether that setting belongs in production.

## Checkpoint

- ✅ You can name the top query by **total** time and explain why total beats mean.
- ✅ `EXPLAIN (ANALYZE, BUFFERS)` shows `Seq Scan` before your migration and an index scan
   after, with a measurably lower `actual time` — and you have the Grafana p95 before/after.
- ✅ In the lock drill you name the blocking PID via `pg_blocking_pids()` and explain why
   `pg_cancel_backend` doesn't touch an idle-in-transaction session.
- ✅ The burst that returned 500s without PgBouncer completes with it, with no app change.

## Common failures

- `pg_stat_statements` doesn't exist → the extension needs `CREATE EXTENSION` **and** the
  overlay's `shared_preload_libraries` **and** a restart. All three.
- Every plan is a `Seq Scan` even after the index → the table is small enough that a scan is
  genuinely cheaper (Postgres is right), or stats are stale — `ANALYZE notes;`.
- The `EXPLAIN` is fast but the app is slow → you're measuring the wrong query. Go back to
  `pg_stat_statements` instead of guessing.
- PgBouncer connects but queries fail oddly → prepared statements in transaction pooling mode;
  check the `default_query_exec_mode` / `statement_cache_capacity` parameters in the DSN.
- Cleaning up: `DELETE FROM notes WHERE body LIKE 'drill note %';` then `VACUUM ANALYZE notes;`

## Maps to

Lab [06](../06-database-migrations/) (the fix ships as a migration), lab
[10](../10-monitoring/) (where you prove it), lab [20](../20-load-testing/) (the threshold that
gates it), lab [35](../35-incident-response/) (the DB-lock drill, now with a method behind it),
and lab [52](../52-k8s-storage/) (what protects `data-db-0` when this database is in Kubernetes).

➡️ Next: [Lab 56 — SLOs & error budgets](../56-slo-and-error-budgets/)
