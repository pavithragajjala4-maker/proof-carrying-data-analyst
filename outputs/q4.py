import pandas as pd

# Load the refunds data
refunds = pd.read_csv("data/refunds.csv")

# No duplicate rows to drop (profile reports 0 exact duplicates)
# No missing values affect the row count, so all rows are included

# Count total refund records
result = len(refunds)

# Document assumptions made during processing
assumptions = [
    "No duplicate rows in refunds.csv; none removed.",
    "All rows have valid data for counting; no rows excluded."
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
