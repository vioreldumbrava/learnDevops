package store

import (
	"encoding/json"
	"testing"
)

func TestStepJSONContractIncludesCurriculumMetadata(t *testing.T) {
	step := Step{
		ID:            "22-kubernetes",
		Tier:          "core",
		Tracks:        []string{"common-core"},
		Requires:      []string{"08-health-checks"},
		EffortMinutes: 180,
		CostClass:     "local",
		DrillRequired: true,
	}

	body, err := json.Marshal(step)
	if err != nil {
		t.Fatal(err)
	}
	var got map[string]any
	if err := json.Unmarshal(body, &got); err != nil {
		t.Fatal(err)
	}

	for _, key := range []string{
		"id", "lab_no", "title", "topic", "maps_to", "milestone", "doc_path", "summary",
		"tier", "tracks", "requires", "effort_minutes", "cost_class", "drill_required",
		"completed", "drilled", "last_practiced_at",
	} {
		if _, ok := got[key]; !ok {
			t.Errorf("Step JSON is missing %q", key)
		}
	}
	if got["tier"] != "core" || got["cost_class"] != "local" || got["drill_required"] != true {
		t.Fatalf("unexpected curriculum metadata: %#v", got)
	}
}
