"""tests/test_plan_contract.py -- the contract the renderers depend on.

The UI (and any other renderer) reads a plan and needs two guarantees:

  1. the plan serialises to plain JSON, exactly as SPEC.md section 8 describes
  2. every violation says what it is about, so the violation can be drawn on
     the wire it belongs to

If either of these breaks, the renderers break with it. That is why they are
tests and not a comment.
"""
from __future__ import annotations

import json
import pathlib
import sys

try:
    import pytest
except ImportError:
    class _Shim:
        class _Mark:
            @staticmethod
            def parametrize(argnames, argvalues):
                def deco(fn):
                    fn._params = (argnames, list(argvalues))
                    return fn
                return deco
        mark = _Mark()

        @staticmethod
        def parametrize(argnames, argvalues):
            def deco(fn):
                fn._params = (argnames, list(argvalues))
                return fn
            return deco
    pytest = _Shim()

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from benchtruth.db import load_db            # noqa: E402
from benchtruth.solver import Solver         # noqa: E402

DB = load_db()
SOLVER = Solver(DB)

FLAGSHIP = {
    "board": "esp32-devkitc-v4",
    "goal": "Two OLEDs, a soil probe on GPIO 25, a servo, a buzzer, WiFi, board only",
    "peripherals": [
        {"part_id": "ssd1306-096", "role": "screen 1", "count": 2},
        {"part_id": "soil-capacitive", "role": "moisture probe"},
        {"part_id": "sg90", "role": "vent servo"},
        {"part_id": "piezo-buzzer", "role": "alarm"},
    ],
    "requested_pins": [{"part_id": "soil-capacitive", "signal": "analog_in", "gpio": 25}],
    "constraints": {
        "power": {"external_supply_allowed": False},
        "connectivity": ["wifi"],
        "mechanical": {"mount_style": "free"},
    },
}

VALID_REF_KINDS = {"signal", "part", "rail", "bus", "i2c", "envelope"}


def _plan(spec):
    return SOLVER.solve(spec)


def test_the_plan_serialises_to_plain_json():
    payload = _plan(FLAGSHIP).to_dict()
    text = json.dumps(payload)          # must not raise
    back = json.loads(text)
    assert back["verdict"] == payload["verdict"]
    assert back["signals"] == payload["signals"]


def test_the_plan_carries_the_sections_the_contract_promises():
    payload = _plan(FLAGSHIP).to_dict()
    assert payload["i2c"]["sda"] == 21 and payload["i2c"]["scl"] == 22
    assert len(payload["i2c"]["devices"]) == 2
    assert payload["power"]["rails"][0]["name"] == "3v3"
    assert payload["mech"]["mount_style"] == "free"


def test_every_violation_says_what_it_is_about():
    for v in _plan(FLAGSHIP).violations:
        assert v.affected, f"{v.rule_id} has no affected refs"
        for ref in v.affected:
            assert ref["kind"] in VALID_REF_KINDS, ref


def test_the_affected_refs_point_at_real_things():
    plan = _plan(FLAGSHIP)
    part_ids = {p["id"] for p in DB.raw["parts"]}
    rails = {r["name"] for r in plan.power["rails"]}
    for v in plan.violations:
        for ref in v.affected:
            if ref["kind"] in ("part", "signal", "i2c"):
                if ref.get("part_id"):
                    assert ref["part_id"] in part_ids, ref
            if ref["kind"] == "rail":
                assert ref["name"] in rails, ref


def test_a_moved_pin_records_where_it_went():
    plan = _plan(FLAGSHIP)
    r5 = [v for v in plan.violations if v.rule_id == "R5"]
    assert r5, "R5 must fire for an ADC2 pin with WiFi on"
    ref = r5[0].affected[0]
    assert ref["kind"] == "signal"
    assert ref["gpio"] == 25          # the pin the user asked for
    assert ref["moved_to"] not in (None, 25)   # and where the solver put it
    live = [s for s in plan.signals if s.part_id == "soil-capacitive"]
    assert live and live[0].gpio == ref["moved_to"]


def test_an_address_collision_names_both_devices():
    plan = _plan(FLAGSHIP)
    r8 = [v for v in plan.violations if v.rule_id == "R8"]
    assert r8, "R8 must fire for two devices on one address"
    kinds = {ref["kind"] for ref in r8[0].affected}
    assert "bus" in kinds and "i2c" in kinds
    devices = [ref for ref in r8[0].affected if ref["kind"] == "i2c"]
    assert len(devices) == 2
    assert all(d["address"] == "0x3C" for d in devices)


def test_a_rail_budget_violation_names_the_rail_and_its_parts():
    plan = _plan(FLAGSHIP)
    r11 = [v for v in plan.violations if v.rule_id == "R11"]
    assert r11
    kinds = {ref["kind"] for ref in r11[0].affected}
    assert "rail" in kinds and "part" in kinds
    rails = [ref for ref in r11[0].affected if ref["kind"] == "rail"]
    assert rails[0]["name"] == "3v3"


def test_an_unknown_part_is_named_in_its_ref():
    spec = {"board": "esp32-devkitc-v4", "goal": "a flux capacitor",
            "peripherals": [{"part_id": "UNKNOWN:flux capacitor", "role": "cap"}],
            "constraints": {"mechanical": {"mount_style": "free"}}}
    plan = _plan(spec)
    assert plan.verdict == "REFUSE"
    r15 = [v for v in plan.violations if v.rule_id == "R15"]
    assert r15
    ref = r15[0].affected[0]
    assert ref["kind"] == "part"
    assert "flux" in (ref.get("name") or "")
