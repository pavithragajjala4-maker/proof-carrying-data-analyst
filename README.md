# Proof-Carrying Data Analyst

HackNex 2026 - Internal Qualifier - **PS08: Proof-Carrying Data Analyst (Agentic GenAI)**

An AI agent that answers questions about messy, multi-table data. **Every number comes from code that anyone can re-run**, and the agent **refuses** when the data cannot support a reliable answer instead of guessing.

## What it does

1. **Profiles the data first.** `src/profiler.py` scans every row of every table (plain pandas, no LLM) and reports exact duplicates, missing values, mixed currencies, mixed date formats (with evidence for DD/MM vs MM/DD), and keys that do not match across tables.
2. **Writes code, never numbers.** The LLM receives the question plus the data profile and replies with pandas code, or with `CANNOT_DETERMINE: <reason>`. It never states a result itself.
3. **Runs the code.** `src/executor.py` saves the code as `outputs/q<id>.py` and runs it. If it crashes, the error goes back to the LLM for up to 3 attempts.
4. **Shows its assumptions.** Every answer lists the cleaning decisions it made (duplicates removed, rows excluded, date format used, currency handling).
5. **Proves it.** `src/verifier.py` re-runs each saved script in a fresh Python process and checks that it prints the same number the agent reported.

```
Question + data/*.csv
        |
  profiler.py   (duplicates, nulls, currencies, date formats, broken keys)
        |
  agent.py      LLM -> pandas code  OR  CANNOT_DETERMINE + reason
        |
  executor.py   saves outputs/q<id>.py, runs it, retries on error
        |
  answer + code + assumptions        refusal + reason
        |
  verifier.py   re-runs the saved code from scratch and compares
```

## Technologies, libraries and models used

| Item | Details |
|---|---|
| Language | Python 3.10+ |
| Libraries | `pandas`, `requests`, `python-dotenv` |
| LLM | Groq API (free tier), model set by `MODEL` in `.env` - **FILL IN: the exact model name you used** |
| Other providers supported | Google Gemini API, Ollama (local), Anthropic API - switch with `PROVIDER` in `.env` |
| Data | **Synthetic**, created by `generate_data.py` (no external dataset) |
| AI assistance | AI tools were used to help write this code. The team reviewed and understands it and takes responsibility for it. |

## Setup

```bash
git clone https://github.com/<your-username>/proof-carrying-data-analyst.git
cd proof-carrying-data-analyst
pip install -r requirements.txt
```

Create a file named `.env` in the project root (it is git-ignored, never commit it):

```
PROVIDER=groq
GROQ_API_KEY=your-key-here
MODEL=your-model-name
```

Get a free Groq key at https://console.groq.com/keys. List the models your key can use with:

```bash
python -c "import os,requests; from dotenv import load_dotenv; load_dotenv(); r=requests.get('https://api.groq.com/openai/v1/models', headers={'Authorization':'Bearer '+os.environ['GROQ_API_KEY']}); print('\n'.join(sorted(m['id'] for m in r.json()['data'])))"
```

## Run it

```bash
python generate_data.py          # 1. create the messy dataset (fixed seed: identical every time)
python build_test_set.py         # 2. build the 16 test questions with ground-truth answers
python src/profiler.py           # 3. (optional) see the data profile the agent sees

python src/agent.py "How many unique customers placed at least one order?"   # ask one question
```

### Reproduce the reported results

```bash
python src/run_tests.py          # runs all 16 questions and grades them
python src/verifier.py           # re-runs every saved proof script from scratch
```

Outputs are written to `outputs/`: `q<id>.py` (the proof code), `q<id>.json` (answer, status, assumptions), `test_report.json` and `verification_report.json`.

On the free tier you may see "rate-limited, waiting..." messages. This is normal; the agent retries automatically.

## The dataset and the traps

`generate_data.py` builds a small online store (customers, orders, refunds) with deliberately planted problems. The answer key is `questions/trap_log.json` and must never be shown to the agent.

