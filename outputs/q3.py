import pandas as pd

# Load customers data
customers = pd.read_csv("data/customers.csv")

# No exact duplicate rows reported, but apply drop_duplicates() as a safety measure
customers = customers.drop_duplicates()

# Count distinct customers
result = customers["customer_id"].nunique()

# Record assumptions made during processing
assumptions = [
    "Applied drop_duplicates() on customers table (0 duplicates found).",
    "Counted distinct customer_id values to determine number of customers.",
    "Missing values in other columns do not affect the customer count."
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
