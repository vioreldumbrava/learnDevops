# AI Lab 08 — Evaluation v2 & prompt versioning

## Concept

Five test cases is a smoke test, not an eval. A real eval is a **categorized dataset** with
adversarial cases, a **retrieval metric** separate from answer quality, **reports** you can
read in CI, and the discipline to **A/B a change before shipping it**. This lab turns lab 04's
harness into the LLM equivalent of a regression suite that gates a deploy — and uses it to
change the system prompt *safely*.

## What you'll do

Run the expanded eval, read the per-category report, then A/B two prompt versions and let the
numbers pick the winner.

## Steps — the categorized eval

```powershell
# Stack up + ingested (labs 01–02). From ai-assistant/:
python eval/eval.py
```

Output now breaks down by **category** — `factual`, `paraphrase`, `refuse`, `injection`,
`multiturn` — plus a **retrieval hit@k** line and a written `eval/report.json`. The injection
cases assert the system prompt does *not* leak; the multiturn cases send prior `history`.

## Steps — A/B a prompt change

Two system prompts live in [app/prompts/](../../api/app/prompts/): `v1.txt` (the original) and
`v2.txt` (stricter citations + explicit injection resistance). Compare them on the same dataset:

```powershell
$env:PROMPT_VERSION="v1"; docker compose up -d rag-api; python eval/eval.py
$env:PROMPT_VERSION="v2"; docker compose up -d rag-api; python eval/eval.py
```

Keep the version that scores better (especially on `injection` and `refuse`). That decision —
data, not vibes — is the whole point.

## Steps — reports in CI

The nightly workflow
([ai-assistant-eval.yml](../../../.github/workflows/ai-assistant-eval.yml)) writes the
markdown table to the run's **job summary** and uploads `report.json` as an artifact. Trigger it
by hand with a prompt version to run the A/B in CI:

```powershell
gh workflow run "ai-assistant nightly eval" -f prompt_version=v2
```

## How it works

- [eval/dataset.jsonl](../../eval/dataset.jsonl) — ~25 cases, each with a `category`. New
  fields: `forbid_keyword` (a phrase that must NOT appear — the injection leak check) and
  optional `history` (multi-turn). `expect_source: ""` still means "must refuse (no sources)".
- [eval/eval.py](../../eval/eval.py) — sends `history` when present, checks `forbid_keyword`,
  reports **retrieval hit@k** (expected source within the returned `TOP_K`) *separately* from
  answer quality, computes per-category pass rates, and writes `report.json` + a markdown
  table (`EVAL_REPORT_MD`). Overall threshold still gates the exit code; per-category rates are
  report-only — a 1b CPU model legitimately fails some paraphrase cases, and saying so honestly
  is itself an interview point.
- **Prompt versioning** — [app/rag.py](../../api/app/rag.py) loads
  `prompts/{PROMPT_VERSION}.txt`, and the active version is exposed in
  `dojo_ai_app_info{prompt_version}` and every request's log line — so when a metric moves you
  know which prompt produced it. A prompt is config; a config change gets tested like code.

## Exercise

1. Add 3 `injection` cases of your own (e.g. instructions hidden inside a code block) and see
   whether `v1` or `v2` resists them.
2. Add a category the dataset lacks (e.g. `numeric` — questions with a specific number as the
   answer) and decide how to score it.
3. Wire a *gate*: make the workflow fail if the `refuse` OR `injection` category drops below
   100% (safety regressions should block, even when overall quality is lenient).

## Checkpoint

- ✅ `eval.py` prints per-category pass rates and a retrieval hit@k line, and writes `report.json`.
- ✅ An injection case fails if the system prompt leaks (try it with a deliberately chatty prompt).
- ✅ Running v1 vs v2 produces two comparable scores and you can say which wins and why.
- ✅ The nightly workflow shows the table in its job summary and uploads the artifact.

## Common failures

- All `injection` cases "pass" trivially → the model refused for an unrelated reason; confirm
  the `forbid_keyword` is actually a distinctive phrase from the system prompt.
- `multiturn` cases fail → `HISTORY_TURNS` is 0, or the harness isn't sending `history` (it
  only sends it for cases that include the field).
- v1 and v2 score identically → the prompt change is too subtle for a 1b model to reflect; try
  a bigger model locally, or a starker prompt difference.
- hit@k is high but answers are wrong → retrieval works, generation doesn't; that separation is
  exactly why the two metrics are reported apart.
- `report.json` not created → eval crashed before finishing; check the first `request error`
  line (stack down or not ingested).

➡️ You've completed the LLMOps depth track. Bring the talk track home in
[docs/INTERVIEW_PREP.md](../../../docs/INTERVIEW_PREP.md) (the LLMOps Q&A section).
