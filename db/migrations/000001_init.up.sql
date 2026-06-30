-- Curriculum steps (one row per lab), progress tracking, and per-step notes.

CREATE TABLE IF NOT EXISTS steps (
    id          TEXT PRIMARY KEY,
    lab_no      INTEGER NOT NULL,
    title       TEXT    NOT NULL,
    topic       TEXT    NOT NULL,
    maps_to     TEXT    NOT NULL DEFAULT '',
    milestone   INTEGER NOT NULL DEFAULT 1,
    doc_path    TEXT    NOT NULL DEFAULT '',
    summary     TEXT    NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    step_id      TEXT PRIMARY KEY REFERENCES steps(id) ON DELETE CASCADE,
    completed    BOOLEAN     NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notes (
    id         BIGSERIAL PRIMARY KEY,
    step_id    TEXT        NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
    body       TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notes_step ON notes (step_id);
