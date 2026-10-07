"""
verifier.py - the "proof-carrying" check.

For every answered question it re-runs the saved script outputs/q<id>.py in a FRESH
Python process (no memory of the agent), and confirms it prints the same number the
agent reported. If the code fails or gives a different number, that answer is not
verified.

Usage (from the project root):
    python src/verifier.py
"""
import json

from executor import ROOT, run_script

OUT = ROOT / "outputs"


def same(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) <= 0.01
    except (TypeError, ValueError):
        return a == b


def verify_all() -> list:
    records = []
    for f in sorted(OUT.glob("q*.json"), key=lambda p: (len(p.stem), p.stem)):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("status") != "answered":
            continue  # refusals have no number to verify
        run = run_script(ROOT / rec["code_file"])
        if not run["ok"]:
            verdict, detail = "FAIL", f"code did not run: {run['error'][:100]}"
        elif same(run["result"], rec["result"]):
            verdict, detail = "PASS", f"re-run gave {run['result']}"
        else:
            verdict, detail = "FAIL", f"agent said {rec['result']}, re-run gave {run['result']}"
        records.append({"id": rec["id"], "verdict": verdict, "detail": detail,
                        "code_file": rec["code_file"]})
        print(f"Q{rec['id']:>6}  {verdict}  {detail}   ({rec['code_file']})")

    passed = sum(r["verdict"] == "PASS" for r in records)
    print(f"\nVerified {passed}/{len(records)} answered questions by re-running their code.")
    (OUT / "verification_report.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    return records


if __name__ == "__main__":
    verify_all()
