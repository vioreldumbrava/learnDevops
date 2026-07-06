-- Rollback pair for 000002_seed_steps.up.sql: remove the seeded curriculum rows.
-- (progress/notes rows cascade via their foreign keys to steps.)
DELETE FROM steps;
