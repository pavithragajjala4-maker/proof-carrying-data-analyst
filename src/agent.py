"""
agent.py - question -> LLM writes pandas code -> run it -> answer + proof.

Usage (from the project root):
    python src/agent.py "How many unique customers placed at least one order?"

Design rule: the LLM NEVER states a number itself. Every number comes from
executing the code it wrote, and that code is saved to outputs/ as the proof.
"""
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from executor import ROOT, run_script, save_script

load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
MAX_ATTEMPTS = 3

SYSTEM = """You are a careful data analyst. You answer questions about CSV files
by writing Python (pandas) code. You never compute or guess numbers yourself.

RULES
1. Reply with EITHER one ```python code block OR a single line starting with
   CANNOT_DETERMINE: followed by the specific reason.
2. The code must be standalone: import pandas, load the CSVs with relative
   paths like pd.read_csv("data/orders.csv"), and store the final answer in a
   variable named `result` (a number, string, or small list/dict).
3. Also create a list named `assumptions` with short strings describing every
   data-cleaning decision (duplicates removed, rows excluded, date format
   assumed, currency handled, etc.).
4. Real data is messy. Before answering, consider: duplicate rows, missing
   values, mixed currencies/units, mixed or ambiguous date formats, and
   records that don't join across tables. Handle them explicitly.
5. Use CANNOT_DETERMINE when the data cannot support a reliable answer: the
   needed column/table does not exist, the question assumes something false
   (e.g. an ID that does not exist), or a required conversion (such as an
   exchange rate) is missing. A justified refusal is better than a confident
   wrong answer. Name the exact missing column or conflict.
6. Do not hardcode numbers you did not compute from the data. Do not read any
   file outside data/.
"""


# ----------------------------------------------------------------- LLM call
def call_llm(system: str, messages: list) -> str:
    import anthropic  # imported here so the rest works without the package
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    resp = client.messages.create(
        model=MODEL, max_tokens=2000, temperature=0,
        system=system, messages=messages,
    )
    return "".join(b.text for b in resp.content if b.type == "text")


# ------------------------------------------------------------------ helpers
def schema_summary() -> str:
    """Describe every CSV in data/: size, columns, nulls and a few sample rows."""
    parts = []
    for csv in sorted(DATA_DIR.glob("*.csv")):
        df = pd.read_csv(csv)
        cols = ", ".join(f"{c} ({df[c].dtype}, {int(df[c].isna().sum())} nulls)" for c in df.columns)
        sample = df.sample(min(5, len(df)), random_state=0).to_string(index=False)
        parts.append(f"FILE data/{csv.name}  ({len(df)} rows)\nColumns: {cols}\nSample rows:\n{sample}")
    return "\n\n".join(parts)


def extract_code(reply: str):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", reply, re.DOTALL)
    return m.group(1).strip() if m else None


def refusal_reason(reply: str):
    for line in reply.strip().splitlines():
        if line.strip().startswith("CANNOT_DETERMINE"):
            return line.split(":", 1)[1].strip() if ":" in line else "No reason given"
    return None


# -------------------------------------------------------------------- agent
def answer(question: str, qid="adhoc", llm=call_llm) -> dict:
    OUT_DIR.mkdir(exist_ok=True)
    messages = [{"role": "user",
                 "content": f"TABLES\n{schema_summary()}\n\nQUESTION: {question}"}]
    record = {"id": qid, "question": question, "status": "error", "result": None,
              "reason": "", "assumptions": [], "code_file": None, "attempts": 0}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        record["attempts"] = attempt
        reply = llm(SYSTEM, messages)

        reason = refusal_reason(reply)
        if reason:
            record.update(status="refused", reason=reason)
            break

        code = extract_code(reply)
        if not code:
            messages += [{"role": "assistant", "content": reply},
                         {"role": "user", "content": "Reply with ONE ```python block or a CANNOT_DETERMINE line."}]
            continue

        script = OUT_DIR / f"q{qid}.py"
        save_script(code, script)
        run = run_script(script)
        if run["ok"]:
            record.update(status="answered", result=run["result"],
                          assumptions=run["assumptions"],
                          code_file=str(script.relative_to(ROOT)))
            break

        record["reason"] = run["error"]
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"That code failed:\n{run['error']}\nReturn the full corrected code."}]

    (OUT_DIR / f"q{qid}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def show(rec: dict) -> None:
    print(f"\nQuestion : {rec['question']}")
    print(f"Status   : {rec['status']}  (attempts: {rec['attempts']})")
    if rec["status"] == "answered":
        print(f"Answer   : {rec['result']}")
        print(f"Proof    : {rec['code_file']}")
        for a in rec["assumptions"]:
            print(f"  - {a}")
    else:
        print(f"Reason   : {rec['reason']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Usage: python src/agent.py "your question"')
    show(answer(" ".join(sys.argv[1:])))
