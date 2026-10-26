#!/usr/bin/env python3
"""eval/run_eval.py -- the headline number.

Runs the 20 conflict cases through the deterministic solver using hand-written golden
specs. No LLM is involved, so this number measures the solver, not the model.

Usage:
    python eval/run_eval.py            # print table + write eval/RESULTS.md
    python eval/run_eval.py --json     # machine-readable
Exit code 0 if every case matches, 1 otherwise.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from benchtruth.db import load_db          # noqa: E402
from benchtruth.solver import Solver       # noqa: E402


def load(p: pathlib.Path):
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def main() -> int:
    cases = {c["id"]: c for c in load(ROOT / "eval" / "cases.json")["cases"]}
    goldens = load(ROOT / "eval" / "golden_specs.json")["specs"]
    db = load_db()
    solver = Solver(db)

    rows, passed = [], 0
    for g in goldens:
        cid = g["id"]
        case = cases.get(cid)
        if case is None:
            rows.append((cid, "?", case["expected_verdict"] if case else "?",
                         "MISSING CASE", False))
            continue
        plan = solver.solve(g["spec"])
        want_verdict = case["expected_verdict"]
        want_rules = as_list(case.get("expected_rule"))
        got_rules = plan.fired_rules()
        ok = (plan.verdict == want_verdict) and (
            not want_rules or any(r in got_rules for r in want_rules))
        passed += int(ok)
        rows.append((cid, plan.verdict, want_verdict,
                     ",".join(got_rules) or "-", ok))

    width = max(len(r[0]) for r in rows)
    header = f"{'CASE'.ljust(width)}  {'ACTUAL':<8} {'EXPECTED':<8} {'RULES FIRED':<28} OK"
    lines = [header, "-" * len(header)]
    for cid, got, want, rules, ok in rows:
        lines.append(f"{cid.ljust(width)}  {got:<8} {want:<8} {rules:<28} {'PASS' if ok else 'FAIL'}")

    total = len(rows)
    lines.append("")
    lines.append(f"{passed}/{total} correct verdicts")
    text = "\n".join(lines)
    print(text)

    results = ROOT / "eval" / "RESULTS.md"
    results.write_text(
        "# Eval results (solver, deterministic)\n\n"
        "```\n" + text + "\n```\n\n"
        "Rules: `ruleset.md`. Golden specs: `eval/golden_specs.json`.\n"
        "This number measures the solver only -- no LLM calls are made.\n",
        encoding="utf-8")
    print(f"\nwrote {results}")

    if "--json" in sys.argv:
        print(json.dumps([{"case": r[0], "actual": r[1], "expected": r[2],
                           "rules": r[3], "pass": r[4]} for r in rows], indent=2))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
