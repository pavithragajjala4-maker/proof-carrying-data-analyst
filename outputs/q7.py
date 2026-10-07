import pandas as pd

# Load customers data
customers = pd.read_csv("data/customers.csv")

# Parse the signup_date column (ISO format)
customers["signup_date"] = pd.to_datetime(customers["signup_date"], format="%Y-%m-%d")

# Exclude rows with missing country information
missing_country = customers["country"].isna().sum()
customers_clean = customers.dropna(subset=["country"])

# Count customers whose country is India
result = (customers_clean["country"] == "India").sum()

# Record assumptions and cleaning steps
assumptions = [
    f"Dropped {missing_country} rows with missing country values.",
    "Parsed signup_date with format='%Y-%m-%d'."
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
