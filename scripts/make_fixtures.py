#!/usr/bin/env python3
"""scripts/make_fixtures.py -- regenerate the sample plans the UI is built against.

    python scripts/make_fixtures.py

Three states, because the UI has to handle all of them:

  plan_flagship_offer.json  the demo build: four violations, priced fixes
  plan_build.json           an approved build: everything green
  plan_refuse.json          a part that is not in the database: the hard refuse

The fixtures are committed so that a renderer can be developed and tested
against them without running the solver, and so a change in the plan contract
shows up as a diff in these files.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from benchtruth.db import load_db          # noqa: E402
from benchtruth.solver import Solver       # noqa: E402
from llm.spec_gen import generate_spec     # noqa: E402

OUT = ROOT / "docs" / "fixtures"

FLAGSHIP = ("ESP32 desk plant monitor: two oled displays, a soil moisture probe on "
            "gpio 25, a servo vent and a buzzer. Wifi, and it has to run off the board.")

BUILD = "a servo and a buzzer and an oled display"

# The hard refuse: a part that is not in the database. The spec is written by
# hand here, because the local parser never invents a part -- that is the point.
REFUSE_SPEC = {
    "board": "esp32-devkitc-v4",
    "goal": "A flux capacitor next to an oled display",
    "peripherals": [
        {"part_id": "UNKNOWN:flux capacitor", "role": "the thing that is not in the database"},
        {"part_id": "ssd1306-096", "role": "display"},
    ],
    "constraints": {"mechanical": {"mount_style": "free"}},
}


def write(name: str, payload: dict) -> None:
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"wrote {path.relative_to(ROOT)}  verdict={payload['verdict']}  "
          f"rules={[v['rule_id'] for v in payload['violations']]}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    db = load_db()
    solver = Solver(db)

    for name, text in (("plan_flagship_offer.json", FLAGSHIP),
                       ("plan_build.json", BUILD)):
        spec = generate_spec(text, db=db)
        plan = solver.solve(spec)
        payload = plan.to_dict()
        payload["_source"] = {"prompt": text, "spec": spec}
        write(name, payload)

    plan = solver.solve(REFUSE_SPEC)
    payload = plan.to_dict()
    payload["_source"] = {"prompt": "a flux capacitor and an oled display",
                           "spec": REFUSE_SPEC}
    write("plan_refuse.json", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
