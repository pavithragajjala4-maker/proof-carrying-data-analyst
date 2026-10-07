import pandas as pd

# Load orders data
orders = pd.read_csv("data/orders.csv")

# 1. Remove exact duplicate rows
duplicates_removed = orders.shape[0] - orders.drop_duplicates().shape[0]
orders = orders.drop_duplicates()

# 2. Parse order_date with the two known formats
# First try ISO format
orders["order_date_parsed"] = pd.to_datetime(
    orders["order_date"], format="%Y-%m-%d", errors="coerce"
)

# For rows that failed, parse the DD/MM/YYYY format
mask_ddmmyyyy = orders["order_date_parsed"].isna()
orders.loc[mask_ddmmyyyy, "order_date_parsed"] = pd.to_datetime(
    orders.loc[mask_ddmmyyyy, "order_date"], format="%d/%m/%Y", errors="coerce"
)

# 3. Filter orders placed in March 2026
march_2026 = orders[
    (orders["order_date_parsed"].dt.year == 2026)
    & (orders["order_date_parsed"].dt.month == 3)
]

# 4. Count distinct order_id values
result = march_2026["order_id"].nunique()

# Record assumptions and actions taken
assumptions = [
    f"Removed {duplicates_removed} exact duplicate rows from orders.csv.",
    "Parsed 'order_date' using two explicit formats: '%Y-%m-%d' for ISO dates and '%d/%m/%Y' for DD/MM/YYYY dates.",
    "Rows with unparsable dates (if any) are excluded from the March 2026 count.",
    "Counted distinct order_id values after duplicate removal.",
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
