"""
profiler.py - scans EVERY row of every CSV in data/ and reports the problems that
trip up analysis: exact duplicate rows, missing values, mixed date formats,
multi-currency columns, and keys that don't match across tables.

The report is computed by plain pandas code (not by an LLM), so it is reliable
evidence. agent.py puts it in the prompt, and it is also useful in the demo:

    python src/profiler.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLASH = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _is_text(s: pd.Series) -> bool:
    return s.dtype == object or pd.api.types.is_string_dtype(s)


def _date_report(col: str, s: pd.Series):
    """If the column holds dates stored as text, describe the formats in use."""
    vals = s.dropna().astype(str)
    if vals.empty:
        return None
    iso = vals[vals.str.match(ISO)]
    slash = vals[vals.str.match(SLASH)]
    if len(iso) + len(slash) < 0.9 * len(vals):
        return None  # not a date column

    lines = [f"  '{col}' is a DATE stored as text with {2 if len(iso) and len(slash) else 1} format(s):"]
    if len(iso):
        lines.append(f"    - {len(iso)} rows are ISO YYYY-MM-DD (unambiguous). Parse with format='%Y-%m-%d'.")
    if len(slash):
        parts = slash.str.extract(SLASH).astype(int)
        first_gt12 = int((parts[0] > 12).sum())   # first number can only be a day
        second_gt12 = int((parts[1] > 12).sum())  # second number can only be a day
        ambiguous = int(((parts[0] <= 12) & (parts[1] <= 12)).sum())
        if first_gt12 and not second_gt12:
            order, fmt = "DD/MM/YYYY", "%d/%m/%Y"
            why = f"{first_gt12} rows have a first number >12 and none have a second number >12"
        elif second_gt12 and not first_gt12:
            order, fmt = "MM/DD/YYYY", "%m/%d/%Y"
            why = f"{second_gt12} rows have a second number >12 and none have a first number >12"
        else:
            order, fmt, why = "UNKNOWN", None, "evidence is missing or contradictory"
        lines.append(f"    - {len(slash)} rows are slash dates, evidence says {order} ({why}); "
                     f"{ambiguous} of them could be read either way if you did not know the order.")
        if fmt:
            lines.append(f"      Parse these with format='{fmt}'.")
    if len(slash):
        lines.append("    - NEVER parse the whole column in one call with dayfirst=True/False or format='mixed': "
                     "that mis-reads ISO dates. Parse each format separately with an explicit format string.")
    return "\n".join(lines)


def profile_tables() -> str:
    tables = {p.stem: pd.read_csv(p) for p in sorted(DATA_DIR.glob("*.csv"))}
    out = ["DATA PROFILE (computed by code over ALL rows; treat as authoritative)"]
    out.append("Tables available: " + ", ".join(f"data/{n}.csv" for n in tables))

    for name, df in tables.items():
        out.append(f"\nTABLE data/{name}.csv - {len(df)} rows, {len(df.columns)} columns")
        out.append("  Columns: " + ", ".join(df.columns))
        dups = int(df.duplicated().sum())
        out.append(f"  Exact duplicate rows: {dups}" + (" -> remove with drop_duplicates() before counting/summing" if dups else ""))

        for col in df.columns:
            s = df[col]
            notes = []
            nulls = int(s.isna().sum())
            if nulls:
                notes.append(f"{nulls} missing values")
            if _is_text(s):
                nun = s.nunique(dropna=True)
                if col.endswith("_id") and nun:
                    vals = sorted(s.dropna().astype(str).unique())
                    notes.append(f"{nun} distinct ids, from {vals[0]} to {vals[-1]}")
                elif nun <= 8 and nun > 0:
                    counts = s.value_counts().to_dict()
                    notes.append("categories: " + ", ".join(f"{k} ({v})" for k, v in counts.items()))
                    if "currency" in col.lower() and nun > 1:
                        notes.append("MULTIPLE CURRENCIES in one column")
            elif pd.api.types.is_numeric_dtype(s) and s.notna().any():
                notes.append(f"numeric, min {s.min():g}, max {s.max():g}")
            if notes:
                out.append(f"  - {col}: " + "; ".join(notes))

        for col in df.columns:
            if _is_text(df[col]):
                rep = _date_report(col, df[col])
                if rep:
                    out.append(rep)

    # keys that should match across tables: a table's primary key is its OWN id column
    # (orders -> order_id, customers -> customer_id)
    pk = {}
    for n, df in tables.items():
        own = {n + "_id", n.rstrip("s") + "_id"}
        pk[n] = [c for c in df.columns if c in own]
    checks = []
    for child, cdf in tables.items():
        for col in cdf.columns:
            if not col.endswith("_id"):
                continue
            for parent, pdf in tables.items():
                if parent != child and col in pk[parent]:
                    missing = sorted(set(cdf[col].dropna()) - set(pdf[col].dropna()))
                    checks.append(f"  - data/{child}.csv.{col} -> data/{parent}.csv.{col}: "
                                  + (f"{len(missing)} values have NO match in {parent} (e.g. {', '.join(map(str, missing[:4]))})"
                                     if missing else "all values match"))
    if checks:
        out.append("\nCROSS-TABLE KEY CHECKS")
        out.extend(checks)

    out.append("\nNOT PRESENT IN ANY TABLE: any column not listed above does not exist "
               "(e.g. do not invent region, product, cost or exchange-rate data).")
    return "\n".join(out)


if __name__ == "__main__":
    print(profile_tables())
