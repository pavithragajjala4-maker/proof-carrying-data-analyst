import pandas as pd

# Load the orders table
orders = pd.read_csv("data/orders.csv")

# Remove exact duplicate rows as indicated by the data profile
orders_clean = orders.drop_duplicates()

# Count distinct order IDs
result = orders_clean["order_id"].nunique()

# Record assumptions made during processing
assumptions = [
    "Removed 15 exact duplicate rows from orders.csv before counting.",
    "No date parsing needed for this count."
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
