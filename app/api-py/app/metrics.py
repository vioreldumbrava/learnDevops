"""Prometheus metrics — the SAME names and labels as the Go app's
internal/httpapi/metrics.go, on purpose. Because both services export
``dojo_http_requests_total`` / ``dojo_http_request_duration_seconds`` /
``dojo_http_in_flight_requests``, the existing Prometheus scrape config,
Grafana dashboards and alerts (labs 10/12) work against either implementation
with no changes. Shared metric names are the observability half of the shared
contract.
"""
from prometheus_client import Counter, Gauge, Histogram

http_requests = Counter(
    "dojo_http_requests_total",
    "Total HTTP requests processed, by method, route and status.",
    ["method", "route", "status"],
)

# Default buckets match prometheus.DefBuckets used on the Go side, so the two
# histograms are directly comparable in the same dashboard panel.
http_duration = Histogram(
    "dojo_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_in_flight = Gauge(
    "dojo_http_in_flight_requests",
    "Number of in-flight HTTP requests.",
)
