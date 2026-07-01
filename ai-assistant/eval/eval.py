"""Tiny RAG evaluation harness. Runs against a LIVE assistant (the full stack must
be up and the docs ingested). Checks retrieval (expected source) and answer quality
(expected keyword), including a grounding case that must be refused.

    python eval/eval.py            # against http://localhost:8000
    EVAL_API_URL=... EVAL_THRESHOLD=0.8 python eval/eval.py
"""
import json
import os
import sys
import urllib.request

API = os.getenv("EVAL_API_URL", "http://localhost:8000/api/chat")
DATA = os.path.join(os.path.dirname(__file__), "dataset.jsonl")
THRESHOLD = float(os.getenv("EVAL_THRESHOLD", "0.8"))


def ask(question: str) -> dict:
    body = json.dumps({"question": question, "stream": False}).encode()
    req = urllib.request.Request(
        API, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> None:
    cases = [
        json.loads(line)
        for line in open(DATA, encoding="utf-8")
        if line.strip()
    ]
    passed = 0
    for c in cases:
        try:
            res = ask(c["question"])
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  request error: {e}  | {c['question'][:50]}")
            continue
        answer = (res.get("answer") or "").lower()
        sources = " ".join(s.get("source", "") for s in res.get("sources", []))
        ok_kw = (c["expect_keyword"].lower() in answer) if c["expect_keyword"] else True
        ok_src = (
            (c["expect_source"] in sources)
            if c["expect_source"]
            else len(res.get("sources", [])) == 0
        )
        ok = ok_kw and ok_src
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  kw={ok_kw} src={ok_src}  | {c['question'][:56]}")

    rate = passed / len(cases) if cases else 0.0
    print(f"\nscore: {passed}/{len(cases)} = {rate:.0%}  (threshold {THRESHOLD:.0%})")
    sys.exit(0 if rate >= THRESHOLD else 1)


if __name__ == "__main__":
    main()
