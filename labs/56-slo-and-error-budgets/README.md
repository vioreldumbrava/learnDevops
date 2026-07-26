# Lab 56 — SLOs and error-budget burn-rate alerting

**Maps to:** extra · **Milestone:** 4 — Operate & Automate · **SRE**

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Lab 12 gave you alerts: *"5xx above 5% for 5 minutes"*. Those alerts have a problem that only
shows up once someone is actually carrying the pager — they have **no idea how much reliability
you have left to spend**.

A static threshold pages at 03:00 for a six-minute blip that cost 0.02% of the month, and stays
completely silent through a 3% error rate that quietly eats the month's budget over a fortnight.
Both calls are wrong, and the first is worse: alert fatigue is the mechanism by which real pages
get ignored.

**Burn-rate alerting** asks a better question: *at the current rate, when do I run out of error
budget?* Urgency stops being a matter of taste and becomes arithmetic.

Three definitions, and you must be able to give them cleanly:

- **SLI** — the measurement. *"Fraction of requests that didn't 5xx."*
- **SLO** — the target on it. *"99.5%, over 30 days."*
- **Error budget** — the permitted failure, 0.5% ≈ **3h 36m** per 30 days. While budget remains
  you ship freely; when it's burning you spend the time on reliability instead.

**Burn rate** is the multiplier: 1× spends the budget exactly over the window; **14.4×** spends
the entire 30-day budget in about two days.

Everything you need is already running — this lab is the gap between the SLO answer in
[INTERVIEW_PREP.md §2](../../docs/INTERVIEW_PREP.md) and being able to demonstrate it.

## What you'll do

Write the SLI recording rules, replace two static alerts with six burn-rate alerts across fast
and slow windows, route page-vs-ticket in Alertmanager, then break the API and watch exactly
one alert fire.

---

## Steps

### 1. Bring up the stack with the SLO rules

```powershell
$dc = "docker","compose","-f","deploy/compose/compose.yaml"
& $dc -f deploy/compose/compose.dev.yaml -f deploy/compose/compose.observability.yaml up -d --build
```

Then **read** [`deploy/monitoring/prometheus/slo-rules.yml`](../../deploy/monitoring/prometheus/slo-rules.yml)
top to bottom before running anything. It is the lab.

Confirm the rules loaded: <http://localhost:9090/rules> — two groups, `dojo-slo-sli` and
`dojo-slo-burn`.

### 2. The SLIs — and why they're recording rules

```promql
job:slo_availability_error:ratio_rate5m
job:slo_latency_error:ratio_rate1h
```

Both are **error ratios** (fraction *bad*), not success ratios. That's deliberate: the alert
arithmetic below is `error_ratio > burn_rate × (1 - SLO)`, which only reads cleanly this way.

Four details worth being able to defend — and the first two are the same lesson twice, because
**an alert that cannot fire looks exactly like an alert with nothing to report**:

- **`or vector(0)`** around every 5xx numerator. If the service has served no 5xx at all, the
  selector `{status=~"5.."}` matches **no series**, `sum(rate(...))` is an *empty vector*, and
  empty ÷ anything is empty. Your dashboard reads "No data" and your alert can never fire —
  on a perfectly healthy service, which is exactly when you don't notice. This lab's rules
  were written without it and caught in verification; check it yourself by querying
  `sum(rate(dojo_http_requests_total{status=~"5.."}[5m]))` on a clean stack.
- **`clamp_min(..., 1e-9)`** in every denominator. With zero traffic the denominator is 0 and
  the ratio is `NaN`; comparisons against `NaN` are false, so the alert stays silent during the
  outage where nobody can reach you at all. (`ApiDown` covers that case — see
  [alerts.yml](../../deploy/monitoring/prometheus/alerts.yml).)
- **The latency SLI reads the `le="0.5"` bucket directly**, not `histogram_quantile`. No
  interpolation, no estimate. This is the argument for defining a latency SLO *on a bucket
  boundary* rather than on "p95".
- **`level:metric:operation` naming.** A shared convention means someone can read
  `job:slo_availability_error:ratio_rate5m` in an alert and know what it is without opening
  this file.

Compare the cost yourself: run the raw expression and the recorded one in
<http://localhost:9090> and look at the query duration. Six alerts and a dashboard evaluate
these constantly.

### 3. Multi-window, multi-burn-rate alerts

The table the alerts implement:

| Budget consumed | Long window | Short window | Burn rate | Severity |
|---|---|---|---|---|
| 2% | 1h | 5m | **14.4×** | page |
| 5% | 6h | 30m | **6×** | page |
| 10% | 3d | 6h | **1×** | ticket |

Two windows per alert, `and`-ed together, and this is the part people get wrong:

- The **long** window answers *"is this real?"* — it stops a 30-second blip from paging you.
- The **short** window answers *"is it still happening?"* — without it, a 6h window keeps the
  alert firing for hours after you fixed the problem, and you learn to ignore it.

Where does 14.4 come from? You want to be paged after 2% of a 30-day budget is consumed within
1 hour. `0.02 × (30 × 24) / 1 = 14.4`. Being able to derive that on a whiteboard is a strong
signal.

