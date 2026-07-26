DROP INDEX IF EXISTS idx_progress_last_practiced;

ALTER TABLE progress
    DROP COLUMN IF EXISTS last_practiced_at,
    DROP COLUMN IF EXISTS drilled_at,
    DROP COLUMN IF EXISTS drilled;
