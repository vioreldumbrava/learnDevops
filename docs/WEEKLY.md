# The job-first weekly plan

The 57 labs are a library. This is the plan for a **fresh learner** targeting a generalist
DevOps / Cloud role with roughly five hours a week. Week numbers are relative to the day you
start; missed work rolls forward instead of creating an artificial backlog.

The common core is intentionally finite. Applications begin while it is in progress, and CKA
preparation begins only after the Kubernetes foundation is demonstrated.

## The five-hour week

| Block | Time | Outcome |
|---|---:|---|
| Build A | 90 min | Run/explain the next lab or first half of a large lab. |
| Build B | 90 min | Complete its exercise and produce a commit, ADR, runbook or postmortem. |
| Recall | 60 min | The oldest due drill, an independent variation, or a blind incident. |
| Career | 60 min | CV/GitHub work, two targeted applications, or interview rehearsal. |

That is exactly **300 minutes**. A 180-minute or half-day lab consumes both build blocks; it
does not get squeezed into one evening. During final CKA preparation, use one 120-minute
simulator, one 90-minute build/remediation block, 30 minutes of review, and the 60-minute
career block.

## Common-core route (about 16–18 weeks)

The dashboard's **Common core** filter is the source of truth for the ordered list:

> `00 → Git basics from 38 → 01–08 → 37 → 54 (local) → 10 → 13 → 15 → 16 → 39 →`
> `40 Part A → 17 → 18 → 22 → 23 → 26 → 35 → 25 → 40 Part B`

Use these ranges as planning estimates, not deadlines:

| Relative weeks | Focus | Portfolio evidence |
|---|---|---|
| 1–2 | Setup, Git basics, images and containers (`00`, selected `38`, `01–03`) | CV outline, GitHub profile, first exercise commits. |
| 3–5 | Compose, migrations, restore and probes (`04–08`) | Foundation demo; begin two targeted applications per week. |
| 6–7 | Bash/Python glue, Linux diagnostics, monitoring (`37`, local `54`, `10`) | One automation script and one troubleshooting note. |
| 8–10 | Registry, secure CI, Terraform (`13`, `15`, `16`) | PR-to-image evidence, SBOM/attestation, reproducible plan/apply/destroy. |
| 11–12 | Remote state and AWS fundamentals (`39`, `40` Part A) | OIDC-based cloud workflow, budget/audit evidence. |
| 13–14 | Configuration and real HTTPS deployment (`17`, `18`) | Public deployment plus teardown record. |
| 15–16 | Kubernetes, Helm and external secrets (`22`, `23`, `26`) | Gateway API deployment and rollback. |
| 17–18 | Blind incident, EKS/GitOps capstone, `40` Part B (`35`, `25`, `40`) | Postmortem and end-to-end capstone demo. |

If a gate fails, spend the next build block repairing the specific gap. Do not add a new lab
to avoid repeating an uncomfortable skill.

## Applications start in week 3

- **Week 1:** write the CV outline and GitHub profile summary.
- **Week 2:** add an honest project note: this repository began as a scaffold; list the
  exercises, decisions and operational artifacts you personally produced.
- **Week 3 onward:** submit two targeted applications every week. Tailor the top third of the
  CV and record the role, date, result and skill signal.
- Use rejection and interview feedback to select a drill, not to expand the curriculum.

The capstone strengthens later applications; it is not permission to begin the search.

## Choose one branch after the common core

- **Platform / CKA:** `27 → 28 → 52 → 53 → 48`. Labs 29–34, 49 and 51 are role-dependent
  depth rather than booking prerequisites.
- **SRE:** `11 → 12 → 55 → 56`, with recurring lab-35 incidents.
- **Electives:** Nexus, Jenkins/GitLab variants, AKS, Cilium, the polyglot service, the
  operator and the LLMOps companion project.

Do **not** book the CKA yet. Pass lab 48's 10-task internal mock at 8/10 inside 45 minutes on
two different weeks, then book the exam four to six weeks out. Before the exam, pass one
120-minute full simulator using that simulator's published rule.

## The four-stage mastery loop

1. **Guided:** finish the lab checkpoint with the reference open.
2. **Independent:** within the next build block, solve a changed or partially broken variant;
   official documentation is allowed.
3. **Timed:** after roughly seven days, pass the published drill inside its target.
4. **Transfer:** after 21–42 days, solve a novel variant or explain the trade-off in a mock
   interview.

Only stage 3 marks a lab **drilled**. Add a compact note after every attempt:

```text
2026-08-12 | timed | 14m | fail | official docs only | forgot readinessProbe fields
```

The dashboard still prioritizes completed-but-undrilled work and then the stalest practice.
Attempt history deliberately remains in notes so building a richer tracker cannot become a
substitute for doing the labs.

## Learner gates

- **Foundation:** rebuild a minimal Compose stack, apply/rollback a migration, restore a row,
  and diagnose readiness without the repo answer files.
- **Delivery / cloud:** take a PR through secure CI and complete a repeatable Terraform
  apply/destroy using short-lived AWS credentials.
- **Kubernetes:** deploy and roll back through Helm + Gateway API, then resolve one unseen
  incident.
- **Portfolio-ready:** demonstrate the capstone, one runbook, one postmortem and two clean
  recorded mock-interview loops.

## Authoring freeze

Do not add subject-area labs until applications are underway. Update unsafe, broken or retired
instructions when found; otherwise, new content must be justified by a repeated signal from a
real job description or interview.
