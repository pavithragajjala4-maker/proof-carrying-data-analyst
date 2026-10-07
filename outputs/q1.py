import pandas as pd

# Load data
customers = pd.read_csv("data/customers.csv")
orders = pd.read_csv("data/orders.csv")
refunds = pd.read_csv("data/refunds.csv")

# Clean orders: remove exact duplicate rows as indicated in the profile
orders_clean = orders.drop_duplicates()

# Determine the number of unique customers who have placed at least one order
result = orders_clean["customer_id"].nunique()

# Record assumptions and cleaning steps
assumptions = [
    "Removed 15 exact duplicate rows from orders.csv using drop_duplicates()",
    "All customer_id values in orders.csv match those in customers.csv (no unmatched keys)",
    "Missing values in 'amount' are ignored for this count (they do not affect customer IDs)",
]


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
