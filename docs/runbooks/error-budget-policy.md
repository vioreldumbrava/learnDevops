# Runbook — error-budget policy

**Applies to:** the Dojo API · **Owner:** you · **Related:** [api-down](api-down.md),
[high-latency](high-latency.md) · **Lab:** [56](../../labs/56-slo-and-error-budgets/)

An SLO with no policy attached is a dashboard. The policy is what makes it a decision rule —
and "what does your team do when the budget is spent?" is the follow-up question after every
SLO answer in an interview.

## The SLO

> **99.5% of API requests succeed and complete within 500 ms, measured over a rolling 30 days.**

| | |
|---|---|
| **SLIs** | availability = `1 - (5xx / all)` · latency = fraction under 500 ms |
| **Target** | 99.5% each |
| **Error budget** | 0.5% of 30 days ≈ **3h 36m** of bad requests |
| **Measured by** | `job:slo_*` recording rules in [slo-rules.yml](../../deploy/monitoring/prometheus/slo-rules.yml) |
| **Seen at** | Grafana → *DevOps Dojo · SLO & error budget* (`dojo-slo`) |

The SLO is deliberately **not** 100%. A target of 100% means every change is a risk you can
never justify, so the real decision gets made by whoever argues hardest. 99.5% turns it into
arithmetic.

## What each alert means, and what you do

| Alert | Burn rate | Budget gone in | Action |
|---|---|---|---|
| `SLOAvailabilityFastBurn` / `SLOLatencyFastBurn` | >14.4× | ~2 days | **Page.** Treat as an incident: work [api-down](api-down.md) or [high-latency](high-latency.md). Roll back first, diagnose second. |
| `SLOAvailabilitySlowBurn` / `SLOLatencySlowBurn` | >6× | ~5 days | **Page**, but with a moment to think. Usually a bad release still ramping — check what deployed in the last 6h. |
| `SLOAvailabilityBudgetDegrading` | >1× | end of window | **Ticket.** Not an outage. Something is chronically wrong; schedule it. |
| `SLOErrorBudgetExhausted` | — | already gone | **Freeze.** See below. |

## The policy

**Budget above 50%** — ship freely. Deploy on Fridays if you want to; that's what the budget
is for.

**Budget 25–50%** — ship, but not blind. Canary risky changes (lab
[32](../../labs/32-k8s-argo-rollouts/)), and no schema migration without a tested rollback.

**Budget under 25%** — feature work continues, reliability work gets priority in the same
sprint. Every deploy is a canary.

**Budget exhausted (≤ 0)** — **feature releases pause.** Only these ship:
1. fixes for whatever is burning the budget,
2. reliability work identified in postmortems,
3. security patches.

The freeze lifts when the rolling 30-day budget climbs back above 25% — not when someone
declares the incident over. That's the whole point of a rolling window: recovery is measured,
not announced.

## The honest caveats

Say these unprompted; they're what separates having read about SLOs from having run them.

- **Low traffic breaks ratios.** At 3 requests/minute, one 500 is a 33% error rate. Burn-rate
  alerting needs volume; below it, use `ApiDown` and a static threshold and say so.
- **The SLI must measure what users feel.** Ours is measured server-side, so it misses DNS,
  TLS, CDN and the client's network entirely. A blackbox probe from outside is closer to the
  truth — which is why lab 10's blackbox exporter is still scraping.
- **A budget freeze is a social contract, not a technical control.** If nobody honours it, the
  SLO is decoration. Agreeing it *before* the budget is spent is the only version that works.
- **One 30-day window hides a bad week.** A steady 0.4% is fine; 0.02% for 25 days and 4% for
  five is the same number and a much worse month. That's what the multi-window alerts catch
  while the 30-day gauge stays green.

## Verifying the policy still works

Quarterly, or after any change to the rules — break it on purpose and watch:

```powershell
# from the repo root, with the observability overlay up
bash scripts/chaos/kill-db.sh          # or stop the api container
# Prometheus → Alerts: SLOAvailabilityFastBurn goes Pending → Firing within ~5 min
# Alertmanager :9093 → the alert is on the `pager` route, and slow-burn is inhibited
bash scripts/chaos/heal.sh
```

If the alert doesn't fire, the rules are decoration too. An untested alert is worse than no
alert, because you're counting on it.
