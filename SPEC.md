# SPEC.md — data contracts (authoritative)

Anything in this file is **normative**. Code must match it. If they disagree, fix the
code and update this file in the same commit.

---

## 1. Concept of a build

```
user prompt
   → Muse Spark 1.3 → project_spec.json      (intent only; schema-validated)
   → SOLVER (deterministic) → plan.json      (pins, addresses, power, mechanical, violations)
   → renderers → artifacts                   (BOM, wiring table, .ino, diagram.json, plate STL, drill SVG)
   → compile gate → simulation → teaching panel → (SAM 3.1 build-check)
```

**The LLM never assigns pins.** It states which *signals* each peripheral needs. The
solver allocates. If a user explicitly asks for a pin ("put the servo on GPIO 34"), the
LLM records it as a **requested pin**, the solver honours the request, and the rules
judge it — which is how R1/R2/R5/R6/R7 become reachable and testable.

---

## 2. `project_spec.json` (LLM output)

Validated against `spec/project_spec.schema.json` (JSON Schema draft-07).
Key additions over the original draft:

| Field | Type | Meaning |
|---|---|---|
| `peripherals[].signals_needed[]` | `{signal, direction, note}` | What the MCU must provide. **Never a pin number.** |
| `peripherals[].power` | `"3v3" \| "5v" \| "external" \| "auto"` | Optional. If the user says "power it from 5 V", record it here. |
| `requested_pins[]` | `{part_id, signal, gpio}` | Optional. Only when the user names a specific pin. The solver honours then judges. |
| `constraints.i2c_pullup_mode` | `"auto" \| "external" \| "internal"` | Whether I2C pull-ups are onboard, external, or the board's internal ones. |
| `constraints.mechanical.mount_style` | `"free" \| "breadboard" \| "grid_plate" \| "enclosure"` | **Default `"free"`** (no mechanical output). `grid_plate` and `enclosure` trigger the fit-check and the dimension-uncertainty rule. |
| `constraints.mechanical.max_envelope_mm` | `{w, d, h}` | Plate/envelope budget. |
| `constraints.power.external_supply_allowed` | bool | If false, everything must run off the board → R11/R12 fire. |
| `constraints.connectivity[]` | `"wifi" \| "ble" \| ...` | `"wifi"` makes ADC2 unusable (R5). |

---

## 3. `parts/parts_db.json` (curated ground truth; the moat)

Units: **mm, mA, V, IDR**. Required per part:

```
id, name, source_url, price_idr_min, price_idr_max, price_date, pack_size,
logic_v, supply_v_min, supply_v_max,
current_idle_ma, current_peak_ma,
iface{type, pins[], i2c_addr_default, i2c_addr_options[]},
dims{w_mm, d_mm, h_mm, tolerance_mm, shape_class},
mount{holes[] {x_mm,y_mm,dia_mm}, standoff_mm, header_pitch_mm},
keepouts[] {side, w_mm, d_mm},
needs_level_shift, needs_external_supply, needs_flyback,
confidence, notes
```

- `shape_class` ∈ `rect | cyl | L` — **do not force everything square**.
- **Datum convention (all parts):** hole coords and keepouts are relative to the
  **bottom-left corner of the body bounding box**, X right, Y away from the viewer, Z up.
  One convention for the whole DB or CAD cannot compose.
- `confidence` ∈ `datasheet | measured | clone-typical | community`. `measured` = your caliper.
  `clone-typical` = copied from a visually identical clone — **must be re-measured**.
- `null` for a required value ⇒ the part is **incomplete** ⇒ solver refuses (R15).
- `db_version` bumped on every change; the plan records the DB version that produced it.
- CI validates the DB against `parts/db.schema.json` on every commit.

## 4. `parts/signal_profiles.json` (per-part electrical interface)

Kept separate from the mechanical/price DB so both can evolve independently.

```json
{
  "ssd1306-096": {
    "default_signals": [{"signal": "i2c", "direction": "bidirectional"}],
    "power_rail": "3v3",
    "pullups_needed": false,
    "onboard_pullups": true,
    "library": "Adafruit_SSD1306",
    "wokwi_name": "wokwi-ssd1306",
    "vision_aliases": ["oled display", "oled screen", "ssd1306"],
    "keywords": ["oled", "display", "screen"]
  }
}
```

- `default_signals` kinds: `digital_in | digital_out | pwm_out | analog_in | i2c | spi | onewire`
- `power_rail`: `3v3` (logic rail) | `5v` (VIN) | `external` (own supply, e.g. servos, LED strips)
- `onboard_pullups`: does the module already have I2C pull-ups?
- `wokwi_name`: the Wokwi part name, or `null` if none exists (then the part is excluded
  from simulation and the plan says so).
- `vision_aliases`: text prompts for SAM 3.1.

## 5. Board profile (`parts_db.json → boards[]`)

```json
{ "id": "esp32-devkitc-v4",
  "pins": { "input_only": [...], "flash_reserved": [...], "strapping": [...],
            "usb_native": [...], "uart0": [...], "boot": [...],
            "adc1": [...], "adc2": [...], "dac": [...], "touch": [...],
            "pwm_ledc": [...], "i2c_default": {...}, "spi_vspi": {...} },
  "rails": { "3v3": {"recommended_max_ma": 300, "absolute_max_ma": 500},
             "5v_vin": {"recommended_max_ma": 500} },
  "dims": {...} }
```

`WIFI_RESERVE_MA = 240` is subtracted from the 3V3 rail (WiFi TX bursts).

---

