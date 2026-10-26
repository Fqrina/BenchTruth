# BenchTruth

**A hardware build verifier that refuses impossible builds — with the physics, the cost,
and the fix.**

Anyone can prompt a chatbot for a wiring diagram. BenchTruth is the one that tells you
your build **cannot work**: it names the violated rule, explains the physics in physical
terms, prices each way out, and then proves the corrected build.

```
user prompt
   → Muse Spark 1.3  → project_spec.json      (intent only: no pins, no code, no geometry)
   → SOLVER          → plan.json              (pins, I2C, power, mechanical, violations)
   → renderers       → artifacts              (BOM, wiring table, .ino, diagram.json, plate, drill template)
   → compile gate → simulation → teaching panel
```

**The models do what models are good at; the deterministic engine decides what is true.**

---

## The refusal card, verbatim

```
❌ CANNOT BUILD AS SPECIFIED
esp32-devkitc-v4 · 5 signals

R17: MQ-2 gas/smoke sensor (LPG, methane, smoke) analog output can exceed the 3.3 V ADC range
  Why it matters: The ADC saturates at 3.3 V. Anything above that reads as full-scale
  forever -- a silent, wrong measurement.
  A. Add a resistor divider (measure the output first) · Rp 3,000–10,000 · 2 resistors
  B. Power the sensor from 3.3 V if it allows · - · move one jumper

R12: 250 mA of loads must run off the board itself
  Why it matters: Servos, motors and LED strips draw stall current far beyond the 3V3
  regulator. The board will brown out and reset.
  A. Add a separate 5 V supply with a common ground · Rp 40,000–120,000 · 2 extra wires
  B. Use a PCA9685 driver on its own supply · Rp 18,000–45,000 · +3 solder points
  C. Allow an external supply · - · free

R11: 3V3 rail needs 540 mA but the board is rated 300 mA
  Why it matters: Breakdown on the 3V3 rail: SG90 micro servo 250 mA, 0.96in SSD1306
  OLED 20 mA, Piezo buzzer 30 mA, WiFi TX reserve 240 mA. Over budget by 240 mA.
  A. Move the load to VIN (5 V) with a common ground · - · 2 extra wires
  B. Add an external supply · Rp 40,000–120,000 · 1 supply
  C. Drop the heaviest peripheral · - · edit the request

Pick one and I will rebuild, recompile and re-simulate.
```

Every pin that survives to the plan is justified: `MQ-2 → GPIO 33 (ADC1)`,
`SSD1306 → 21/22 (shared I²C bus)`, `SG90 → GPIO 32 (PWM/LEDC capable)`.

---

## The verification corpus

`eval/cases.json` holds 20 mutually conflicting specs; `eval/golden_specs.json` holds a
hand-written spec for each. The harness never calls a model, so the number measures the
solver and nothing else.

| Case | Conflict | Rule | Verdict |
|---|---|---|---|
| C01 | two I²C devices, one address | R8 | OFFER |
| C02 | 5 V part into a 3.3 V pin | R10 | OFFER |
| C03 | servo on the logic rail | R10, R12, R11 | OFFER |
| C04 | analog read on ADC2 with WiFi | R5 | FIXED |
| C05 | output on an input-only GPIO | R1 | FIXED |
| C06 | signal on a flash-reserved GPIO | R2 | FIXED |
| C07 | two peripherals on one pin | R7 | FIXED |
| C08 | a part that is not in the database | R15 | REFUSE |
| C09 | inductive load, no flyback | R10, R13 | OFFER |
| C10 | motor on the 3V3 rail | R10, R12, R11 | OFFER |
| C11 | LED strip, no external supply | R12 | OFFER |
| C12 | parts do not fit the envelope | R9, R14, R16 | OFFER |
| C13 | OLED + IMU, valid | — | BUILD |
| C14 | I²C bus with no pull-ups | R9 | OFFER |
| C15 | six servos from one board | R9, R12, R11 | OFFER |
| C16 | 1-Wire bus with no pull-up | R9 | OFFER |
| C17 | 5 V part on a 3 V rail | R10 | OFFER |
| C18 | signal on a boot-strapping pin | R3 | FIXED |
| C19 | temperature + IMU, valid | — | BUILD |
| C20 | dimensions from a clone, not measured | R16 | WARN |

