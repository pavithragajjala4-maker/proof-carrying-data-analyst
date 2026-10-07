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
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from executor import ROOT, run_script, save_script
from profiler import profile_tables

load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
# PROVIDER: "groq" (free key), "gemini" (free key), "ollama" (free, runs locally),
# or "anthropic" (paid). Set it in your .env file.
PROVIDER = os.getenv("PROVIDER", "gemini").lower()
_DEFAULT_MODELS = {"groq": "llama-3.3-70b-versatile", "gemini": "gemini-2.5-flash", "ollama": "qwen2.5-coder:7b", "anthropic": "claude-sonnet-5-5"}
MODEL = os.getenv("MODEL", _DEFAULT_MODELS.get(PROVIDER, ""))
MAX_ATTEMPTS = 3

SYSTEM = """You are a careful data analyst. You answer questions about CSV files
by writing Python (pandas) code. You never compute or guess numbers yourself.

OUTPUT FORMAT
1. Reply with EITHER one ```python code block OR a single line starting with
   CANNOT_DETERMINE: followed by the specific reason.
2. The code must be standalone: import pandas, load the CSVs with relative
   paths like pd.read_csv("data/orders.csv"), and store the final answer in a
   variable named `result` (a number, string, or small list/dict).
3. Also create a list named `assumptions` with short strings describing every
   data-cleaning decision (duplicates removed, rows excluded and how many, date
   format used, currency handling, etc.).
4. Do not hardcode numbers you did not compute from the data. Do not read any
   file outside data/.

HOW TO HANDLE MESSY DATA (a DATA PROFILE computed over all rows is provided; follow it)
a. Duplicates: if the profile reports exact duplicate rows, call drop_duplicates()
   before counting or summing records, and say so in assumptions.
b. Missing values: never fill them in silently. Exclude them from sums, and say
   how many rows were excluded.
c. Dates: parse each format SEPARATELY with the explicit format strings the
   profile gives. Never use dayfirst=True/False or format='mixed' on a whole
   column, because that mis-reads ISO dates.
d. Currencies: if amounts are in more than one currency and no exchange-rate
   table exists, never add currencies together and never silently drop one.
   - Filtering to one currency is allowed ONLY when the question explicitly
     restricts to that currency's records (e.g. "USD orders", "orders paid in EUR").
   - A phrase like "total in USD", "overall total", "across all orders" or
     "all customers' spend" asks for EVERY record expressed in one currency. That
     requires converting, which is impossible without a rate table. In that case
     use CANNOT_DETERMINE, or return per-currency totals as a dict such as
     {"USD": ..., "EUR": ...}. Never return a single number that quietly leaves
     out the other currency's rows.
e. Joins: records whose key has no match in the other table (see the profile's
   cross-table key checks) must be left out of comparisons, and you must say so.

WHEN TO REFUSE (CANNOT_DETERMINE). A justified refusal beats a confident wrong answer.
- A column or table the question needs does not exist. Check the profile's column
  lists. NEVER substitute a proxy: for example, do not approximate profit margin
  from revenue or refunds, and do not treat country as region.
- The question mentions a specific ID (customer, order...) that is outside the
  profile's id range or otherwise not in the data. Never return 0 for something
  that does not exist.
- The question's premise is false or the data contradicts it in a way that makes
  any number unreliable.
Name the exact missing column, ID or conflict in your reason.
"""


# ----------------------------------------------------------------- LLM call
def _call_gemini(system: str, messages: list) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "model" if m["role"] == "assistant" else "user",
                      "parts": [{"text": m["content"]}]} for m in messages],
        "generationConfig": {"temperature": 0},
    }
    for attempt in range(1, 6):
        r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=120)
        if r.status_code in (429, 503):  # free tier rate limit / busy: wait and retry
            wait = 15 * attempt
            print(f"  (Gemini busy or rate-limited, waiting {wait}s, retry {attempt}/5)")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:300]}")
        parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    raise RuntimeError("Gemini kept rate-limiting. Wait a minute and try again.")


def _call_groq(system: str, messages: list) -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    body = {"model": MODEL, "temperature": 0,
            "messages": [{"role": "system", "content": system}] + messages}
    for attempt in range(1, 6):
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=120)
        if r.status_code in (429, 503):  # rate limit / busy: wait and retry
            wait = 10 * attempt
            print(f"  (Groq busy or rate-limited, waiting {wait}s, retry {attempt}/5)")
            time.sleep(wait)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Groq error {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"] or ""
    raise RuntimeError("Groq kept rate-limiting. Wait a minute and try again.")


def _call_ollama(system: str, messages: list) -> str:
    body = {"model": MODEL, "stream": False, "options": {"temperature": 0},
            "messages": [{"role": "system", "content": system}] + messages}
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    r = requests.post(f"{host}/api/chat", json=body, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"Ollama error {r.status_code}: {r.text[:300]}")
    return r.json()["message"]["content"]


def _call_anthropic(system: str, messages: list) -> str:
    import anthropic  # only needed if PROVIDER=anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    resp = client.messages.create(model=MODEL, max_tokens=2000, temperature=0,
                                  system=system, messages=messages)
    return "".join(b.text for b in resp.content if b.type == "text")


def call_llm(system: str, messages: list) -> str:
    if PROVIDER == "groq":
        return _call_groq(system, messages)
    if PROVIDER == "gemini":
        return _call_gemini(system, messages)
    if PROVIDER == "ollama":
        return _call_ollama(system, messages)
    if PROVIDER == "anthropic":
        return _call_anthropic(system, messages)
    raise RuntimeError(f"Unknown PROVIDER '{PROVIDER}'. Use groq, gemini, ollama or anthropic.")


# ------------------------------------------------------------------ helpers
def schema_summary() -> str:
    """Full-table data profile (from profiler.py) plus a few sample rows per table."""
    parts = [profile_tables(), "\nSAMPLE ROWS"]
    for csv in sorted(DATA_DIR.glob("*.csv")):
        df = pd.read_csv(csv)
        parts.append(f"data/{csv.name}:\n" + df.head(4).to_string(index=False))
    return "\n".join(parts)


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