## 6. Rules (IDs are stable and shared with `ruleset.md`)

| ID | Name | Severity | Autofix | Fires when |
|---|---|---|---|---|
| R1 | PIN_OUT_ONLY | FATAL | AUTO | output signal on an input-only GPIO |
| R2 | PIN_FLASH_RESERVED | FATAL | AUTO | signal on a flash-reserved GPIO |
| R3 | PIN_STRAPPING | WARN | AUTO | signal on a boot-strapping GPIO → solver moves it |
| R4 | PIN_UART_BOOT | WARN | NONE | signal on GPIO 0/1/3 (boot log / USB serial) |
| R5 | ADC2_WIFI_CONFLICT | FATAL | AUTO | analog read on ADC2 while WiFi is enabled |
| R6 | ANALOG_NOT_ADC | FATAL | AUTO | analog read on a non-ADC pin |
| R7 | PIN_DOUBLE_ASSIGNED | FATAL | AUTO | two signals on one GPIO |
| R8 | I2C_ADDR_COLLISION | FATAL | OFFER | two devices, one bus, same address |
| R9 | I2C_MISSING_PULLUP | WARN | OFFER | I2C bus with no pull-ups, or internal pull-ups requested, or a 1-Wire/DHT bus with no pull-up |
| R10 | LEVEL_MISMATCH | FATAL | OFFER | a 5 V output drives a 3.3 V pin, or a part is powered outside its supply range |
| R11 | RAIL_POWER_BUDGET | FATAL | OFFER | rail demand exceeds the rail's recommended capacity |
| R12 | MOTOR_ON_LOGIC_RAIL | FATAL | OFFER | a part that needs its own supply is asked to run off the board |
| R13 | MISSING_FLYBACK | FATAL | OFFER | inductive load without a flyback path |
| R14 | MECH_FIT | FATAL | OFFER | footprints do not fit the requested envelope |
| R15 | PART_UNKNOWN | FATAL | NONE | the part is not in the DB / data incomplete |
| R16 | DIM_UNMEASURED | WARN | NONE | dimensions are `clone-typical`, not `measured`, and a mount is being produced |
| R17 | ANALOG_OVER_RANGE | FATAL | OFFER | a 5 V analog source would exceed the 3.3 V ADC range |

**Autofix semantics**
- `AUTO` — the solver changes something (reassigns a pin) and reports it.
- `OFFER` — the solver must present costed options (from the parts DB) and wait.
- `NONE` — refuse; no way out.

## 7. Verdict derivation (normative)

Each violation yields a verdict, derived from its autofix policy and whether the
autofix was applied:

| Autofix | Applied? | Verdict |
|---|---|---|
| NONE | — | `REFUSE` if severity is FATAL, else `WARN` |
| OFFER | — | `OFFER` |
| AUTO | yes | `FIXED` |
| AUTO | no | `WARN` |

Overall verdict = the most severe of: `REFUSE` > `OFFER` > `FIXED` > `WARN` > `BUILD`
(no violations ⇒ `BUILD`).

Implemented in `benchtruth/solver.py` → `Solver._verdict`, and enforced by
`tests/test_solver.py::test_verdict_derivation_matches_spec`.

## 8. `plan.json` (solver output)

```json
{
  "db_version": "0.1",
  "board": "esp32-devkitc-v4",
  "verdict": "OFFER",
  "signals": [{ "part_id": "sg90", "kind": "pwm_out", "gpio": 13,
                "reason": "LEDC PWM capable, not strapping, not USB/UART0",
                "requested": false }],
  "i2c": { "bus": "i2c0", "sda": 21, "scl": 22,
           "devices": [{ "part_id": "ssd1306-096", "address": "0x3C" }] },
  "power": { "rails": [{ "name": "3v3", "peak_ma": 270, "capacity_ma": 300 }] },
  "mech": { "mount_style": "grid_plate", "cells": [ ... ], "envelope": { "w": 120, "d": 80 } },
  "violations": [{ "rule_id": "R11", "severity": "FATAL", "autofix": "OFFER",
                   "headline": "...", "why": "...",
                   "fixes": [{ "id": "A", "label": "...", "cost_idr": [8000, 15000] }] }],
  "artifacts": { "bom": "...", "wiring_table": "...", "firmware": "...",
                 "diagram_json": "...", "plate_stl": "...", "drill_svg": "..." },
  "notes": ["simulation excludes mq2: no Wokwi part exists"]
}
```

Every `violation.fixes` entry must carry a cost band from the parts DB when it implies a
part, and a human `effort` string. The refusal card renders these as A/B/C choices.

## 9. The refusal card format

```
❌ CANNOT BUILD AS SPECIFIED
{board} · {n} peripherals

{rule_id}: {headline}

Why it matters:
  {why}

A. {fix label} · {cost} · {effort}
B. ...
C. ...

Pick one (A/B/C) and I will rebuild, recompile and re-simulate.
```

## 10. Eval contract

- `eval/cases.json` — 20 cases, each with `expected_rule` (string or list) and
  `expected_verdict`.
- `eval/golden_specs.json` — hand-written specs, one per case id. **The solver eval must
  not call the LLM** — it measures the solver, deterministically.
- `eval/run_eval.py` — prints `passed/total` and any mismatches. Exit code 1 on failure.
- A second, separate number may be reported for end-to-end LLM spec generation
  ("valid spec on N/20 prompts") — never mix it with the solver number.
- Target: **20/20 solver verdicts correct, and 0 false refusals on the positive controls**
  (C13, C19, and the other BUILD case).
