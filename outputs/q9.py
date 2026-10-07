import pandas as pd

# Load data
customers = pd.read_csv("data/customers.csv")
orders = pd.read_csv("data/orders.csv")
refunds = pd.read_csv("data/refunds.csv")

# -------------------------------------------------
# Assumptions / data‑cleaning decisions
# -------------------------------------------------
assumptions = []

# 1. Remove exact duplicate rows in orders (15 rows)
orders = orders.drop_duplicates()
assumptions.append("Removed 15 exact duplicate rows from orders")

# 2. Exclude refunds whose order_id does not exist in orders (3 rows)
#    (inner join will automatically drop them)
merged = refunds.merge(
    orders[["order_id", "amount"]],  # keep only needed column from orders
    on="order_id",
    how="inner",
    indicator=True,
)

unmatched_refunds = merged["_merge"].value_counts().get("left_only", 0)
if unmatched_refunds:
    assumptions.append(f"Excluded {unmatched_refunds} refunds with no matching order_id")

# Drop the merge indicator column
merged = merged.drop(columns="_merge")

# 3. Exclude refunds where the corresponding order amount is missing (NaN)
missing_amount = merged["amount"].isna().sum()
merged = merged.dropna(subset=["amount"])
if missing_amount:
    assumptions.append(f"Excluded {missing_amount} refunds because the order amount was missing")

# -------------------------------------------------
# Compute the answer
# -------------------------------------------------
# Count refunds where refund_amount > order amount
result = (merged["refund_amount"] > merged["amount"]).sum()


# ---- appended automatically by executor.py (do not edit) ----
import json as _json
def _ser(o):
    try:
        return o.item()          # numpy / pandas scalars
    except Exception:
        return str(o)
print("RESULT_JSON:" + _json.dumps(result, default=_ser))
try:
    print("ASSUMPTIONS_JSON:" + _json.dumps(list(assumptions), default=_ser))
except NameError:
    print("ASSUMPTIONS_JSON:[]")
