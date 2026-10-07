import pandas as pd
import numpy as np

# Load orders data
orders = pd.read_csv("data/orders.csv")

# Assumptions list
assumptions = [
    "Removed 15 exact duplicate rows from orders before any analysis (drop_duplicates).",
    "Missing amounts are represented as NaN; they are counted but not used in any aggregation."
]

# Drop exact duplicate rows
orders = orders.drop_duplicates()

# Count orders with missing amount
result = orders["amount"].isna().sum()


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
