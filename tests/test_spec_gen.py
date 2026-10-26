"""tests/test_spec_gen.py -- the spec layer, offline.

No network, no key. The mock provider stands in for the Meta Model API.

Run:  python -m pytest -q
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

from benchtruth.db import load_db                    # noqa: E402
from llm.providers import MockProvider, ProviderError  # noqa: E402
from llm.spec_gen import (fallback_spec, generate_spec, validate_spec)  # noqa: E402

DB = load_db()
SCHEMA = None


def _schema():
    global SCHEMA
    if SCHEMA is None:
        from llm.spec_gen import load_spec_schema
        SCHEMA = load_spec_schema()
    return SCHEMA


GOOD_SPEC = {
    "board": "esp32-devkitc-v4",
    "goal": "Watch the moisture level of a plant and open a vent when it is dry",
    "peripherals": [
        {"part_id": "ssd1306-096", "role": "screen"},
        {"part_id": "soil-capacitive", "role": "moisture probe"},
    ],
    "constraints": {"connectivity": ["wifi"], "mechanical": {"mount_style": "free"}},
}


def test_a_good_spec_validates():
    assert validate_spec(GOOD_SPEC, _schema()) == []


def test_a_bad_spec_reports_readable_problems():
    bad = {"board": "esp32-devkitc-v4", "goal": "x", "peripherals": []}
    problems = validate_spec(bad, _schema())
    assert problems, "an empty peripheral list must be rejected"
    assert any("peripherals" in p for p in problems)


def test_the_model_reply_is_validated_and_accepted():
    provider = MockProvider(fixture=GOOD_SPEC)
    spec = generate_spec("a plant monitor", provider=provider, db=DB)
    assert spec["peripherals"][0]["part_id"] == "ssd1306-096"
    assert validate_spec(spec, _schema()) == []


def test_a_malformed_reply_is_retried_then_it_falls_back():
    class Broken(MockProvider):
        def chat(self, prompt, **kwargs):
            self.calls.append(prompt)
            return "this is not JSON at all"

    provider = Broken()
    spec = generate_spec("an OLED display and a servo", provider=provider, db=DB)
    # it was retried, and then the local parser produced a usable spec
    assert len(provider.calls) > 1
    assert validate_spec(spec, _schema()) == []
    assert spec["peripherals"]


def test_a_schema_violating_reply_is_retried_with_the_error():
    class BadSchema(MockProvider):
        def chat(self, prompt, **kwargs):
            self.calls.append(prompt)
            return json.dumps({"board": "esp32-devkitc-v4", "goal": "x",
                                "peripherals": [], "constraints": {}})

    provider = BadSchema()
    spec = generate_spec("an OLED display", provider=provider, db=DB)
    assert len(provider.calls) > 1
    assert validate_spec(spec, _schema()) == []


def test_the_fallback_parser_maps_words_onto_real_parts():
    spec = fallback_spec("add an oled display and a servo and a buzzer", db=DB)
    ids = {p["part_id"] for p in spec["peripherals"]}
    assert {"ssd1306-096", "sg90"} <= ids
    assert validate_spec(spec, _schema()) == []


def test_the_fallback_parser_keeps_a_named_pin_for_the_solver_to_judge():
    spec = fallback_spec("a buzzer on gpio 34", db=DB)
    pins = spec.get("requested_pins")
    assert pins and pins[0]["gpio"] == 34
    # the solver is the one that decides whether that pin is legal
    from benchtruth.solver import Solver
    plan = Solver(DB).solve(spec)
    assert "R1" in plan.fired_rules()


def test_an_input_only_pin_is_fine_for_an_input():
    # GPIO 34 cannot drive anything, but reading from it is exactly what it is for
    spec = fallback_spec("a soil moisture probe on gpio 34", db=DB)
    assert spec.get("requested_pins")[0]["gpio"] == 34
    from benchtruth.solver import Solver
    plan = Solver(DB).solve(spec)
    assert "R1" not in plan.fired_rules()


def test_a_named_pin_is_not_given_to_a_bus_device():
    # an OLED is on the I2C bus -- its pins are the bus pins, not the user's choice
    spec = fallback_spec("an oled display on gpio 34", db=DB)
    assert not spec.get("requested_pins")


def test_the_fallback_parser_refuses_to_invent_a_part():
    spec = fallback_spec("a flux capacitor and a oled display", db=DB)
    ids = {p["part_id"] for p in spec["peripherals"]}
    assert "ssd1306-096" in ids
    assert not any(i.startswith("flux") for i in ids)