| Trap | How it appears |
|---|---|
| Mixed currencies | ~30% of orders are EUR; there is no exchange-rate table |
| Duplicate rows | 15 exact duplicate order rows |
| Missing values | 12 orders without an amount, 8 customers without a country |
| Mixed / ambiguous dates | ISO `2026-03-26` and `DD/MM/YYYY` in the same column |
| Contradictions | 4 refunds larger than their order; 3 refunds for orders that do not exist |
| Missing columns | No region, product, cost or exchange-rate data |

## Sample input and output

Input:

```
python src/agent.py "How many unique customers placed at least one order?"
```

Output:

```
Question : How many unique customers placed at least one order?
Status   : answered  (attempts: 1)
Answer   : 112
Proof    : outputs/qadhoc.py
  - Duplicate order rows are removed based on 'order_id'.
  - Rows with missing 'customer_id' in orders are excluded (none expected).
  - Date columns are not needed for this calculation, so no parsing is performed.
  - Currency differences do not affect counting unique customers.
```

A question the data cannot answer, such as `python src/agent.py "What was the profit margin last quarter?"`, returns `Status: refused` with a reason naming the missing cost data, and produces no number.

## Results

**Development set: 16 questions** (5 normal, 6 tricky, 5 should-refuse) in `questions/test_set.json`, graded by `src/run_tests.py` against ground truth computed with trusted pandas code.

| Run | Result | What changed |
|---|---|---|
| First version (agent saw only schema + 5 sample rows) | 9/16 (56%) | Missed duplicates, mis-parsed dates, invented numbers for missing data |
| + data profiler + stricter rules | 15/16 (94%) | Only Q13 (mixed-currency total) failed |
| + tighter currency rule | Q13 passes in a targeted re-run | Total across currencies must refuse or split by currency |

**Verifier:** 12/12 answered questions re-ran from saved code and produced the same number.

> Update this table with your final full run of `python src/run_tests.py` before submitting.

**Honest caveat:** the rules were tuned using these same 16 questions, so the score is optimistic for unseen questions. LLM output can also vary slightly between runs.

## Scope note

### Minimum viable solution (implemented)

- Question answering over **multiple related CSV tables** with joins
- **Data profiler** that finds duplicates, missing values, mixed currencies, mixed date formats and broken keys across all rows
- **LLM-generated pandas code** with a retry loop on errors; numbers always come from executed code
- **Re-runnable proof** for every answer (`outputs/q<id>.py`) plus listed assumptions
- **Independent verifier** that re-runs each proof in a fresh process
- **Refusal logic** for missing columns, false premises (nonexistent ID), and mixed currencies with no exchange rate
- **Evaluation harness** with 16 questions and ground truth from trusted code

### Stretch goals (not implemented, or only partly)

- Documents (PDF/text) as a data source alongside tables - **not done**
- Adversarial or trick data beyond the planted traps - **only partly** (the profiler covers the known trap types)
- Evaluation on **held-out / unseen** questions - **not done**
- A web UI for the demo - **not done** (command-line only)

### Known limitations

- Generated code runs in a separate Python process with a timeout. This is **not a hardened sandbox**; do not run it on untrusted data or prompts.
- The profiler's date logic handles ISO and slash-separated dates; other formats are not detected.
- Contradictions such as "refund larger than order" are not detected by the profiler; the LLM must find them through code.
- Results depend on the LLM used and can vary between runs.

## Repository layout

```
data/              generated CSVs (customers, orders, refunds)
questions/         test_set.json (ground truth) and trap_log.json (answer key)
outputs/           proof scripts, answers, test and verification reports
src/profiler.py    data profile computed over all rows
src/agent.py       LLM call, prompt rules, retry loop, CLI
src/executor.py    saves and runs generated code
src/run_tests.py   grades the agent on the test set
src/verifier.py    re-runs saved proofs to confirm the numbers
generate_data.py   builds the messy dataset (fixed seed)
build_test_set.py  builds the questions with ground-truth answers
```
