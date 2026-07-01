# Lab 20 — Load testing (k6)

**Maps to:** original §18 · **Milestone:** 3

## Concept

You don't know your system's limits until you push it. **k6** drives concurrent virtual
users (VUs) at an endpoint and reports latency and error rates against **thresholds** you
define — turning "seems fast" into pass/fail numbers, before real users find the ceiling.

## What you'll do

Run a short load test against the API and read the results.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml up -d api

# Default run (10 VUs, 30s) against the API
docker compose -f deploy/compose/compose.yaml run --rm load-test

# Turn it up
docker compose -f deploy/compose/compose.yaml run --rm -e VUS=50 -e DURATION=1m load-test

# Point it at the frontend instead
docker compose -f deploy/compose/compose.yaml up -d frontend
docker compose -f deploy/compose/compose.yaml run --rm -e TARGET_URL=http://frontend:80 load-test

docker compose -f deploy/compose/compose.yaml down -v
```

## How it works

[load-test.js](../../deploy/load-test/load-test.js) defines `options.thresholds`:
`http_req_failed rate<0.01` (<1% errors) and `http_req_duration p(95)<500` (95th percentile
under 500 ms). k6 runs inside the Compose network, so it hits `api:8080` directly. If a
threshold is breached, **k6 exits non-zero** — which is exactly how you'd gate a deploy in CI.

## Exercise

Find the knee: increase `VUS` (50 → 100 → 200) until a threshold fails, and watch which one
goes first (latency p95, or error rate). Then bump `--scale api=3` (see lab 21) and re-run —
the failure point should move. That's capacity planning in miniature.

## Checkpoint

- ✅ A k6 summary prints with `http_req_duration` and `http_req_failed`.
- ✅ You can explain what `p(95)<500` means and why thresholds gate CI.
- ✅ Raising VUs eventually breaches a threshold (non-zero exit).

## Common failures

- `dial tcp ... connection refused` → the target isn't up; `up -d api` first.
- Everything passes trivially → increase VUs/duration; a laptop handles small loads easily.

➡️ Next: [Lab 21 — Horizontal scaling](../21-scaling/)