**20/20 correct verdicts, 0 false refusals on the two positive controls.** Regenerate
with `python eval/run_eval.py`; it rewrites `eval/RESULTS.md`.

---

## What BenchTruth is made of

| Layer | What it does | Status |
|---|---|---|
| **Solver** | The deterministic engine. Pin allocation, I²C resolution, rail budgets, mechanical fit. 17 rules, each with a severity, an autofix policy, the physics, and costed options. | **working** |
| **Parts database** | 18 parts with dated price bands, electrical limits, dimensions, and a real source link for every entry. | **working** |
| **Verification corpus** | 20 conflict cases, hand-written golden specs, a deterministic harness. No LLM in the loop. | **working** |
| **Spec layer** | A prompt becomes a schema-validated intent document. It never names a pin, writes code, or draws geometry. Retries with the validation error fed back, then falls back to a local parser so it works with no key. | **working** |
| **Renderers** | BOM with dated price bands, wiring table, Arduino sketch, Wokwi `diagram.json`. | building |
| **Compile gate** | `arduino-cli` compiles the generated sketch. A plan is only approved if the code builds. | building |
| **Simulation** | the approved build, running in a browser. | building |
| **API + web UI** | prompt → spec → plan → refusal card → pick a fix → rebuild. | planned |
| **Teaching panel** | diagnostics derived from the *validated plan* — this pin, this address, this supply. | planned |
| **Silicon receipt** | the generated firmware, flashed to a real board, running. | planned |
| **Open-weight route** | the spec/explain layer on `meta-models/muse-spark-open-1026`. | planned |
| CAD + physical build | OpenSCAD plate, drill template, a breadboard build. Stretch — the demo does not depend on it. | stretch |

---

## Build log

What was built, day by day, with the reason it mattered:
[`docs/BUILD_LOG.md`](docs/BUILD_LOG.md). The first entry is the foundation — the
contracts, the 17 rules, the parts database, the engine, and the verification corpus.

---

## Run it

No install required to check the engine — it is pure standard library.

```bash
python eval/run_eval.py        # 20 conflict cases, expected 20/20
python tests/run_tests.py      # unit tests, expected 19/19
python scripts/validate_db.py  # the data contracts
```

Full product (once built) — two commands:

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload   # then open http://127.00.0.1:8000
```

It works **offline** with `MODEL_PROVIDER=mock` (the default). No API key is needed for
the refusal demo, the eval, or the tests — copy `.env.example` to `.env` for the real
Meta model.

---

## Honest limitations

- The parts database is **18 parts** and **none of them is `measured` yet** — the
  dimensions are datasheet or clone-typical. We mark that honestly: rule R16 warns on
  any build that needs a mount, and `scripts/validate_db.py` reports every part still
  missing a real source URL. The tool refuses to guess (R15) rather than inventing a
  part. Re-measuring the database is the largest single piece of work outstanding.
- Prices are **dated bands from listings**, not live commerce. Each band carries the
  date it was recorded.
- Simulation is **behavioural, not electrical**: it shows the fixed build working, but
  the power and level numbers come from the solver's arithmetic, not from the
  simulator.
- The parts database covers a small slice of electronics. It is a moat, not an
  encyclopedia.

---

## Repository map

| Path | What |
|---|---|
| `AGENTS.md` | how to work on this project (read first) |
| `docs/OFFICIAL_RULES.md` | the participant guide, extracted — **normative** |
| `docs/BUILD_LOG.md` | what was built, day by day |
| `docs/DEMO_SCRIPT.md` | the shot list for the 3-minute video |
| `CONTEXT.md` | why it exists, the competitive landscape, the positioning |
| `PLAN.md` | the timeline and the day-by-day guide |
| `TASKS.md` | the work list with acceptance criteria |
| `SPEC.md` | normative data contracts: spec, parts DB, rules, verdicts |
| `ruleset.md` | R1–R17 in prose, with the refusal template |
| `parts/` | `parts_db.json` + `signal_profiles.json` + their schemas |
| `spec/` | `project_spec.schema.json` — the only thing the LLM may produce |
| `eval/` | `cases.json`, `golden_specs.json`, `run_eval.py`, `RESULTS.md` |
| `benchtruth/` | the deterministic constraint engine |
| `tests/` | `test_solver.py` + `run_tests.py` (no dependencies needed) |
| `scripts/` | `validate_db.py` — the CI gate for the data contracts |

## Licence

MIT — see `LICENSE`.
