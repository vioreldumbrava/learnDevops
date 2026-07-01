# AI Lab 04 — Evaluation

## Concept

"It looked good when I tried it" doesn't scale. **Evaluation** turns LLM quality into a
repeatable, measurable score against a fixed dataset — so you can compare models, prompts, and
retrieval settings objectively and catch regressions. It's the LLM equivalent of a test suite,
and it's a skill interviewers specifically look for.

## What you'll do

Run the eval harness against the live assistant and read the score.

## Steps

```powershell
# Stack must be up + docs ingested (labs 01–02). From ai-assistant/:
python eval/eval.py
# or point at a remote instance:  EVAL_API_URL=http://host:8000/api/chat python eval/eval.py
```

Each case checks two things: **retrieval** (did the expected source come back?) and **answer
quality** (does the answer contain the expected keyword?). One case is a **must-refuse** check —
an out-of-scope question that should be declined, guarding against hallucination regressions.

## How it works

[eval/dataset.jsonl](../../eval/dataset.jsonl) holds question → expected-source + expected-keyword
rows. [eval/eval.py](../../eval/eval.py) calls `/api/chat` for each, scores pass/fail, prints a
rate, and **exits non-zero** below the threshold — so it can gate a release. It's not in the fast
PR CI (it needs a running model), so it runs on a **schedule** instead:
[ai-assistant-eval.yml](../../../.github/workflows/ai-assistant-eval.yml) spins up the stack with
a tiny CPU model (`llama3.2:1b`) nightly — move it to a self-hosted/GPU runner for a real model.

## Exercise

Grow the dataset to 15–20 cases (include tricky ones and more negatives), then A/B two setups:
run the eval with `llama3.2:3b` vs `llama3.2:1b`, or `TOP_K=2` vs `TOP_K=6`, and record which
scores better. That comparison *is* the LLMOps job.

## Checkpoint

- ✅ `eval.py` prints per-case PASS/FAIL and an overall score.
- ✅ The out-of-scope case passes by being **refused**.
- ✅ You changed a variable (model or TOP_K) and saw the score move.

➡️ Next: [AI Lab 05 — Containerize & deploy](../05-deploy/)
