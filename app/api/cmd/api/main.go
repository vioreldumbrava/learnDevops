// Command api is the DevOps Dojo REST API server.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"devops-dojo/internal/cache"
	"devops-dojo/internal/config"
	"devops-dojo/internal/httpapi"
	"devops-dojo/internal/store"
	"devops-dojo/internal/telemetry"
)

func main() {
	// Self-healthcheck mode: the distroless image has no shell/curl, so the
	// Compose/Kubernetes healthcheck runs `/api -healthcheck`.
	if len(os.Args) > 1 && os.Args[1] == "-healthcheck" {
		runHealthcheck()
		return
	}

	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	cfg := config.Load()
	ctx := context.Background()

	shutdownTracer, err := telemetry.Init(ctx, cfg.ServiceName, cfg.OTLPEndpoint)
	if err != nil {
		logger.Warn("tracing init failed; continuing without traces", "error", err)
		shutdownTracer = func(context.Context) error { return nil }
	}

	st, err := store.New(ctx, cfg.DatabaseURL)
	if err != nil {
		logger.Error("connect database", "error", err)
		os.Exit(1)
	}
	defer st.Close()

	c, err := cache.New(cfg.RedisURL)
	if err != nil {
		logger.Error("connect redis", "error", err)
		os.Exit(1)
	}
	defer c.Close()

	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      httpapi.New(st, c, logger),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		logger.Info("api listening", "addr", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("server error", "error", err)
			os.Exit(1)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop

	logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(shutdownCtx)
	_ = shutdownTracer(shutdownCtx)
}

// runHealthcheck performs a local liveness probe and sets the process exit code,
// so the container healthcheck can be the binary itself (no shell required).
func runHealthcheck() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	client := http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get("http://127.0.0.1:" + port + "/healthz")
	if err != nil {
		os.Exit(1)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		os.Exit(1)
	}
}
