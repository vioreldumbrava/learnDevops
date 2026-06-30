// Package telemetry wires up OpenTelemetry tracing exporting over OTLP/HTTP.
package telemetry

import (
	"context"
	"strings"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// Init configures the global tracer provider to export spans to the OTLP/HTTP
// endpoint (host:port, scheme optional). When endpoint is empty, tracing is
// disabled and the returned shutdown func is a no-op.
func Init(ctx context.Context, serviceName, endpoint string) (func(context.Context) error, error) {
	noop := func(context.Context) error { return nil }
	if endpoint == "" {
		return noop, nil
	}

	// Accept "http://host:port", "https://host:port" or bare "host:port".
	endpoint = strings.TrimPrefix(endpoint, "http://")
	endpoint = strings.TrimPrefix(endpoint, "https://")

	exp, err := otlptracehttp.New(ctx,
		otlptracehttp.WithEndpoint(endpoint),
		otlptracehttp.WithInsecure(),
	)
	if err != nil {
		return noop, err
	}

	res, err := resource.New(ctx,
		resource.WithAttributes(attribute.String("service.name", serviceName)),
	)
	if err != nil {
		res = resource.Default()
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp, sdktrace.WithBatchTimeout(5*time.Second)),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)
	return tp.Shutdown, nil
}
