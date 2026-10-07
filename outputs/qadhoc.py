import pandas as pd

# Load data
customers = pd.read_csv("data/customers.csv")
orders = pd.read_csv("data/orders.csv")

# ------------------------------------------------------------------
# Assumptions and cleaning steps
# ------------------------------------------------------------------
assumptions = [
    "Duplicate order rows are removed based on 'order_id'.",
    "Rows with missing 'customer_id' in orders are excluded (none expected).",
    "Date columns are not needed for this calculation, so no parsing is performed.",
    "Currency differences do not affect counting unique customers.",
]

# Remove exact duplicate rows in orders (if any)
orders_clean = orders.drop_duplicates(subset=["order_id"])

# Exclude any rows where customer_id is missing (just in case)
orders_clean = orders_clean[orders_clean["customer_id"].notna()]

# Compute the number of unique customers who placed at least one order
result = orders_clean["customer_id"].nunique()


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
