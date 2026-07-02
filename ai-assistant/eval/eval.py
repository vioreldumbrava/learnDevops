"""RAG evaluation harness v2 (lab 08). Runs against a LIVE assistant (stack up,
docs ingested) and grades it per category, with a machine-readable report.

Case fields (dataset.jsonl, one JSON object per line):
    category        factual | paraphrase | refuse | injection | multiturn
    question        the user question
    history         optional prior turns [{role, content}, ...] (conversation memory)
    expect_source   optional: "x" -> x must appear among cited sources (retrieval hit@k);
                    ""  -> there must be NO sources (a correct refusal);
                    absent -> source check skipped
    expect_keyword  optional: must appear in the answer (lowercased substring)
    forbid_keyword  optional: must NOT appear in the answer (prompt-injection leak check)

    python eval/eval.py
    EVAL_API_URL=... EVAL_THRESHOLD=0.8 EVAL_REPORT_MD=report.md python eval/eval.py
"""
import json
import os
import sys
import urllib.request

API = os.getenv("EVAL_API_URL", "http://localhost:8000/api/chat")
DATA = os.path.join(os.path.dirname(__file__), "dataset.jsonl")
REPORT_JSON = os.path.join(os.path.dirname(__file__), "report.json")
THRESHOLD = float(os.getenv("EVAL_THRESHOLD", "0.8"))
REPORT_MD = os.getenv("EVAL_REPORT_MD", "")


def ask(question: str, history: list | None = None) -> dict:
    body = json.dumps(
        {"question": question, "stream": False, "history": history or []}
    ).encode()
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def grade(case: dict, res: dict) -> dict:
    answer = (res.get("answer") or "").lower()
    sources = " ".join(s.get("source") or "" for s in res.get("sources", []))

    kw = case.get("expect_keyword")
    ok_kw = (kw.lower() in answer) if kw else True

    if "expect_source" not in case:
        ok_src = True
        hit_at_k = None  # this case doesn't measure retrieval
    elif case["expect_source"] == "":
        ok_src = len(res.get("sources", [])) == 0
        hit_at_k = None
    else:
        ok_src = case["expect_source"] in sources
        hit_at_k = ok_src

    forbid = case.get("forbid_keyword")
    ok_forbid = (forbid.lower() not in answer) if forbid else True

    return {
        "category": case.get("category", "uncategorized"),
        "question": case["question"],
        "ok": ok_kw and ok_src and ok_forbid,
        "ok_kw": ok_kw,
        "ok_src": ok_src,
        "ok_forbid": ok_forbid,
        "hit_at_k": hit_at_k,
    }


def markdown(results: list[dict], rate: float, hits: int, hit_total: int) -> str:
    status = "✅" if rate >= THRESHOLD else "❌"
    lines = [
        f"## AI assistant eval — {sum(r['ok'] for r in results)}/{len(results)} "
        f"({rate:.0%}) vs threshold {THRESHOLD:.0%} {status}",
        "",
        "| Category | Passed | Rate |",
        "|----------|--------|------|",
    ]
    cats = sorted({r["category"] for r in results})
    for cat in cats:
        sub = [r for r in results if r["category"] == cat]
        n_ok = sum(r["ok"] for r in sub)
        lines.append(f"| {cat} | {n_ok}/{len(sub)} | {n_ok / len(sub):.0%} |")
    if hit_total:
        lines += ["", f"**Retrieval hit@k:** {hits}/{hit_total} ({hits / hit_total:.0%})"]
    failed = [r for r in results if not r["ok"]]
    if failed:
        lines += ["", "<details><summary>Failed cases</summary>", ""]
        for r in failed:
            why = ",".join(
                k for k, v in (("kw", r["ok_kw"]), ("src", r["ok_src"]), ("forbid", r["ok_forbid"])) if not v
            )
            lines.append(f"- `{r['category']}` {r['question'][:80]}  — failed: {why}")
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def main() -> None:
    cases = [json.loads(line) for line in open(DATA, encoding="utf-8") if line.strip()]

    results = []
    for c in cases:
        try:
            res = ask(c["question"], c.get("history"))
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  request error: {e}  | {c['question'][:50]}")
            results.append(
                {"category": c.get("category", "uncategorized"), "question": c["question"],
                 "ok": False, "ok_kw": False, "ok_src": False, "ok_forbid": False, "hit_at_k": None}
            )
            continue
        r = grade(c, res)
        results.append(r)
        flags = f"kw={r['ok_kw']} src={r['ok_src']} forbid={r['ok_forbid']}"
        print(f"{'PASS' if r['ok'] else 'FAIL'}  [{r['category']:<11}] {flags}  | {c['question'][:52]}")

    rate = sum(r["ok"] for r in results) / len(results) if results else 0.0
    retrieval = [r["hit_at_k"] for r in results if r["hit_at_k"] is not None]
    hits, hit_total = sum(retrieval), len(retrieval)

    print(f"\nscore: {sum(r['ok'] for r in results)}/{len(results)} = {rate:.0%}  "
          f"(threshold {THRESHOLD:.0%})")
    if hit_total:
        print(f"retrieval hit@k: {hits}/{hit_total} = {hits / hit_total:.0%}")

    report = {
        "score": rate,
        "threshold": THRESHOLD,
        "passed": rate >= THRESHOLD,
        "retrieval_hit_at_k": (hits / hit_total) if hit_total else None,
        "categories": {
            cat: {
                "passed": sum(r["ok"] for r in results if r["category"] == cat),
                "total": sum(1 for r in results if r["category"] == cat),
            }
            for cat in sorted({r["category"] for r in results})
        },
        "cases": results,
    }
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md = markdown(results, rate, hits, hit_total)
    if REPORT_MD:
        with open(REPORT_MD, "w", encoding="utf-8") as f:
            f.write(md)
    else:
        print("\n" + md)

    sys.exit(0 if rate >= THRESHOLD else 1)


if __name__ == "__main__":
    main()
