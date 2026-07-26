-- Split "I read this lab" from "I can do this lab from memory".
--
-- completed  = worked through the lab with the repo open (recognition)
-- drilled    = passed the lab's closed-book drill inside its time target (recall)
--
-- last_practiced_at is what makes spaced repetition possible: the dashboard's "stalest"
-- list is an ORDER BY on this column. See docs/DRILLS.md and docs/WEEKLY.md.

ALTER TABLE progress
    ADD COLUMN IF NOT EXISTS drilled           BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS drilled_at        TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_practiced_at TIMESTAMPTZ;

-- Existing rows: a completed lab was practiced at least once, at completion time.
UPDATE progress
   SET last_practiced_at = completed_at
 WHERE last_practiced_at IS NULL
   AND completed_at IS NOT NULL;

-- Ordering the "what should I drill next" list is the only hot query on this table.
CREATE INDEX IF NOT EXISTS idx_progress_last_practiced ON progress (last_practiced_at);
