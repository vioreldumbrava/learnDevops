-- Lab 55 — generate enough rows that the planner's choices actually matter.
--
-- Not a migration: this is throwaway drill data, loaded by hand and deleted at the end of
-- the lab. Migrations describe the schema every environment must have; this describes a
-- situation you are manufacturing on purpose. Keeping the two apart is the point.
--
--   docker compose -f deploy/compose/compose.yaml exec -T db \
--     psql -U dojo -d dojo -f - < db/seed/notes_bulk.sql
--
-- ~200k rows spread over the last 400 days across all seeded steps. On a laptop that is
-- big enough for a sequential scan to be obviously slow and small enough to load in
-- seconds.

INSERT INTO notes (step_id, body, created_at)
SELECT
    s.id,
    'drill note ' || g || ' for ' || s.id || ' — ' || md5(random()::text),
    now() - (random() * interval '400 days')
FROM steps s
CROSS JOIN generate_series(1, 3500) AS g;

-- ANALYZE, not VACUUM: the planner works off statistics, and a bulk insert leaves them
-- stale. Skip this and your first EXPLAIN reads the *old* table shape — a genuinely
-- common source of "the query plan makes no sense".
ANALYZE notes;

SELECT count(*) AS notes_rows,
       pg_size_pretty(pg_total_relation_size('notes')) AS total_size
FROM notes;
