// Package store is the PostgreSQL data layer (curriculum, progress, notes).
package store

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"go.opentelemetry.io/otel"
)

var tracer = otel.Tracer("devops-dojo/store")

// Step is one lab plus this learner's state on it.
//
// Completed and Drilled are deliberately independent: Completed means "worked through it
// with the repo open" (recognition), Drilled means "passed the closed-book drill inside its
// time target" (recall). LastPracticedAt drives the spaced-repetition list — see
// docs/DRILLS.md.
type Step struct {
	ID              string     `json:"id"`
	LabNo           int        `json:"lab_no"`
	Title           string     `json:"title"`
	Topic           string     `json:"topic"`
	MapsTo          string     `json:"maps_to"`
	Milestone       int        `json:"milestone"`
	DocPath         string     `json:"doc_path"`
	Summary         string     `json:"summary"`
	Tier            string     `json:"tier"`
	Tracks          []string   `json:"tracks"`
	Requires        []string   `json:"requires"`
	EffortMinutes   int        `json:"effort_minutes"`
	CostClass       string     `json:"cost_class"`
	DrillRequired   bool       `json:"drill_required"`
	Completed       bool       `json:"completed"`
	Drilled         bool       `json:"drilled"`
	LastPracticedAt *time.Time `json:"last_practiced_at"`
}

// Progress is a step's state on its own — what a write returns.
type Progress struct {
	StepID          string     `json:"step_id"`
	Completed       bool       `json:"completed"`
	Drilled         bool       `json:"drilled"`
	LastPracticedAt *time.Time `json:"last_practiced_at"`
}

type Note struct {
	ID        int64     `json:"id"`
	StepID    string    `json:"step_id"`
	Body      string    `json:"body"`
	CreatedAt time.Time `json:"created_at"`
}

type Store struct {
	pool *pgxpool.Pool
}

func New(ctx context.Context, url string) (*Store, error) {
	pool, err := pgxpool.New(ctx, url)
	if err != nil {
		return nil, err
	}
	return &Store{pool: pool}, nil
}

func (s *Store) Close() { s.pool.Close() }

func (s *Store) Ping(ctx context.Context) error { return s.pool.Ping(ctx) }

// ListSteps returns the full curriculum with each step's completion flag.
func (s *Store) ListSteps(ctx context.Context) ([]Step, error) {
	ctx, span := tracer.Start(ctx, "store.ListSteps")
	defer span.End()

	rows, err := s.pool.Query(ctx, `
		SELECT s.id, s.lab_no, s.title, s.topic, s.maps_to, s.milestone, s.doc_path, s.summary,
		       s.tier, s.tracks, s."requires", s.effort_minutes, s.cost_class, s.drill_required,
		       COALESCE(p.completed, false), COALESCE(p.drilled, false), p.last_practiced_at
		FROM steps s
		LEFT JOIN progress p ON p.step_id = s.id
		ORDER BY s.sort_order`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	steps := []Step{}
	for rows.Next() {
		var st Step
		if err := rows.Scan(&st.ID, &st.LabNo, &st.Title, &st.Topic, &st.MapsTo,
			&st.Milestone, &st.DocPath, &st.Summary, &st.Tier, &st.Tracks, &st.Requires,
			&st.EffortMinutes, &st.CostClass, &st.DrillRequired, &st.Completed,
			&st.Drilled, &st.LastPracticedAt); err != nil {
			return nil, err
		}
		steps = append(steps, st)
	}
	return steps, rows.Err()
}

// SetProgress upserts a step's state. completed and drilled are pointers so a caller can
// change one flag without clobbering the other: nil means "leave as it is". Either way the
// step counts as practiced right now, which is what the spaced-repetition list reads.
//
// It returns the resulting state via RETURNING (no second round trip) — the caller needs it
// because a request that sets only one flag still has to report both.
//
// The $n::boolean casts are load-bearing: inside COALESCE/CASE, Postgres cannot infer a
// parameter's type from context and errors out without them.
func (s *Store) SetProgress(ctx context.Context, stepID string, completed, drilled *bool) (Progress, error) {
	ctx, span := tracer.Start(ctx, "store.SetProgress")
	defer span.End()

	var p Progress
	err := s.pool.QueryRow(ctx, `
		INSERT INTO progress (step_id, completed, completed_at, drilled, drilled_at,
		                      last_practiced_at, updated_at)
		VALUES ($1,
		        COALESCE($2::boolean, false),
		        CASE WHEN COALESCE($2::boolean, false) THEN now() END,
		        COALESCE($3::boolean, false),
		        CASE WHEN COALESCE($3::boolean, false) THEN now() END,
		        now(), now())
		ON CONFLICT (step_id) DO UPDATE
		SET completed    = COALESCE($2::boolean, progress.completed),
		    completed_at = CASE WHEN $2::boolean IS NULL THEN progress.completed_at
		                        WHEN $2::boolean THEN now() END,
		    drilled      = COALESCE($3::boolean, progress.drilled),
		    drilled_at   = CASE WHEN $3::boolean IS NULL THEN progress.drilled_at
		                        WHEN $3::boolean THEN now() END,
		    last_practiced_at = now(),
		    updated_at        = now()
		RETURNING step_id, completed, drilled, last_practiced_at`,
		stepID, completed, drilled).
		Scan(&p.StepID, &p.Completed, &p.Drilled, &p.LastPracticedAt)
	return p, err
}

func (s *Store) StepExists(ctx context.Context, stepID string) (bool, error) {
	var exists bool
	err := s.pool.QueryRow(ctx, `SELECT EXISTS(SELECT 1 FROM steps WHERE id=$1)`, stepID).Scan(&exists)
	return exists, err
}

func (s *Store) ListNotes(ctx context.Context, stepID string) ([]Note, error) {
	rows, err := s.pool.Query(ctx,
		`SELECT id, step_id, body, created_at FROM notes WHERE step_id=$1 ORDER BY created_at`, stepID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	notes := []Note{}
	for rows.Next() {
		var n Note
		if err := rows.Scan(&n.ID, &n.StepID, &n.Body, &n.CreatedAt); err != nil {
			return nil, err
		}
		notes = append(notes, n)
	}
	return notes, rows.Err()
}

func (s *Store) AddNote(ctx context.Context, stepID, body string) (Note, error) {
	var n Note
	err := s.pool.QueryRow(ctx,
		`INSERT INTO notes (step_id, body) VALUES ($1, $2)
		 RETURNING id, step_id, body, created_at`,
		stepID, body).Scan(&n.ID, &n.StepID, &n.Body, &n.CreatedAt)
	return n, err
}
