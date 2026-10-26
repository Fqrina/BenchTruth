"""benchtruth.solver — the deterministic build verifier.

This is the moat. It reads only:
  * a board profile (pin capabilities, rails)
  * a parts DB with a real source, a dated price band and a measurement confidence
    for every part (prices, electrical limits, mechanical dimensions)
  * a signal profile per part (which signals it needs)

It never asks a model anything. It produces a Plan containing:
  * pin allocations, each with a human-readable reason
  * I2C address resolution
  * rail power budgets
  * a mechanical layout + fit check
  * violations (R1..R17), each with costed fixes

Verdict derivation is normative -- see SPEC.md section 7.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

WIFI_RESERVE_MA = 240
GRID_CLEARANCE_MM = 5
PACKING_EFFICIENCY = 0.7

# Preference order for pin allocation (lower index = nicer pin).
PREF_ORDER = [13, 14, 27, 26, 25, 33, 32, 23, 18, 19, 22, 21, 16, 17, 4, 5, 15, 12, 2, 0,
               35, 36, 37, 38, 39]

VERDICT_ORDER = ["REFUSE", "OFFER", "FIXED", "WARN", "BUILD"]

BUS_SIGNALS = {"i2c_sda", "i2c_scl", "spi_sck", "spi_miso", "spi_mosi", "spi_ss"}

SIGNAL_EXPANSION = {
    "i2c": ["i2c_sda", "i2c_scl"],
    "spi": ["spi_sck", "spi_miso", "spi_mosi", "spi_ss"],
}


def _worse(a: str, b: str) -> str:
    return a if VERDICT_ORDER.index(a) <= VERDICT_ORDER.index(b) else b


def _console_safe(text: str, plain: bool = False) -> str:
    """Keep the emoji when the terminal can encode them, fall back to ASCII if not.

    A Windows console with the default code page cannot encode U+274C, and the
    refusal card is exactly the thing you do not want to crash on.
    """
    ascii_form = (text.replace("❌", "[X] ").replace("✅", "[OK] ")
                      .replace("—", "--").replace("–", "-")
                      .replace("·", "-").replace("µ", "u"))
    if plain:
        return ascii_form
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return ascii_form
    return text


@dataclass
class Fix:
    id: str
    label: str
    cost_idr: Optional[tuple] = None
    effort: str = ""
    part_id: Optional[str] = None

    def render(self) -> str:
        cost = "-"
        if self.cost_idr:
            cost = f"Rp {self.cost_idr[0]:,}–{self.cost_idr[1]:,}"
        effort = f" · {self.effort}" if self.effort else ""
        return f"{self.id}. {self.label} · {cost}{effort}"


@dataclass
class Violation:
    rule_id: str
    severity: str
    autofix: str
    headline: str
    why: str = ""
    fixes: list = field(default_factory=list)
    applied: bool = False
    verdict: str = "WARN"


@dataclass
class Signal:
    part_id: str
    kind: str
    direction: str = "out"
    gpio: Optional[int] = None
    reason: str = ""
    requested: bool = False
    bus: Optional[str] = None


@dataclass
class Plan:
    board_id: str = ""
    db_version: str = ""
    verdict: str = "BUILD"
    signals: list = field(default_factory=list)
    i2c: dict = field(default_factory=dict)
    power: dict = field(default_factory=dict)
    mech: dict = field(default_factory=dict)
    violations: list = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    def fired_rules(self) -> list:
        return [v.rule_id for v in self.violations]

    def refusal_card(self, plain: bool = False) -> str:
        """The refusal card, as text.

        The emoji are the point in a browser, but a Windows console often cannot
        encode them, so the text falls back to ASCII markers when it has to.
        """
        if self.verdict == "BUILD":
            return _console_safe("✅ BUILD OK — every constraint satisfied.", plain)
        blocks = [f"❌ CANNOT BUILD AS SPECIFIED\n{self.board_id} · {len(self.signals)} signals"]
        for v in self.violations:
            if v.verdict in ("WARN",) and self.verdict in ("REFUSE", "OFFER"):
                continue
            blocks.append(f"{v.rule_id}: {v.headline}")
            if v.why:
                blocks.append(f"  Why it matters: {v.why}")
            for fx in v.fixes:
                blocks.append(f"  {fx.render()}")
        if self.verdict in ("REFUSE", "OFFER"):
            blocks.append("Pick one and I will rebuild, recompile and re-simulate.")
        return _console_safe("\n".join(blocks), plain)


class Solver:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # public entry point
    # ------------------------------------------------------------------
    def solve(self, spec: dict) -> Plan:
        board = self.db.board(spec["board"])
        plan = Plan(board_id=spec["board"], db_version=self.db.version)
        viol: list = []

        # --- expand peripherals into signals --------------------------
        signals, unknown = self._expand(spec)
        if unknown:
            for name in unknown:
                viol.append(Violation(
                    rule_id="R15", severity="FATAL", autofix="NONE",
                    headline=f"'{name}' is not in the verified parts database",
                    why="Its pinout, voltage, current and dimensions are unknown. "
                        "A build around an unverified part is a guess, and guesses "
                        "burn boards.",
                    fixes=[Fix("A", f"Add '{name}' to the database (measure it first)",
                               None, "1 evening"),
                           Fix("B", "Use a part that is already in the database",
                               None, "swap in the plan")],
                    verdict="REFUSE"))
            plan.violations = viol
            plan.verdict = "REFUSE"
            return plan

        plan.signals = signals
        used: set = set()
        board_pins = board["pins"]
        wifi = "wifi" in (spec.get("constraints", {}).get("connectivity") or [])

        # --- allocate ------------------------------------------------
        self._allocate(signals, board, used, spec, plan, viol)

        # --- rules ----------------------------------------------------
        self._rule_pins(signals, board, used, wifi, viol)
        self._rule_i2c(spec, signals, board, viol, plan)
        self._rule_pullups(spec, signals, viol)
        self._rule_level(spec, signals, board, viol)
        self._rule_power(spec, signals, board, wifi, viol, plan)
        self._rule_flyback(spec, signals, viol)
        self._rule_mech(spec, signals, board, viol, plan)
        self._rule_dims(spec, signals, viol)

        for v in viol:
            v.verdict = self._verdict(v)
        plan.violations = viol
        verdict = "BUILD"
        for v in viol:
            verdict = _worse(verdict, v.verdict)
        plan.verdict = verdict
        plan.notes.append(
            "Rule ids: " + ", ".join(sorted({v.rule_id for v in viol})) if viol
            else "No constraint violations.")
        return plan

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _expand(self, spec: dict):
        signals, unknown = [], []
        for p in spec.get("peripherals", []):
            pid = p.get("part_id", "")
            rec = self.db.part(pid)
            if rec is None:
                unknown.append(pid.split(":")[-1] or pid)
                continue
            prof = self.db.profile(pid)
            count = int(p.get("count", 1))
            kinds = p.get("signals_needed") or prof.get("default_signals") or []
            multiplicity = prof.get("signal_multiplicity", "per_unit")
            n = count if multiplicity == "per_unit" else 1
            for k in kinds:
                kind = k.get("signal", "digital_out")
                for expanded in SIGNAL_EXPANSION.get(kind, [kind]):
                    for _ in range(n):
                        signals.append(Signal(pid, expanded, k.get("direction", "out")))
        # honour explicitly requested pins
        for rp in spec.get("requested_pins", []):
            for s in signals:
                if s.part_id == rp.get("part_id") and s.kind == rp.get("signal"):
                    s.gpio = int(rp["gpio"])
                    s.requested = True
                    s.reason = "user requested"
                    break
        return signals, unknown

    def _caps(self, board: dict, g: int) -> set:
        p = board["pins"]
        if g in p.get("flash_reserved", []):
            return set()
        caps = {"in"}
        if g not in p.get("input_only", []):
            caps.add("out")
        if g in p.get("adc1", []):
            caps.update({"adc1", "analog_in"})
        if g in p.get("adc2", []):
            caps.update({"adc2", "analog_in"})
        if g in p.get("pwm_ledc", []):
            caps.add("pwm")
        return caps

    def _score(self, board: dict, g: int) -> int:
        p = board["pins"]
        s = 0
        if g in p.get("strapping", []):
            s += 100
        if g in p.get("uart0", []) or g in p.get("boot", []):
            s += 80
        if g in p.get("usb_native", []):
            s += 60
        if g in p.get("adc2", []):
            s += 10
        s += PREF_ORDER.index(g) if g in PREF_ORDER else 50
        return s

    def _candidates(self, board, used, need: set, exclude_input_only=False):
        out = []
        pool = list(dict.fromkeys(list(board["pins"].get("pwm_ledc", [])) +
                                  list(board["pins"].get("adc1", [])) +
                                  list(range(0, 40))))
        for g in sorted(pool):
            if g in used or g in board["pins"].get("flash_reserved", []):
                continue
            caps = self._caps(board, g)
            if not need.issubset(caps):
                continue
            if exclude_input_only and g in board["pins"].get("input_only", []):
                continue
            out.append(g)
        out.sort(key=lambda g: self._score(board, g))
        return out

    def _allocate(self, signals, board, used, spec, plan, viol):
        p = board["pins"]
        bus_pins: dict = {}
        self._bus_pins = bus_pins      # same object; filled in below, read by _rule_i2c
        order = (["i2c_sda", "i2c_scl", "spi_sck", "spi_miso", "spi_mosi", "spi_ss"] +
                 ["analog_in", "pwm_out", "digital_in", "digital_out"])
        for kind in order:
            group = [s for s in signals if s.kind == kind]
            if not group:
                continue
            if kind in ("i2c_sda", "i2c_scl", "spi_sck", "spi_miso", "spi_mosi", "spi_ss"):
                bus = "i2c" if kind.startswith("i2c") else "spi"
                names = ["sda", "scl"] if bus == "i2c" else ["sck", "miso", "mosi", "ss"]
                default = (p.get("i2c_default") or {}) if bus == "i2c" else (p.get("spi_vspi") or {})
                if bus not in bus_pins:
                    bus_pins[bus] = {}
                    for nm in names:
                        chosen = None
                        for s2 in signals:
                            if s2.kind == f"{bus}_{nm}" and s2.gpio is not None:
                                chosen = s2.gpio
                                break
                        if chosen is None and default.get(nm) is not None:
                            d = int(default[nm])
                            if d not in used and self._caps(board, d):
                                chosen = d
                        if chosen is None:
                            need = {"out"} if bus == "i2c" else {"in", "out"}
                            cands = self._candidates(board, used, need)
                            chosen = cands[0] if cands else None
                        if chosen is not None:
                            bus_pins[bus][nm] = chosen
                            used.add(chosen)
                for s in group:
                    s.bus = bus
                    s.gpio = bus_pins[bus].get(kind.split("_", 1)[1])
                    s.reason = f"shared {bus.upper()} bus pin"
                continue
            need = {"digital_out": {"out"}, "pwm_out": {"out", "pwm"},
                    "digital_in": {"in"}, "analog_in": {"analog_in"},
                    "onewire": {"in"}}.get(kind, {"out"})
            for s in group:
                if s.gpio is not None:      # requested pin -> keep, rules will judge
                    used.add(s.gpio)
                    continue
                cands = self._candidates(board, used, need)
                if kind == "analog_in":
                    adc1 = [g for g in cands if "adc1" in self._caps(board, g)]
                    cands = adc1 or cands
                if not cands:
                    viol.append(Violation(
                        rule_id="R7", severity="FATAL", autofix="NONE",
                        headline=f"no free GPIO left for {s.part_id} ({s.kind})",
                        why="Every pin that can serve this signal is already in use.",
                        fixes=[Fix("A", "Drop one peripheral", None, "edit the request")],
                        verdict="REFUSE"))
                    continue
                pick = cands[0]
                s.gpio = pick
                used.add(pick)
                caps = self._caps(board, pick)
                bits = []
                if "pwm" in caps:
                    bits.append("PWM/LEDC capable")
                if "adc1" in caps:
                    bits.append("ADC1")
                if pick in board["pins"].get("strapping", []):
                    bits.append("boot-strapping (not ideal)")
                if pick in board["pins"].get("uart0", []):
                    bits.append("USB serial / boot log")
                s.reason = ", ".join(bits) if bits else "general purpose"

    # ---- rules ------------------------------------------------------
    @staticmethod
    def _verdict(v: Violation) -> str:
        """Normative verdict derivation -- see SPEC.md section 7."""
        if v.autofix == "NONE":
            return "REFUSE" if v.severity == "FATAL" else "WARN"
        if v.autofix == "OFFER":
            return "OFFER"
        return "FIXED" if v.applied else "WARN"

    def _rule_pins(self, signals, board, used, wifi, viol):
        p = board["pins"]
        for s in signals:
            if s.gpio is None or s.kind in BUS_SIGNALS:
                continue
            g = s.gpio
            caps = self._caps(board, g)
            need = {"digital_out": {"out"}, "pwm_out": {"out", "pwm"},
                    "digital_in": {"in"}, "analog_in": {"analog_in"},
                    "onewire": {"in"}}.get(s.kind, {"out"})
            if not need.issubset(caps):
                if g in p.get("flash_reserved", []):
                    rule = "R2"
                elif s.kind == "analog_in":
                    rule = "R6"
                else:
                    rule = "R1"
                viol.append(Violation(
                    rule_id=rule, severity="FATAL", autofix="AUTO",
                    headline=f"GPIO {g} cannot drive {s.part_id} ({s.kind})",
                    why=("GPIO 34-39 are input-only on this board: they have no output driver."
                         if rule == "R1" else
                         "GPIO 6-11 are wired to the SPI flash and are not available."
                         if rule == "R2" else
                         "This pin has no ADC channel, so an analog sensor on it reads noise."),
                    applied=True))
                self._reassign(s, board, used, need)
                continue
            if s.kind == "analog_in" and wifi and "adc2" in caps:
                viol.append(Violation(
                    rule_id="R5", severity="FATAL", autofix="AUTO",
                    headline=f"GPIO {g} is an ADC2 channel and WiFi is enabled",
                    why="ADC2 channels stop working while the radio is active, so the "
                        "reading would be silently wrong.",
                    applied=True))
                self._reassign(s, board, used, {"analog_in"}, prefer_adc1=True)
                continue
            if g in p.get("strapping", []):
                viol.append(Violation(
                    rule_id="R3", severity="WARN", autofix="AUTO",
                    headline=f"GPIO {g} is a boot-strapping pin",
                    why="Its level is sampled at reset, so the board may boot into the "
                        "wrong mode or not boot at all.",
                    applied=True))
                self._reassign(s, board, used, need)
                continue
            if g in p.get("uart0", []) or g in p.get("boot", []):
                viol.append(Violation(
                    rule_id="R4", severity="WARN", autofix="NONE",
                    headline=f"GPIO {g} is the boot log / USB serial pin",
                    why="Anything wired here can stop the board from booting and hides "
                        "the error messages you need when it does.",
                    verdict="WARN"))
        # duplicate pin detection (R7)
        seen: dict = {}
        for s in signals:
            if s.gpio is None or s.kind in BUS_SIGNALS:
                continue
            if s.gpio in seen:
                viol.append(Violation(
                    rule_id="R7", severity="FATAL", autofix="AUTO",
                    headline=f"GPIO {s.gpio} is already assigned to {seen[s.gpio]}",
                    why="Two peripherals on one pin: at least one of them will not "
                        "respond, and you will debug it for an hour.",
                    applied=True))
                need = {"digital_out": {"out"}, "pwm_out": {"out", "pwm"},
                        "digital_in": {"in"}, "analog_in": {"analog_in"},
                        "onewire": {"in"}}.get(s.kind, {"out"})
                self._reassign(s, board, used, need)
            else:
                seen[s.gpio] = s.part_id

    def _reassign(self, s, board, used, need, prefer_adc1=False):
        cands = self._candidates(board, used - {s.gpio} if s.gpio else used, need)
        if prefer_adc1:
            adc1 = [g for g in cands if "adc1" in self._caps(board, g)]
            cands = adc1 or cands
        if cands:
            s.gpio = cands[0]
            used.add(cands[0])
            s.reason = "reassigned after rule check"

    def _rule_i2c(self, spec, signals, board, viol, plan=None):
        devices = []
        for p in spec.get("peripherals", []):
            rec = self.db.part(p.get("part_id", ""))
            if not rec or rec.get("iface", {}).get("type") != "i2c":
                continue
            # A part with a count of 2 is two devices on the bus, not one -- and
            # two identical devices land on the same address.
            for _ in range(int(p.get("count", 1))):
                devices.append((p, rec))
        if not devices:
            if plan is not None:
                plan.i2c = {"bus": "i2c0", "sda": None, "scl": None, "devices": []}
            return
        assigned = []
        for p, rec in devices:
            addr = p.get("address_preference") or rec["iface"].get("i2c_addr_default")
            assigned.append((p, rec, addr))
        if plan is not None:
            bus = (getattr(self, "_bus_pins", None) or {}).get("i2c", {})
            plan.i2c = {
                "bus": "i2c0",
                "sda": bus.get("sda"),
                "scl": bus.get("scl"),
                "devices": [{"part_id": rec["id"], "name": rec["name"], "address": addr}
                            for _p, rec, addr in assigned],
            }
        seen: dict = {}
        for p, rec, addr in assigned:
            if addr in seen:
                other_p, other_rec, _ = seen[addr]
                fixes = []
                opts = rec.get("iface", {}).get("i2c_addr_options") or []
                if opts:
                    fixes.append(Fix("A", f"Re-address {rec['name']} to {opts[0]} (strap or solder jumper)",
                                     self.db.price_band(rec["id"]), "one soldered pad"))
                if self.db.has_part("tca9548a"):
                    fixes.append(Fix("B", "Add a TCA9548A I2C multiplexer",
                                     self.db.price_band("tca9548a"), "4 extra solder points"))
                fixes.append(Fix("C", f"Drop {rec['name']}", None, "free"))
                viol.append(Violation(
                    rule_id="R8", severity="FATAL", autofix="OFFER",
                    headline=f"{other_rec['name']} and {rec['name']} both want I2C address {addr}",
                    why="A bus carries one device per address. Two devices with the same "
                        "address answer at the same time and the bus locks up.",
                    fixes=fixes))
            else:
                seen[addr] = (p, rec, addr)

    def _rule_pullups(self, spec, signals, viol):
        mode = (spec.get("constraints", {}) or {}).get("i2c_pullup_mode", "auto")
        i2c_parts = [s for s in signals if s.kind.startswith("i2c")]
        if i2c_parts:
            onboard = any(self.db.profile(s.part_id).get("onboard_pullups") for s in i2c_parts)
            if mode == "internal":
                viol.append(Violation(
                    rule_id="R9", severity="WARN", autofix="OFFER",
                    headline="I2C bus using the ESP32 internal pull-ups",
                    why="Internal pull-ups are ~45 kOhm. I2C needs ~4.7 kOhm; at 45 kOhm "
                        "the bus will not meet rise-time limits and will fail at 400 kHz.",
                    fixes=[Fix("A", "Add a 4.7 kOhm pull-up pair", (2000, 8000), "2 resistors")],
                    verdict="OFFER"))
            elif not onboard:
                viol.append(Violation(
                    rule_id="R9", severity="WARN", autofix="OFFER",
                    headline="I2C bus has no pull-up resistors",
                    why="Without 4.7 kOhm pull-ups on SDA and SCL the bus cannot work.",
                    fixes=[Fix("A", "Add a 4.7 kOhm pull-up pair", (2000, 8000), "2 resistors")],
                    verdict="OFFER"))
        for s in signals:
            if s.kind in ("digital_in", "onewire") and \
                    self.db.profile(s.part_id).get("pullups_needed"):
                viol.append(Violation(
                    rule_id="R9", severity="WARN", autofix="OFFER",
                    headline=f"{self.db.part(s.part_id)['name']} needs a pull-up resistor",
                    why="The data line idles high; without a pull-up it floats and the "
                        "reading is noise.",
                    fixes=[Fix("A", "Add a 4.7-10 kOhm pull-up resistor",
                               (2000, 8000), "1 resistor")],
                    verdict="OFFER"))

    def _rule_level(self, spec, signals, board, viol):
        board_v = board.get("logic_v", 3.3)
        for p in spec.get("peripherals", []):
            rec = self.db.part(p.get("part_id", ""))
            if not rec:
                continue
            prof = self.db.profile(p.get("part_id"))
            sigs = [s for s in signals if s.part_id == p.get("part_id")]
            # supply violation
            forced = p.get("power")
            if forced and forced != "auto":
                lo = rec.get("supply_v_min", 0)
                hi = rec.get("supply_v_max", 99)
                volts = {"3v3": 3.3, "5v": 5.0, "external": 6.0}.get(forced, 0)
                if volts and not (lo - 0.2 <= volts <= hi + 0.2):
                    viol.append(Violation(
                        rule_id="R10", severity="FATAL", autofix="OFFER",
                        headline=f"{rec['name']} cannot be powered from {forced}",
                        why=f"Its supply range is {lo}-{hi} V. Feeding it {volts} V "
                            "destroys the module.",
                        fixes=[Fix("A", f"Power it from {lo} V", None, "move one jumper"),
                               Fix("B", f"Use a different part", None, "swap in the plan")]))
            # digital level mismatch
            digital = [s for s in sigs if s.kind in ("digital_in", "digital_out")]
            if digital and rec.get("logic_v", 3.3) > board_v + 0.01:
                viol.append(Violation(
                    rule_id="R10", severity="FATAL", autofix="OFFER",
                    headline=f"{rec['name']} speaks {rec['logic_v']} V logic into a {board_v} V pin",
                    why="A 5 V output into a 3.3 V pin can exceed the ESP32's input "
                        "tolerance and damage the board.",
                    fixes=[Fix("A", "Add a 4-channel BSS138 level shifter",
                               self.db.price_band("bss138-4ch"), "4 solder points"),
                           Fix("B", "Use a 3.3 V-native variant of this part",
                               self.db.price_band(rec["id"]), "swap in the plan")]))
            # analog over-range
            if any(s.kind == "analog_in" for s in sigs) and rec.get("logic_v", 3.3) > board_v + 0.01:
                viol.append(Violation(
                    rule_id="R17", severity="FATAL", autofix="OFFER",
                    headline=f"{rec['name']} analog output can exceed the {board_v} V ADC range",
                    why="The ADC saturates at 3.3 V. Anything above that reads as "
                        "full-scale forever -- a silent, wrong measurement.",
                    fixes=[Fix("A", "Add a resistor divider (measure the output first)",
                               (3000, 10000), "2 resistors"),
                           Fix("B", f"Power the sensor from {board_v} V if it allows",
                               None, "move one jumper")]))

    def _rule_power(self, spec, signals, board, wifi, viol, plan=None):
        rails = board.get("rails", {})
        cap3v3 = rails.get("3v3", {}).get("recommended_max_ma", 300)
        cap5v = rails.get("5v_vin", {}).get("recommended_max_ma", 500)
        demand3 = 0
        demand5 = 0
        external = 0
        breakdown = []
        for p in spec.get("peripherals", []):
            rec = self.db.part(p.get("part_id", ""))
            if not rec:
                continue
            prof = self.db.profile(p.get("part_id"))
            rail = prof.get("power_rail", "3v3")
            peak = float(rec.get("current_peak_ma", 0)) * int(p.get("count", 1))
            breakdown.append((rec["name"], rail, peak))
            if rail == "3v3":
                demand3 += peak
            elif rail == "5v":
                demand5 += peak
            elif rail == "external":
                external += peak
        allowed = bool((spec.get("constraints", {}).get("power", {}) or {}).get(
            "external_supply_allowed", True))
        if not allowed and external > 0:
            demand3 += external
            viol.append(Violation(
                rule_id="R12", severity="FATAL", autofix="OFFER",
                headline=f"{external:.0f} mA of loads must run off the board itself",
                why="Servos, motors and LED strips draw stall current far beyond the "
                    "3V3 regulator. The board will brown out and reset.",
                fixes=[Fix("A", "Add a separate 5 V supply with a common ground",
                           (40000, 120000), "2 extra wires"),
                       Fix("B", "Use a PCA9685 driver on its own supply",
                           self.db.price_band("pca9685"), "+3 solder points"),
                       Fix("C", "Allow an external supply", None, "free")]))
        reserve = WIFI_RESERVE_MA if wifi else 0
        total3 = demand3 + reserve
        if total3 > cap3v3:
            viol.append(Violation(
                rule_id="R11", severity="FATAL", autofix="OFFER",
                headline=f"3V3 rail needs {total3:.0f} mA but the board is rated {cap3v3} mA",
                why=("Breakdown on the 3V3 rail: " +
                     ", ".join(f"{n} {v:.0f} mA" for n, r, v in breakdown if r in ("3v3", "external")) +
                     (f", WiFi TX reserve {reserve} mA" if reserve else "") +
                     f". Over budget by {total3 - cap3v3:.0f} mA."),
                fixes=[Fix("A", "Move the load to VIN (5 V) with a common ground",
                           None, "2 extra wires"),
                       Fix("B", "Add an external supply", (40000, 120000), "1 supply"),
                       Fix("C", "Drop the heaviest peripheral", None, "edit the request")]))
        if demand5 > cap5v:
            viol.append(Violation(
                rule_id="R11", severity="FATAL", autofix="OFFER",
                headline=f"5V rail needs {demand5:.0f} mA but VIN is rated {cap5v} mA",
                why="Exceeding the USB/buck supply makes the whole board unstable.",
                fixes=[Fix("A", "Use an external 5 V supply", (40000, 120000), "1 supply")]))
        self._last_power = {"3v3": total3, "3v3_capacity": cap3v3,
                            "5v": demand5, "5v_capacity": cap5v,
                            "external": external, "breakdown": breakdown}
        if plan is not None:
            plan.power = {
                "rails": [
                    {"name": "3v3", "peak_ma": total3, "capacity_ma": cap3v3,
                     "reserve_ma": reserve},
                    {"name": "5v", "peak_ma": demand5, "capacity_ma": cap5v},
                    {"name": "external", "peak_ma": external, "capacity_ma": None},
                ],
                "breakdown": [{"part": n, "rail": r, "peak_ma": v}
                              for n, r, v in breakdown],
            }

    def _rule_flyback(self, spec, signals, viol):
        for p in spec.get("peripherals", []):
            rec = self.db.part(p.get("part_id", ""))
            if rec and rec.get("needs_flyback"):
                viol.append(Violation(
                    rule_id="R13", severity="FATAL", autofix="OFFER",
                    headline=f"{rec['name']} is inductive and needs a flyback diode",
                    why="When the coil is switched off the collapsing field produces a "
                        "voltage spike that can reset the ESP32 or destroy the pin.",
                    fixes=[Fix("A", "Add a 1N4007 diode across the coil",
                               (1000, 5000), "1 diode"),
                           Fix("B", "Use a driver board with the diodes built in",
                               self.db.price_band(rec["id"]), "swap in the plan")]))

    def _rule_mech(self, spec, signals, board, viol, plan=None):
        mech = (spec.get("constraints", {}).get("mechanical", {}) or {})
        style = mech.get("mount_style", "free")
        pitch = float(mech.get("grid_pitch_mm", 10))
        bd = board.get("dims", {})
        raw = [(f"board:{board['id']}", bd.get("w_mm", 55), bd.get("d_mm", 28))]
        for p in spec.get("peripherals", []):
            rec = self.db.part(p.get("part_id", ""))
            if not rec:
                continue
            d = rec.get("dims", {})
            raw.append((rec["name"], d.get("w_mm", 30), d.get("d_mm", 30)))

        cells, total, detail = [], 0, []
        for name, w, d in raw:
            cw = math.ceil((w + GRID_CLEARANCE_MM) / pitch) * pitch
            cd = math.ceil((d + GRID_CLEARANCE_MM) / pitch) * pitch
            total += cw * cd
            cells.append({"name": name, "w_mm": w, "d_mm": d,
                          "cell_w_mm": cw, "cell_d_mm": cd})
            detail.append(f"{name} {cw:.0f}x{cd:.0f}")

        env = mech.get("max_envelope_mm") or {"w": 200, "d": 200}
        mounting = style in ("grid_plate", "enclosure")
        capacity = float(env["w"]) * float(env["d"]) * PACKING_EFFICIENCY if mounting else None
        if plan is not None:
            plan.mech = {
                "mount_style": style,
                "grid_pitch_mm": pitch,
                "envelope": env if mounting else None,
                "cells": cells,
                "total_area_mm2": total,
                "capacity_mm2": capacity,
            }
        self._last_mech = {"mount_style": style, "grid_pitch_mm": pitch,
                           "envelope": env, "cells": detail, "total_area_mm2": total,
                           "capacity_mm2": capacity}
        if not mounting:
            return
        if total > capacity:
            viol.append(Violation(
                rule_id="R14", severity="FATAL", autofix="OFFER",
                headline=f"the parts do not fit in a {env['w']}x{env['d']} mm envelope",
                why=f"Cell areas total {total:.0f} mm2 against a usable {capacity:.0f} mm2 "
                    f"({PACKING_EFFICIENCY:.0%} packing). Cells: " + ", ".join(detail),
                fixes=[Fix("A", f"Enlarge the plate to {env['w']+30}x{env['d']+30} mm",
                           (50000, 150000), "reprint"),
                       Fix("B", "Drop one peripheral", None, "edit the request"),
                       Fix("C", "Stack one module above another", None, "spacers")]))

    def _rule_dims(self, spec, signals, viol):
        mech = (spec.get("constraints", {}).get("mechanical", {}) or {})
        if mech.get("mount_style", "free") not in ("grid_plate", "enclosure"):
            return
        unsure = []
        for p in spec.get("peripherals", []):
            rec = self.db.part(p.get("part_id", ""))
            if not rec:
                continue
            conf = (rec.get("dims", {}) or {}).get("confidence", rec.get("confidence"))
            if conf in ("clone-typical", "community"):
                unsure.append(rec["name"])
        if unsure:
            viol.append(Violation(
                rule_id="R16", severity="WARN", autofix="NONE",
                headline=f"dimensions for {', '.join(unsure)} are not measured",
                why="They come from a visually identical clone. Batch variance is real, "
                    "so the mount can be off by a millimetre or two.",
                fixes=[Fix("A", "Print with a 3 mm tolerance on the mount",
                           None, "free"),
                       Fix("B", "Measure the actual part and re-run", None, "10 minutes")],
                verdict="WARN"))


def solve_spec(spec: dict, db=None) -> Plan:
    from .db import load_db
    db = db or load_db()
    return Solver(db).solve(spec)
