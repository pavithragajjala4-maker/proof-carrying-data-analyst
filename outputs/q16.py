import pandas as pd

# Load data
customers = pd.read_csv("data/customers.csv")
orders = pd.read_csv("data/orders.csv")
refunds = pd.read_csv("data/refunds.csv")

# ------------------------------------------------------------------
# Assumptions and cleaning steps
# ------------------------------------------------------------------
assumptions = [
    "Duplicate rows are removed based on primary keys (customer_id, order_id, refund_id).",
    "Missing order amounts are treated as 0 and excluded from the total.",
    "All monetary values are assumed to be in the same currency (USD); no conversion applied.",
    "order_date strings may be in 'dd/mm/yyyy' or 'yyyy-mm-dd' format; parsed with dayfirst=True.",
    "refund_date parsing is not required for the calculation.",
    "If the customer has no orders, total spent is 0.",
    "Net spent = sum(order amounts) – sum(refunds for those orders)."
]

# Remove exact duplicate rows
customers = customers.drop_duplicates(subset=["customer_id"])
orders = orders.drop_duplicates(subset=["order_id"])
refunds = refunds.drop_duplicates(subset=["refund_id"])

# Parse order_date to datetime (mixed formats)
orders["order_date"] = pd.to_datetime(orders["order_date"], dayfirst=True, errors="coerce")

# Ensure numeric columns are proper floats; treat NaNs as 0 for amount
orders["amount"] = pd.to_numeric(orders["amount"], errors="coerce").fillna(0)

# ------------------------------------------------------------------
# Filter orders for the target customer
# ------------------------------------------------------------------
target_customer_id = "C0500"
customer_orders = orders[orders["customer_id"] == target_customer_id]

# Sum of order amounts
total_order_amount = customer_orders["amount"].sum()

# ------------------------------------------------------------------
# Compute total refunds for those orders
# ------------------------------------------------------------------
# Join refunds to orders to know which refunds belong to the target customer's orders
refunds_with_orders = refunds.merge(
    customer_orders[["order_id"]], on="order_id", how="inner"
)

total_refund_amount = refunds_with_orders["refund_amount"].sum()

# ------------------------------------------------------------------
# Net total amount spent
# ------------------------------------------------------------------
result = total_order_amount - total_refund_amount


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
