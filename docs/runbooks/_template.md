# Runbook — <symptom, as the alert/user reports it>

> A runbook is written for the *symptom*, not the cause — the on-call engineer doesn't know
> the cause yet. Keep it executable at 3am: exact commands, no prose that isn't a decision.

**Trigger:** <the alert rule / user report that lands you here>
**Impact:** <who/what is affected while this is true>
**Severity guide:** <when is this a page vs. a ticket>
**Dashboards:** <Grafana links / panels to open first>

## Quick diagnosis (first 5 minutes)

1. <command> — <what each possible output tells you>
2. <command> — …
3. Decision point: if <X> go to [Mitigation A], if <Y> go to [Mitigation B].

## Mitigation

### A — <most common cause>
<commands to stop the bleeding — mitigation first, root cause later>

### B — <second cause>
<commands>

## Known causes seen before

| Signature | Cause | Reference |
|-----------|-------|-----------|
| <observation> | <cause> | <drill/lab/postmortem link> |

## After the incident

- Verify: <command that proves recovery>
- Write the postmortem: [postmortem-template.md](../postmortem-template.md)
- If this runbook was wrong or incomplete — fixing it *is* part of closing the incident.