### 4. Route page vs ticket

Read [`alertmanager.yml`](../../deploy/monitoring/alertmanager/alertmanager.yml). Two receivers,
two matchers, and two **inhibit rules** — the second is the subtle one:

```yaml
- source_matchers: ['burn="fast"']
  target_matchers: ['burn="slow"']
  equal: ["slo"]
```

A fast burn always implies a slow burn, so both fire together during a real incident. Without
inhibition you get two notifications for one problem, which is precisely how alert fatigue
starts.

### 5. Break it and watch

```bash
bash scripts/chaos/kill-db.sh        # or: docker compose ... stop db
```

Then generate traffic so there's a ratio to compute — with no requests there is no error
*rate*:

```powershell
& $dc run --rm -e VUS=20 -e DURATION=5m load-test
```

Watch, in this order:

1. <http://localhost:9090/alerts> — `SLOAvailabilityFastBurn` goes **Pending** → **Firing**
   within about 5 minutes. `SLOAvailabilitySlowBurn` stays Inactive far longer: its 6h window
   dilutes a fresh incident. *That asymmetry is the design working.*
2. <http://localhost:9093> — the alert arrives on the `pager` route.
3. Grafana → **DevOps Dojo · SLO & error budget** — the burn-rate panel spikes past the 14.4
   threshold line and the budget gauge drops.

Heal it and watch the **5m** series recover in minutes while **6h** stays elevated for hours:

```bash
bash scripts/chaos/heal.sh
```

That lag is why the short window is in the `and` — it's what lets the alert resolve.

### 6. Read the policy

An SLO without a policy is a dashboard. [`docs/runbooks/error-budget-policy.md`](../../docs/runbooks/error-budget-policy.md)
is the decision rule: what you ship at 50% budget, at 25%, and at zero. Read it — "what does
your team actually *do* when the budget is spent?" is the follow-up question to every SLO answer
in an interview.

## How it works

- **A recording rule** is evaluated on Prometheus's schedule and stored as a new series, so an
  expensive expression is computed once instead of on every alert evaluation and dashboard
  refresh.
- **`for:`** requires the condition to hold continuously before firing — a *third* layer of
  noise suppression on top of the two windows.
- **Inhibition** is Alertmanager-side, not Prometheus-side: both alerts still fire, only the
  notification is suppressed. Prometheus's alert list still shows the truth.
- **The 30-day budget gauge** uses `increase(...[30d])` rather than a `rate` ratio, because a
  budget is about *how many* requests failed over the window, not the instantaneous rate.

## Exercise

1. **Add a third SLO** for the worker: a queue-depth or job-latency SLI from lab 09's metrics,
   with its own recording rules and one fast-burn alert. Choosing the SLI is the hard part —
   write down what a user would actually notice before writing any PromQL.
2. **Tune the windows to your traffic.** Run the burst profile from
   [lab 55](../55-postgres-operations/) (`db-load.js` with `BURST=1`) and check whether the fast
   window pages on a legitimate 60-second spike. If it does, you've reproduced the real
   trade-off: too sensitive is as broken as too slow. Change one number and justify it.

## Checkpoint

- ✅ `http://localhost:9090/rules` shows both rule groups healthy, and you can explain what
   `clamp_min` prevents.
- ✅ You can derive **14.4** on paper from "2% of the budget in 1 hour".
- ✅ With the database killed, **`SLOAvailabilityFastBurn` fires within ~5 minutes** while
   `SLOAvailabilitySlowBurn` stays Inactive; the alert lands on the `pager` route in
   Alertmanager and the Grafana budget gauge visibly drops.
- ✅ You can state the trade-off you accepted by deleting `HighErrorRate` — including the case
   where the static threshold would have been the better choice.

## Common failures

- Rules don't appear → the observability overlay must mount `slo-rules.yml` (it does, but check
  `docker compose ... config`), and `rule_files` in `prometheus.yml` must list it. Prometheus
  has no `--web.enable-lifecycle` here, so a config change needs a container restart.
- Every burn-rate series is empty → no traffic. The ratios need requests; run the load test.
- Alerts never fire even under load → `for:` hasn't elapsed, or the short window hasn't caught
  up. Check the raw expression in the Prometheus expression browser first, then the alert.
- The budget gauge is empty for the first 30 days → `increase(...[30d])` needs history.
  Shorten the window to `[1d]` while you're learning and say why you did.
- Alertmanager rejects the config → `matchers:` (list form) is v0.22+; older examples online
  use the deprecated `match:` map.

## Maps to

Lab [10](../10-monitoring/) (the metrics), lab [12](../12-tracing-and-alerting/) (the static
alerts this replaces), lab [34](../34-k8s-kube-prometheus-stack/) (the same rules as a
`PrometheusRule` CR in Kubernetes), lab [35](../35-incident-response/) (the incident these
alerts start), and [INTERVIEW_PREP.md §2](../../docs/INTERVIEW_PREP.md) — the SLO answer you can
now demonstrate instead of assert.

➡️ Back to the [curriculum](../../docs/CURRICULUM.md) · next drill:
[DRILLS.md](../../docs/DRILLS.md)
