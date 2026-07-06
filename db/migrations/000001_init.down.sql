-- Rollback pair for 000001_init.up.sql — golang-migrate runs this on `migrate down`.
-- Every migration ships with its undo so a bad deploy can be reversed (lab 06).
-- Drop order matters: progress and notes reference steps, so children go first.
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS progress;
DROP TABLE IF EXISTS steps;
