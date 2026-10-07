import pandas as pd

# Load data
customers = pd.read_csv("data/customers.csv")
orders = pd.read_csv("data/orders.csv")
refunds = pd.read_csv("data/refunds.csv")

assumptions = [
    "order_date and refund_date may be in mixed formats; parsed with dayfirst=True",
    "Rows with missing order amount are excluded from revenue calculations",
    "Refunds are subtracted from the order they reference; refunds for orders outside the period are ignored",
    "Profit margin is defined as (total sales - total refunds) / total sales",
    "The 'last quarter' is the 3‑month period ending on the latest order_date in the orders table"
]

# Parse dates, coerce errors to NaT
orders["order_date"] = pd.to_datetime(orders["order_date"], dayfirst=True, errors="coerce")
refunds["refund_date"] = pd.to_datetime(refunds["refund_date"], dayfirst=True, errors="coerce")

# Drop rows where order_date could not be parsed or amount is missing
orders = orders.dropna(subset=["order_date", "amount"])

# Determine the most recent order date
max_date = orders["order_date"].max()

# Define start of the last quarter (3 months prior)
quarter_start = max_date - pd.DateOffset(months=3)

# Filter orders that fall within the last quarter (inclusive of start date)
orders_q = orders[(orders["order_date"] > quarter_start) & (orders["order_date"] <= max_date)]

# Total sales in the quarter
total_sales = orders_q["amount"].sum()

# Join refunds to orders to know which refunds belong to orders in the quarter
refunds_q = refunds.merge(orders_q[["order_id"]], on="order_id", how="inner")

# Total refunds for those orders
total_refunds = refunds_q["refund_amount"].sum()

# Compute profit margin; guard against division by zero
if total_sales == 0:
    result = None  # No sales in the period, margin undefined
else:
    result = (total_sales - total_refunds) / total_sales


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
