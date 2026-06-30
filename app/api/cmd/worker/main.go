// Command worker consumes jobs from the Redis queue. It stands in for the kind
// of background processing (report/certificate generation) you offload from the
// request path — and being stateless, it is what you scale in lab 21.
package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"devops-dojo/internal/cache"
	"devops-dojo/internal/config"
	"devops-dojo/internal/httpapi"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	cfg := config.Load()

	c, err := cache.New(cfg.RedisURL)
	if err != nil {
		logger.Error("connect redis", "error", err)
		os.Exit(1)
	}
	defer c.Close()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	logger.Info("worker started", "queue", httpapi.JobQueue)
	for {
		if ctx.Err() != nil {
			logger.Info("worker stopping")
			return
		}

		job, ok, err := c.Dequeue(ctx, httpapi.JobQueue, 5*time.Second)
		if err != nil {
			if ctx.Err() != nil {
				return
			}
			logger.Error("dequeue", "error", err)
			time.Sleep(time.Second)
			continue
		}
		if !ok {
			continue // timed out, poll again
		}

		// Simulate generating a progress report / certificate.
		logger.Info("processing job", "job", job)
		time.Sleep(500 * time.Millisecond)
		logger.Info("job done", "job", job)
	}
}
