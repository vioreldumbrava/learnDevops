# Go Hello World — Slices & Maps

A minimal Go program that prints "Hello, World!" and demonstrates the two
core built-in collections:

- **Slices** — dynamic arrays: literal creation, `append`, `len`/`cap`,
  slicing (`s[:2]`), and `range` iteration.
- **Maps (hash tables)** — average O(1) lookup/insert/delete, the
  "comma ok" idiom for missing keys, `delete`, and sorted-key iteration
  (map order is random in Go).
- **Combined** — a `map[string][]string` (map of slices).

## Run

```bash
cd golang/hello-world
go run .
```
