import pandas as pd

# Load orders data
orders = pd.read_csv("data/orders.csv")

# 1. Remove exact duplicate rows
duplicates_removed = orders.shape[0] - orders.drop_duplicates().shape[0]
orders = orders.drop_duplicates()

# 2. Exclude rows with missing amount (cannot be counted in revenue)
missing_amount = orders['amount'].isna().sum()
orders = orders.dropna(subset=['amount'])

# 3. Filter to USD orders only
usd_orders = orders[orders['currency'] == 'USD']

# 4. Compute total revenue from USD orders
result = usd_orders['amount'].sum()

# Record assumptions about data cleaning
assumptions = [
    f"Dropped {duplicates_removed} exact duplicate rows from orders.csv",
    f"Excluded {missing_amount} rows with missing amount values",
    "Summed only rows where currency == 'USD'; other currencies are ignored as per the question"
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
