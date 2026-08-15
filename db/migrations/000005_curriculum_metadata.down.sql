ALTER TABLE steps
    DROP COLUMN IF EXISTS drill_required,
    DROP COLUMN IF EXISTS cost_class,
    DROP COLUMN IF EXISTS effort_minutes,
    DROP COLUMN IF EXISTS "requires",
    DROP COLUMN IF EXISTS tracks,
    DROP COLUMN IF EXISTS tier;
