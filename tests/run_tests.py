#!/usr/bin/env python3
"""tests/run_tests.py -- zero-dependency test runner.

Use this if pytest is not installed:

    python tests/run_tests.py

It collects every `test_*` function from tests/test_solver.py, supports the one
parametrize case used there, and exits non-zero on failure.
"""
from __future__ import annotations

import pathlib
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))


def main() -> int:
    import test_solver as mod

    names = [n for n in dir(mod) if n.startswith("test_")]
    passed, failed = 0, []
    for name in sorted(names):
        fn = getattr(mod, name)
        params = getattr(fn, "_params", None)
        calls = []
        if params:
            argnames, argvalues = params
            for v in argvalues:
                calls.append((v,))
        else:
            calls.append(())
        for args in calls:
            label = f"{name}{list(args) if args else ''}"
            try:
                fn(*args)
                passed += 1
                print(f"PASS  {label}")
            except Exception:
                failed.append(label)
                print(f"FAIL  {label}")
                traceback.print_exc()
    print(f"\n{passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
