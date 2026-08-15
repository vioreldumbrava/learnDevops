# Postmortem — API unreachable after Service edit (selector typo)

> Worked example from lab 35, drill 4 — use it as the bar for your own writeups.

| | |
|---|---|
| **Date** | 2026-07-01 |
| **Duration** | 14:02–14:23 UTC (21 min) |
| **Severity** | SEV1 — all `/api/*` traffic failing |
| **Author** | Viorel |
| **Status** | reviewed |

## Summary

A manual `kubectl patch` intended to adjust the `api` Service changed its selector from
`app: api` to `app: apy`. The Service immediately matched zero pods, so every `/api/*` request
through the Gateway returned 502/504 while all pods stayed Running and Ready. Diagnosis was
delayed ~10 minutes because pod health looked perfect; checking Service endpoints identified
the mismatch, and re-patching the selector restored traffic instantly.

## Impact

- Dashboard loaded (static frontend) but all data reads/writes failed for 21 minutes.
- No data loss — requests failed before reaching the API.

## Timeline (UTC)

| Time | What happened / what we did |
|------|------------------------------|
| 14:00 | Manual `kubectl patch svc api` applied (selector typo introduced) |
| 14:02 | Blackbox probe on `/api/steps` fails; dashboard shows fetch errors |
| 14:04 | `get pods`: everything Running/Ready — pod-level causes ruled *in* by mistake; ~8 min spent re-reading logs that showed no errors (no requests were arriving) |
| 14:12 | Stepped back to the traffic path: `get endpoints api` → `<none>` |
| 14:14 | Compared Service selector to pod labels → `apy` vs `api` |
| 14:15 | Selector re-patched to `app: api`; endpoints repopulated |
| 14:16 | `/api/steps` serving again |
| 14:23 | Error rate at baseline for 5 min — incident closed |

## Root cause

A live object was edited by hand, so there was no review, no diff, and no reconciliation to
catch or revert the typo. The system tolerated the bad state indefinitely because a Service
with an empty selector match is *valid* — nothing was "unhealthy" for pod-level checks to
flag, and no alert watched Service endpoint counts.

## What went well / what went poorly

- 👍 The diagnosis loop eventually worked; "no app logs" was correctly reinterpreted as "no
  traffic arriving" rather than "app fine".
- 👍 Fix was instant and needed no restarts.
- 👎 8 minutes lost staring at healthy pods — endpoints should be step 2, not step 5, when
  pods are green but traffic fails (runbook updated).
- 👎 Nothing alerted on "Service has zero endpoints".

## Action items

| # | Action | Type | Owner | Due |
|---|--------|------|-------|-----|
| 1 | Manage this Service via GitOps (lab 25) so manual drift is auto-reverted | prevent | Viorel | done (capstone) |
| 2 | Alert: `kube_endpoint_address_available == 0` for services with running backends (lab 34 metrics) | detect | Viorel | next lab session |
| 3 | Reorder [runbooks/api-down.md](../runbooks/api-down.md): endpoints check moved into the first-5-minutes block | mitigate | Viorel | done |
