// Package store is the PostgreSQL data layer (curriculum, progress, notes).
package store

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"go.opentelemetry.io/otel"
)

var tracer = otel.Tracer("devops-dojo/store")

type Step struct {
	ID        string `json:"id"`
	LabNo     int    `json:"lab_no"`
	Title     string `json:"title"`
	Topic     string `json:"topic"`
	MapsTo    string `json:"maps_to"`
	Milestone int    `json:"milestone"`
	DocPath   string `json:"doc_path"`
	Summary   string `json:"summary"`
	Completed bool   `json:"completed"`
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
		       COALESCE(p.completed, false)
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
			&st.Milestone, &st.DocPath, &st.Summary, &st.Completed); err != nil {
			return nil, err
		}
		steps = append(steps, st)
	}
	return steps, rows.Err()
}

// SetProgress upserts the completion state of a step.
func (s *Store) SetProgress(ctx context.Context, stepID string, completed bool) error {
	ctx, span := tracer.Start(ctx, "store.SetProgress")
	defer span.End()

	var completedAt *time.Time
	if completed {
		now := time.Now()
		completedAt = &now
	}
	_, err := s.pool.Exec(ctx, `
		INSERT INTO progress (step_id, completed, completed_at, updated_at)
		VALUES ($1, $2, $3, now())
		ON CONFLICT (step_id) DO UPDATE
		SET completed = EXCLUDED.completed,
		    completed_at = EXCLUDED.completed_at,
		    updated_at = now()`,
		stepID, completed, completedAt)
	return err
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
