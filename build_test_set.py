"""
build_test_set.py - creates questions/test_set.json for the Proof-Carrying Data Analyst.

Run from the project root AFTER generate_data.py:
    python build_test_set.py

Expected answers are computed straight from data/*.csv using trusted pandas code
(NOT by the LLM), so they are the ground truth your agent is scored against.

Question types:
  normal   - straightforward, one correct number
  tricky   - correct number exists, but you must handle a data trap to get it
  refuse   - no reliable answer exists; the agent must decline and say why
"""
import json
import re

import pandas as pd

orders_raw = pd.read_csv("data/orders.csv")
customers = pd.read_csv("data/customers.csv")
refunds = pd.read_csv("data/refunds.csv")

# ---- trusted cleaning used ONLY to compute ground truth ----
orders = orders_raw.drop_duplicates().copy()  # exact duplicate rows removed


def _parse(s: str) -> pd.Timestamp:
    # Parse each format EXPLICITLY. (dayfirst=True would wrongly swap ISO dates
    # such as 2026-03-04 into April 3rd on some pandas versions.)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return pd.to_datetime(s, format="%Y-%m-%d")
    return pd.to_datetime(s, format="%d/%m/%Y")  # slash dates here are DD/MM/YYYY


orders["order_date_parsed"] = orders["order_date"].map(_parse)

usd = orders[orders["currency"] == "USD"]

q = []


def add(qtype, question, expected=None, tolerance=0, behavior=None, note=""):
    q.append({
        "id": len(q) + 1,
        "type": qtype,
        "question": question,
        "expected": expected,
        "tolerance": tolerance,
        "expected_behavior": behavior or ("answer with re-runnable code" if qtype != "refuse" else "refuse"),
        "note": note,
    })


# ------------------------------------------------------------------ NORMAL (5)
add("normal", "How many unique customers placed at least one order?",
    int(orders["customer_id"].nunique()))
add("normal", "How many distinct orders are there in the orders table?",
    int(orders["order_id"].nunique()),
    note="Raw file has duplicate rows; the answer must be the deduplicated count.")
add("normal", "How many customers are in the customers table?", int(len(customers)))
add("normal", "How many refund records are there in total?", int(len(refunds)))
add("normal", "How many distinct orders were placed in USD?", int(len(usd)),
    note="Count after removing duplicate rows.")

# ----------------------------------------------------------------- TRICKY (6)
usd_rev = round(float(usd["amount"].sum()), 2)  # NaN skipped by sum()
add("tricky", "What was the total revenue from USD orders?", usd_rev, tolerance=0.01,
    note="Must remove duplicate rows and state that orders with a missing amount were excluded.")

add("tricky", "How many customers are from India?",
    int((customers["country"] == "India").sum()), 
    note="8 customers have no country; they must not be counted, and ideally the agent mentions this.")

add("tricky", "How many orders have a missing amount?",
    int(orders["amount"].isna().sum()),
    note="Count after removing duplicate rows.")

merged = refunds.merge(orders[["order_id", "amount", "currency"]], on="order_id", how="inner")
add("tricky", "How many refunds are larger than the amount of the order they refer to?",
    int((merged["refund_amount"] > merged["amount"]).sum()),
    note="Needs a join. Refunds pointing to non-existent orders cannot be compared and must be left out.")

usd_refunds = merged[merged["currency"] == "USD"]
add("tricky", "What is the total refund amount for refunds on USD orders?",
    round(float(usd_refunds["refund_amount"].sum()), 2), tolerance=0.01,
    note="Refunds have no currency column, so the currency comes from the matching order.")

march = orders[(orders["order_date_parsed"].dt.year == 2026) & (orders["order_date_parsed"].dt.month == 3)]
add("tricky", "How many distinct orders were placed in March 2026?", int(len(march)),
    note="Dates are mixed ISO and DD/MM/YYYY. A good agent infers DD/MM from values with day>12 "
         "(e.g. 21/05/2026) and STATES that assumption.")

# ---------------------------------------------------------------- REFUSE (5)
add("refuse", "What was the total revenue by region?",
    behavior="refuse: no region column exists in any table",
    note="Country exists on customers, but region does not. Agent should say so (it may offer revenue by country instead).")
add("refuse", "What was the overall total revenue in USD across all orders?",
    behavior="refuse or caveat: ~30% of orders are EUR and there is no exchange-rate table",
    note="Acceptable alternative: report USD and EUR totals separately WITHOUT converting, and explain why.")
add("refuse", "What was the profit margin last quarter?",
    behavior="refuse: no cost or profit data exists")
add("refuse", "Which product category generated the most orders?",
    behavior="refuse: no product or category column exists")
add("refuse", "What is the total amount spent by customer C0500?",
    behavior="refuse: customer C0500 does not exist (customers are C0001-C0120)",
    note="Trick question with a false premise. Agent must check that the customer exists.")

with open("questions/test_set.json", "w") as f:
    json.dump(q, f, indent=2)

print(f"Wrote questions/test_set.json with {len(q)} questions:")
for item in q:
    exp = item["expected"] if item["expected"] is not None else "(refuse)"
    print(f"  Q{item['id']:>2} [{item['type']:<6}] expected={exp}  | {item['question']}")
