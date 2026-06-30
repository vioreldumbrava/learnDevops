// Package config loads runtime configuration from environment variables.
// Twelve-factor style: everything that changes between environments comes
// from the environment, with sensible local defaults.
package config

import "os"

type Config struct {
	Port         string
	DatabaseURL  string
	RedisURL     string
	OTLPEndpoint string // host:port for OTLP/HTTP; empty disables tracing
	ServiceName  string
}

func Load() Config {
	return Config{
		Port:         getenv("PORT", "8080"),
		DatabaseURL:  getenv("DATABASE_URL", "postgres://dojo:dojo@localhost:5432/dojo?sslmode=disable"),
		RedisURL:     getenv("REDIS_URL", "redis://localhost:6379/0"),
		OTLPEndpoint: os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
		ServiceName:  getenv("OTEL_SERVICE_NAME", "dojo-api"),
	}
}

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
