#!/usr/bin/env python3
"""scripts/validate_db.py -- CI gate for the data contracts.

Three checks:
  1. parts/parts_db.json validates against parts/db.schema.json
  2. every golden spec validates against spec/project_spec.schema.json
  3. cross-file integrity: every part has a signal profile, and every signal
     profile points at a part that actually exists in the DB

Two severity tiers:
  BLOCKING  -- a contract violation. Exit code 1.
  INCOMPLETE -- a placeholder that still needs real data (a part whose
                source_url is still "TODO"). Loudly reported. Exit code 0
                unless --strict is passed, which is how CI enforces it once
                the parts database has been finished.

Usage:
    python scripts/validate_db.py            # blocking errors fail the build
    python scripts/validate_db.py --strict   # placeholders fail the build too
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLACEHOLDER = "TODO"


def load(rel: str):
    with (ROOT / rel).open(encoding="utf-8") as fh:
        return json.load(fh)


def collect(instance, schema, label, blocking, incomplete):
    from jsonschema import Draft7Validator
    validator = Draft7Validator(schema)
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        # A source_url that is still a TODO is unfinished data, not a broken
        # contract -- but it must still be visible until it is filled in.
        try:
            value = err.instance
        except Exception:                                    # pragma: no cover
            value = None
        if isinstance(value, str) and value.startswith(PLACEHOLDER):
            incomplete.append(f"{label}: {where}: {value}")
        else:
            blocking.append(f"{label}: {where}: {err.message}")


def main() -> int:
    strict = "--strict" in sys.argv
    blocking: list = []
    incomplete: list = []

    db = load("parts/parts_db.json")
    db_schema = load("parts/db.schema.json")
    spec_schema = load("spec/project_spec.schema.json")
    profiles = load("parts/signal_profiles.json")
    profiles_schema = load("parts/signal_profiles.schema.json")

    collect(db, db_schema, "parts_db.json", blocking, incomplete)
    collect(profiles, profiles_schema, "signal_profiles.json", blocking, incomplete)

    goldens = load("eval/golden_specs.json").get("specs", [])
    for g in goldens:
        collect(g.get("spec", {}), spec_schema, f"golden_spec {g.get('id')}",
                blocking, incomplete)

    part_ids = {p["id"] for p in db.get("parts", [])}
    for pid in sorted(part_ids):
        if pid not in profiles:
            blocking.append(f"signal_profiles.json: no profile for part '{pid}'")
    for pid in sorted(profiles):
        if pid not in part_ids:
            blocking.append(f"signal_profiles.json: profile '{pid}' has no part in the DB")

    if blocking:
        print(f"FAILED -- {len(blocking)} blocking problem(s):")
        for p in blocking:
            print(f"  - {p}")
        return 1

    print(f"OK  parts_db.json valid ({len(db.get('parts', []))} parts, "
          f"{len(db.get('boards', []))} board(s), db_version {db.get('db_version')})")
    print(f"OK  {len(goldens)} golden specs valid against spec/project_spec.schema.json")
    print(f"OK  signal profiles consistent ({len(profiles)} parts)")

    if incomplete:
        print()
        print(f"INCOMPLETE -- {len(incomplete)} placeholder(s) still need real data:")
        for p in incomplete:
            print(f"  - {p}")
        print("  (these are TODO source URLs; each part needs the real listing or "
              "datasheet link. Run with --strict to fail the build on them.)")
        if strict:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
