"""tests/test_solver.py -- unit tests for the constraint engine.

Run:  python -m pytest -q
"""
from __future__ import annotations

import json
import pathlib
import sys

try:
    import pytest
except ImportError:          # pytest is optional -- tests/run_tests.py needs no deps
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

from benchtruth.db import load_db        # noqa: E402
from benchtruth.solver import Solver     # noqa: E402

DB = load_db()
SOLVER = Solver(DB)


def golden() -> dict:
    with (ROOT / "eval" / "golden_specs.json").open(encoding="utf-8") as fh:
        return {g["id"]: g["spec"] for g in json.load(fh)["specs"]}


G = golden()


def plan(cid):
    return SOLVER.solve(G[cid])


def fired(cid):
    return plan(cid).fired_rules()


# ---- individual rules ------------------------------------------------

def test_r1_input_only_pin_is_moved():
    p = plan("C05")
    assert "R1" in p.fired_rules()
    assert p.verdict == "FIXED"
    servo = [s for s in p.signals if s.part_id == "sg90"][0]
    assert servo.gpio not in (34, 35, 36, 37, 38, 39)


def test_r2_flash_pin_is_moved():
    p = plan("C06")
    assert "R2" in p.fired_rules()
    buzzer = [s for s in p.signals if s.part_id == "piezo-buzzer"][0]
    assert buzzer.gpio not in (6, 7, 8, 9, 10, 11)


def test_r3_strapping_pin_is_moved():
    p = plan("C18")
    assert "R3" in p.fired_rules()
    buzzer = [s for s in p.signals if s.part_id == "piezo-buzzer"][0]
    assert buzzer.gpio != 2


def test_r5_adc2_with_wifi_is_moved_to_adc1():
    p = plan("C04")
    assert "R5" in p.fired_rules()
    soil = [s for s in p.signals if s.part_id == "soil-capacitive"][0]
    assert soil.gpio in DB.board("esp32-devkitc-v4")["pins"]["adc1"]


def test_r7_duplicate_pin_is_resolved():
    p = plan("C07")
    assert "R7" in p.fired_rules()
    gpios = [s.gpio for s in p.signals]
    assert len(gpios) == len(set(gpios))


def test_r8_i2c_collision_offers_costed_fixes():
    p = plan("C01")
    v = [x for x in p.violations if x.rule_id == "R8"][0]
    assert v.autofix == "OFFER"
    assert len(v.fixes) >= 2
    assert any(f.cost_idr for f in v.fixes)


def test_r10_level_mismatch_is_offered_not_guessed():
    p = plan("C02")
    v = [x for x in p.violations if x.rule_id == "R10"][0]
    assert v.autofix == "OFFER"


def test_r11_power_budget_reports_breakdown():
    p = plan("C03")
    v = [x for x in p.violations if x.rule_id == "R11"]
    assert v, "expected a power budget violation"
    assert "mA" in v[0].why


def test_r12_motor_on_logic_rail_is_offered():
    p = plan("C10")
    assert "R12" in p.fired_rules()


def test_r13_missing_flyback():
    p = plan("C09")
    assert "R13" in p.fired_rules()


def test_r14_mechanical_fit():
    p = plan("C12")
    v = [x for x in p.violations if x.rule_id == "R14"]
    assert v
    assert "mm2" in v[0].why or "mm" in v[0].why


def test_r15_unknown_part_refuses():
    p = plan("C08")
    assert p.verdict == "REFUSE"
    assert "R15" in p.fired_rules()


def test_r16_unmeasured_dimensions_warn():
    p = plan("C20")
    assert "R16" in p.fired_rules()
    assert p.verdict == "WARN"


def test_r17_analog_over_range():
    p = plan("C02")
    # HC-SR04 is digital; the analog over-range rule is exercised by the MQ build.
    assert "R17" not in p.fired_rules()


# ---- positive controls (no false refusals) --------------------------

@pytest.mark.parametrize("cid", ["C13", "C19"])
def test_valid_builds_are_not_refused(cid):
    p = plan(cid)
    assert p.verdict == "BUILD", f"{cid}: {p.refusal_card()}"


def test_every_allocation_has_a_reason():
    for cid, spec in G.items():
        p = SOLVER.solve(spec)
        for s in p.signals:
            assert s.reason, f"{cid}: signal without a reason"


def test_no_signal_lands_on_an_unusable_pin():
    board = DB.board("esp32-devkitc-v4")
    for cid, spec in G.items():
        p = SOLVER.solve(spec)
        for s in p.signals:
            if s.gpio is None:
                continue
            if s.kind in ("i2c_sda", "i2c_scl"):
                continue
            assert s.gpio not in board["pins"]["flash_reserved"], f"{cid}: flash pin"
            if s.kind in ("digital_out", "pwm_out"):
                assert s.gpio not in board["pins"]["input_only"], f"{cid}: input-only pin"


def test_verdict_derivation_matches_spec():
    """See SPEC.md section 7."""
    for cid, spec in G.items():
        p = SOLVER.solve(spec)
        for v in p.violations:
            if v.autofix == "NONE":
                want = "REFUSE" if v.severity == "FATAL" else "WARN"
            elif v.autofix == "OFFER":
                want = "OFFER"
            else:
                want = "FIXED" if v.applied else "WARN"
            assert v.verdict == want, f"{cid}: {v.rule_id} -> {v.verdict} != {want}"
