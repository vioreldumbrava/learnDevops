package config

import (
	"os"
	"testing"
)

func TestLoadDefaults(t *testing.T) {
	os.Clearenv()
	c := Load()
	if c.Port != "8080" {
		t.Errorf("Port default = %q, want 8080", c.Port)
	}
	if c.ServiceName != "dojo-api" {
		t.Errorf("ServiceName default = %q, want dojo-api", c.ServiceName)
	}
	if c.OTLPEndpoint != "" {
		t.Errorf("OTLPEndpoint default = %q, want empty (tracing off)", c.OTLPEndpoint)
	}
}

func TestLoadOverridesFromEnv(t *testing.T) {
	os.Clearenv()
	os.Setenv("PORT", "9999")
	os.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "tempo:4318")
	t.Cleanup(os.Clearenv)

	c := Load()
	if c.Port != "9999" {
		t.Errorf("Port = %q, want 9999", c.Port)
	}
	if c.OTLPEndpoint != "tempo:4318" {
		t.Errorf("OTLPEndpoint = %q, want tempo:4318", c.OTLPEndpoint)
	}
}
