import pandas as pd

# Load orders data
orders = pd.read_csv("data/orders.csv")

# Remove exact duplicate rows as indicated by the data profile
orders = orders.drop_duplicates()

# Filter orders that are in USD currency
usd_orders = orders[orders["currency"] == "USD"]

# Count distinct order IDs (after duplicate removal)
result = usd_orders["order_id"].nunique()

# Record assumptions and cleaning steps
assumptions = [
    "Removed 15 exact duplicate rows from orders.csv using drop_duplicates().",
    "Filtered rows where currency == 'USD' to count USD orders.",
    "Counted distinct order_id values after duplicate removal."
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
