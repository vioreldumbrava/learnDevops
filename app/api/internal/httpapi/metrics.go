package httpapi

import (
	"net/http"
	"strconv"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	httpRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "dojo_http_requests_total",
		Help: "Total HTTP requests processed, by method, route and status.",
	}, []string{"method", "route", "status"})

	httpDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "dojo_http_request_duration_seconds",
		Help:    "HTTP request latency in seconds.",
		Buckets: prometheus.DefBuckets,
	}, []string{"method", "route"})

	httpInFlight = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "dojo_http_in_flight_requests",
		Help: "Number of in-flight HTTP requests.",
	})
)

// statusRecorder captures the response status code for middleware.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

// metricsMiddleware records Prometheus metrics for each request. It runs inside
// the chi router so the matched route pattern (not the raw path) is the label,
// keeping cardinality bounded.
func metricsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		httpInFlight.Inc()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

		next.ServeHTTP(rec, r)

		httpInFlight.Dec()
		route := chi.RouteContext(r.Context()).RoutePattern()
		if route == "" {
			route = "unmatched"
		}
		httpDuration.WithLabelValues(r.Method, route).Observe(time.Since(start).Seconds())
		httpRequests.WithLabelValues(r.Method, route, strconv.Itoa(rec.status)).Inc()
	})
}
