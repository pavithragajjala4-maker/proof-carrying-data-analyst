"""
executor.py - saves and runs generated analysis code.

Every answer is backed by a standalone .py file in outputs/. That file is what
the verifier re-runs later, so the proof is always re-runnable from scratch.

NOTE: this runs code in a separate Python process with a timeout. It is not a
hardened sandbox (see README scope note); it is fine for a hackathon demo.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # project root

FOOTER = '''

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
'''


def save_script(code: str, path: Path) -> None:
    """Write the generated code plus the result-printing footer to disk."""
    path.write_text(code.rstrip() + "\n" + FOOTER, encoding="utf-8")


def run_script(path: Path, timeout: int = 60) -> dict:
    """Run a saved script from the project root and parse its output."""
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "result": None, "assumptions": [],
                "error": f"Timed out after {timeout}s"}

    result, assumptions, found = None, [], False
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT_JSON:"):
            result, found = json.loads(line[len("RESULT_JSON:"):]), True
        elif line.startswith("ASSUMPTIONS_JSON:"):
            assumptions = json.loads(line[len("ASSUMPTIONS_JSON:"):])

    if proc.returncode != 0 or not found:
        err = (proc.stderr or "No `result` variable was produced.").strip()
        return {"ok": False, "result": None, "assumptions": [],
                "error": err[-1500:]}  # last part of the traceback is the useful bit
    return {"ok": True, "result": result, "assumptions": assumptions, "error": ""}
