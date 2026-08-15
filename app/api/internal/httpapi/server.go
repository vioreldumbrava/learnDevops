// Package httpapi defines the REST API: curriculum, progress, notes, plus the
// /healthz, /readyz and /metrics operational endpoints.
package httpapi

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"

	"devops-dojo/internal/cache"
	"devops-dojo/internal/store"
)

// JobQueue is the Redis list the worker consumes.
const JobQueue = "dojo:jobs"

// Version the cache key when the additive response schema changes so a rolling
// deployment cannot serve pre-metadata JSON from an older API instance.
const stepsCacheKey = "steps:v2:all"

type Server struct {
	store  *store.Store
	cache  *cache.Cache
	logger *slog.Logger
}

// New builds the HTTP handler with middleware and routes wired up.
func New(st *store.Store, c *cache.Cache, logger *slog.Logger) http.Handler {
	s := &Server{store: st, cache: c, logger: logger}

	r := chi.NewRouter()
	r.Use(middleware.Recoverer)
	r.Use(s.requestLogger)
	r.Use(metricsMiddleware)

	r.Get("/healthz", s.handleLive)
	r.Get("/readyz", s.handleReady)
	r.Handle("/metrics", promhttp.Handler())

	r.Route("/api", func(r chi.Router) {
		r.Get("/steps", s.handleSteps)
		r.Post("/progress/{id}", s.handleSetProgress)
		r.Get("/notes", s.handleListNotes)
		r.Post("/notes", s.handleAddNote)
	})

	// Wrap the entire router in OpenTelemetry server instrumentation.
	return otelhttp.NewHandler(r, "dojo-api")
}

// handleLive is the liveness probe: process is up. No dependency checks.
func (s *Server) handleLive(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// handleReady is the readiness probe: can the app actually serve traffic?
func (s *Server) handleReady(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	checks := map[string]string{"db": "ok", "redis": "ok"}
	ready := true
	if err := s.store.Ping(ctx); err != nil {
		checks["db"] = err.Error()
		ready = false
	}
	if err := s.cache.Ping(ctx); err != nil {
		checks["redis"] = err.Error()
		ready = false
	}

	code := http.StatusOK
	if !ready {
		code = http.StatusServiceUnavailable
	}
	writeJSON(w, code, checks)
}

func (s *Server) handleSteps(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	if v, ok, _ := s.cache.Get(ctx, stepsCacheKey); ok {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("X-Cache", "HIT")
		_, _ = w.Write([]byte(v))
		return
	}

	steps, err := s.store.ListSteps(ctx)
	if err != nil {
		s.serverError(w, "list steps", err)
		return
	}
	body, _ := json.Marshal(steps)
	_ = s.cache.Set(ctx, stepsCacheKey, string(body), 30*time.Second)

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Cache", "MISS")
	_, _ = w.Write(body)
}

func (s *Server) handleSetProgress(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	id := chi.URLParam(r, "id")

	// Pointers, so {"completed":true} leaves `drilled` alone and vice versa. A body with
	// neither field is a no-op the caller almost certainly didn't mean, so it's a 400.
	var req struct {
		Completed *bool `json:"completed"`
		Drilled   *bool `json:"drilled"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid body"})
		return
	}
	if req.Completed == nil && req.Drilled == nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "set completed and/or drilled"})
		return
	}

	exists, err := s.store.StepExists(ctx, id)
	if err != nil {
		s.serverError(w, "step exists", err)
		return
	}
	if !exists {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "unknown step"})
		return
	}

	p, err := s.store.SetProgress(ctx, id, req.Completed, req.Drilled)
	if err != nil {
		s.serverError(w, "set progress", err)
		return
	}

	// Invalidate the cached steps list and queue a report-refresh job.
	_ = s.cache.Del(ctx, stepsCacheKey)
	_ = s.cache.Enqueue(ctx, JobQueue, "progress:"+id)

	writeJSON(w, http.StatusOK, p)
}

func (s *Server) handleListNotes(w http.ResponseWriter, r *http.Request) {
	stepID := r.URL.Query().Get("step")
	if stepID == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "missing step query param"})
		return
	}
	notes, err := s.store.ListNotes(r.Context(), stepID)
	if err != nil {
		s.serverError(w, "list notes", err)
		return
	}
	writeJSON(w, http.StatusOK, notes)
}

func (s *Server) handleAddNote(w http.ResponseWriter, r *http.Request) {
	var req struct {
		StepID string `json:"step_id"`
		Body   string `json:"body"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.StepID == "" || req.Body == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "step_id and body are required"})
		return
	}
	note, err := s.store.AddNote(r.Context(), req.StepID, req.Body)
	if err != nil {
		s.serverError(w, "add note", err)
		return
	}
	writeJSON(w, http.StatusCreated, note)
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func (s *Server) serverError(w http.ResponseWriter, msg string, err error) {
	s.logger.Error(msg, "error", err)
	writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error"})
}

// requestLogger emits one structured JSON line per request (Loki-friendly),
// skipping the noisy liveness/metrics endpoints.
func (s *Server) requestLogger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)

		if r.URL.Path == "/healthz" || r.URL.Path == "/metrics" {
			return
		}
		s.logger.Info("http_request",
			"method", r.Method,
			"path", r.URL.Path,
			"status", rec.status,
			"duration_ms", time.Since(start).Milliseconds(),
			"remote", r.RemoteAddr,
		)
	})
}
