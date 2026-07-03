package main

import (
	"fmt"
	"sort"
)

func main() {
	fmt.Println("Hello, World!")

	// --- Slices ---
	// A slice is a dynamically-sized view over an array.
	languages := []string{"Go", "Python", "Bash"}

	// Append grows the slice (reallocating the backing array if needed).
	languages = append(languages, "Terraform HCL", "YAML")

	fmt.Printf("\nSlice: %v (len=%d, cap=%d)\n", languages, len(languages), cap(languages))

	// Slicing: half-open range [low:high).
	firstTwo := languages[:2]
	fmt.Println("First two:", firstTwo)

	// Iterate with index and value.
	for i, lang := range languages {
		fmt.Printf("  %d: %s\n", i, lang)
	}

	// --- Maps (hash tables) ---
	// A map is Go's built-in hash table: keys hash to buckets, giving
	// average O(1) lookup, insert, and delete.
	yearCreated := map[string]int{
		"Go":     2009,
		"Python": 1991,
		"Bash":   1989,
	}

	// Insert / update.
	yearCreated["YAML"] = 2001

	// Lookup with the "comma ok" idiom to distinguish a missing key
	// from a zero value.
	if year, ok := yearCreated["Go"]; ok {
		fmt.Printf("\nGo was created in %d\n", year)
	}
	if _, ok := yearCreated["Rust"]; !ok {
		fmt.Println("Rust is not in the map")
	}

	// Delete a key.
	delete(yearCreated, "Bash")

	// Map iteration order is intentionally random in Go, so sort the
	// keys first for deterministic output.
	keys := make([]string, 0, len(yearCreated))
	for k := range yearCreated {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	fmt.Println("\nLanguages by year:")
	for _, k := range keys {
		fmt.Printf("  %-6s -> %d\n", k, yearCreated[k])
	}

	// --- Combining them: map of string -> slice ---
	toolsByCategory := map[string][]string{
		"containers": {"Docker", "Podman"},
		"iac":        {"Terraform", "Ansible"},
	}
	toolsByCategory["containers"] = append(toolsByCategory["containers"], "Kubernetes")

	fmt.Println("\nTools by category:")
	for _, category := range []string{"containers", "iac"} {
		fmt.Printf("  %s: %v\n", category, toolsByCategory[category])
	}
}
