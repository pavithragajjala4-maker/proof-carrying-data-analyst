"""
run_tests.py - runs every question in questions/test_set.json through the agent
and grades it against the expected answer.

Usage (from the project root):
    python src/run_tests.py            # all questions
    python src/run_tests.py 1 6 12     # only these question ids

Grading rules
  normal / tricky : status must be "answered" and the number must match `expected`
                    (within `tolerance`).
  refuse          : status must be "refused". Answering is a FAIL (the answer is
                    printed so you can review it). Questions whose expected_behavior
                    contains "caveat" (mixed currency) also pass if the agent returns
                    separate USD and EUR figures without converting.
"""
import json
import sys
import time

import agent
from executor import ROOT

DELAY_SECONDS = 2  # small pause between questions to be kind to free-tier rate limits


def to_number(x):
    if isinstance(x, (list, tuple)) and len(x) == 1:
        x = x[0]
    if isinstance(x, dict) and len(x) == 1:
        x = next(iter(x.values()))
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def grade(item: dict, rec: dict):
    status = rec["status"]
    if item["type"] == "refuse":
        if status == "refused":
            return True, "correctly refused"
        if status == "answered" and "caveat" in item["expected_behavior"].lower():
            res = rec["result"]
            if isinstance(res, dict) and {"usd", "eur"} <= {str(k).lower() for k in res}:
                return True, "gave separate USD/EUR totals without converting"
        extra = f" reason={rec['reason'][:150]}" if status == "error" else ""
        return False, f"should have refused, but status={status}, result={rec['result']}{extra}"

    if status != "answered":
        return False, f"status={status}: {rec['reason'][:120]}"
    num = to_number(rec["result"])
    if num is None:
        return False, f"result is not a single number: {rec['result']}"
    if abs(num - item["expected"]) <= max(item["tolerance"], 1e-9):
        return True, "correct"
    return False, f"got {rec['result']}, expected {item['expected']}"


def run_all(llm=agent.call_llm, only=None, delay=DELAY_SECONDS):
    items = json.loads((ROOT / "questions" / "test_set.json").read_text(encoding="utf-8"))
    if only:
        items = [i for i in items if i["id"] in only]

    rows = []
    for item in items:
        try:
            rec = agent.answer(item["question"], qid=item["id"], llm=llm)
        except Exception as e:  # e.g. network / API problem
            rec = {"status": "error", "result": None, "reason": str(e), "attempts": 0}
        ok, why = grade(item, rec)
        rows.append({"id": item["id"], "type": item["type"], "question": item["question"],
                     "passed": ok, "detail": why, "status": rec["status"],
                     "result": rec["result"], "attempts": rec["attempts"]})
        print(f"Q{item['id']:>2} [{item['type']:<6}] {'PASS' if ok else 'FAIL'}  {why}")
        time.sleep(delay)

    print("\n=== SUMMARY ===")
    for t in ("normal", "tricky", "refuse"):
        sub = [r for r in rows if r["type"] == t]
        if sub:
            print(f"{t:<7}: {sum(r['passed'] for r in sub)}/{len(sub)}")
    total = sum(r["passed"] for r in rows)
    print(f"OVERALL: {total}/{len(rows)} ({100 * total / max(len(rows), 1):.0f}%)")

    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs" / "test_report.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("Saved outputs/test_report.json. Next: python src/verifier.py")
    return rows


if __name__ == "__main__":
    ids = {int(a) for a in sys.argv[1:] if a.isdigit()} or None
    run_all(only=ids)
