# Postmortem — <short incident title>

> **Blameless.** The question is never "who did it" but "what allowed it". Write it within
> 48h while memory is fresh. A worked example lives in [postmortems/](postmortems/).

| | |
|---|---|
| **Date** | YYYY-MM-DD |
| **Duration** | detection → resolution, e.g. 14:02–14:41 (39 min) |
| **Severity** | SEV1 (full outage) / SEV2 (degraded) / SEV3 (no user impact) |
| **Author** | |
| **Status** | draft / reviewed / actions-done |

## Summary (3–4 sentences)

What broke, who/what was affected, how it was fixed. Written for someone who wasn't there.

## Impact

- User-visible effect and for how long.
- Anything lost (data, jobs, SLO budget).

## Timeline (all times UTC)

| Time | What happened / what we did |
|------|------------------------------|
| 14:02 | Alert X fired / user report |
| 14:05 | Started diagnosis — found … |
| … | mitigation applied |
| 14:41 | Verified recovery |

## Root cause

The chain, not just the trigger: what changed → why the system couldn't absorb it → why
detection took as long as it did. "Human error" is never a root cause — ask why the system
let a human error propagate.

## What went well / what went poorly

- 👍 …
- 👎 …

## Action items

| # | Action | Type | Owner | Due |
|---|--------|------|-------|-----|
| 1 | | prevent (make it impossible) | | |
| 2 | | detect (alert sooner) | | |
| 3 | | mitigate (recover faster / runbook fix) | | |

Every incident should produce at least one *detect* item — you rarely get to choose your next
failure, but you always get to choose how fast you see it.
