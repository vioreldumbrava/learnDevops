# The weekly loop (and the calendar)

Fifty-seven labs is a library, not a plan. This file is the plan: what happens in a normal week,
and the fixed dates that stop preparation from expanding to fill all available time.

Target role: **generalist DevOps / Cloud engineer**. Cert order: **CKA first, AWS SAA second**
([INTERVIEW_PREP.md §6](INTERVIEW_PREP.md#6-close-the-gaps-study-plan)).

---

## The repeating week

Roughly 5 hours. Every slot has an artifact — a drill passed, a lab finished, a postmortem
written, an application sent. A slot with no artifact didn't happen.

| Day | Slot | What |
|-----|------|------|
| **Mon** | 45 min | One closed-book drill from [DRILLS.md](DRILLS.md). The dashboard's **Drill next** panel picks it. |
| **Tue** | 90 min | New content — the next unfinished lab. |
| **Wed** | 45 min | Closed-book drill. |
| **Thu** | 45 min | Closed-book drill. |
| **Sat** | 40 min | The mock-interview loop ([INTERVIEW_PREP.md §10](INTERVIEW_PREP.md#10-mock-interview-protocol-run-it-weekly)) — quick-fire, blind incident, design question. |
| **Sun** | 60 min | Applications and CKA timed practice. |

**Three drills a week, one new lab.** That ratio is deliberate and it's the opposite of how the
repo was being used until now. Adding a lab feels like progress; re-drilling lab 04 for the
third time feels like standing still. The interview measures the second one.

### Picking the drill

Don't choose. The dashboard's *Drill next* panel sorts by: completed-but-never-drilled first,
then longest since practised. Take the top item. If it isn't in [DRILLS.md](DRILLS.md) yet,
write the drill for it before you run it — deciding "what would prove I can do this from
scratch?" is itself half the learning.

### When a drill fails

Leave the lab **undrilled**. Write one line in the card's notes about *what* you couldn't
produce — not "failed lab 22" but "couldn't remember the probe field names". Re-run it the same
week. Two consecutive fails on the same lab means re-read the lab, then drill again.

---

## The calendar

Dates, not intentions. Written 2026-07-26.

| When | What | Done |
|------|------|------|
| **Mon 2026-07-27 → Sun 2026-08-02** | The learning-system work: dashboard tracker, [DRILLS.md](DRILLS.md), [TOOLBOX.md](TOOLBOX.md) (install `kind` + `helm` in WSL). Start the weekly loop immediately — don't wait for the setup to be perfect. | ⬜ |
| **by Fri 2026-07-31** | **Book the CKA** for **Mon 2026-09-14**. The booking is the deliverable. | ⬜ |
| **Mon 2026-08-03 → Fri 2026-08-14** | Labs **54** (Linux server ops) → **55** (Postgres under load) → **56** (SLOs & burn-rate alerting), in that order. Drills continue Mon/Wed/Thu throughout. | ⬜ |
| **Fri 2026-08-14** | 🔒 **Authoring freeze.** No new labs until the CKA is passed *and* 10 applications are out. Milestone 5 (43–47) gets *done*, not extended. | ⬜ |
| **Mon 2026-08-17** | 🚀 **Start applying.** Regardless of how ready it feels. | ⬜ |
| **Mon 2026-08-17 → Sun 2026-09-13** | Weekly loop unchanged, *while* interviewing. Sunday becomes applications + CKA timed practice (lab 48's mock, repeated). | ⬜ |
| **Mon 2026-09-14** | **CKA.** | ⬜ |
| **after** | AWS SAA. Resume authoring if — and only if — a specific interview exposed a specific gap. | ⬜ |

### Why the freeze exists

The three commits before this plan added labs 51, 52 and 53. All three are good labs. None of
them moved you closer to an offer, because the constraint was never coverage — it was recall and
a start date. Breadth is the comfortable work; it always feels productive and it never ends.

### Why 2026-08-17 is a hard date

The stated exit criterion is two consecutive clean mock loops. Keep that as the *target* — but
not as the gate. A job search runs for weeks in parallel with everything else, the first few
interviews are themselves the best diagnostic you'll get, and no candidate has ever felt ready.
Apply on the 17th with whatever state you're in.

### Why CKA before AWS SAA, for a generalist role

Arguably SAA is the stronger filter for generalist cloud postings. CKA still goes first here for
one reason: labs 22–34 and 48–53 are already written, so the exam is nearly free from where you
stand — and it's the harder credential to fake, which is exactly why it filters well.

---

## Tracking it

The dashboard is the tracker; this file is the schedule. The two columns that matter are
**drilled** and **last practised** — not "completed". See
[DRILLS.md](DRILLS.md#how-to-use-this-file).

A healthy month looks like: 4 new labs, 12 drills, 4 mock loops, and the stalest lab in the
dashboard less than 6 weeks old.
