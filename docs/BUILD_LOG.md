# BUILD_LOG.md — what was built, day by day

The project started on **26 October 2026**. This log records what landed, newest
first, with the reason it mattered. It is updated in the same commit as the work it
describes, so `git log` and this file always agree.

**Event:** Meta Global AI Developer Hackathon 2026 (26 Oct – 4 Nov 2026).

---

## 26 Oct 2026 — the foundation

**The idea.** A hardware-build *verifier* that refuses. The model proposes a build
as intent; a deterministic engine decides whether it can exist, and says no — with
the rule, the physics, and the price of the way out.

**What landed:**

- **`SPEC.md`, `ruleset.md`** — the data contracts and the 17-rule constraint set
  (R1–R17), each rule with a severity, an autofix policy (`NONE` / `OFFER` / `AUTO`)
  and a refusal template. Verdict derivation is normative: `REFUSE > OFFER > FIXED >
  WARN > BUILD`.
- **`spec/project_spec.schema.json`** — the only thing the LLM is allowed to produce.
  It states intent; it never names a pin, writes code, or draws geometry.
- **`parts/parts_db.json`** — 18 parts, one board profile (`esp32-devkitc-v4`), dated
  IDR price bands, electrical limits, mechanical dimensions. `db_version 0.3`.
- **`parts/signal_profiles.json` + `parts/signal_profiles.schema.json`** — the
  electrical interface per part, with its own schema so CI can police it too.
- **`benchtruth/solver.py` + `benchtruth/db.py`** — the deterministic engine. It
  never calls a model. It allocates pins (shared buses → analog → PWM → digital in →
  out, every allocation carrying a human-readable reason), resolves I²C addresses
  with priced options, budgets each rail including the 240 mA WiFi TX reserve, lays
  out the mechanical grid and checks the fit, and emits violations with costed ways
  out.
- **`eval/`** — 20 conflict cases with hand-written golden specs and a deterministic
  harness. No LLM in the loop, so the number measures the solver and nothing else.
  **20/20 correct verdicts, 0 false refusals on the two positive controls.**
- **`tests/`** — 19 unit tests, one per rule plus the verdict derivation.
- **`scripts/validate_db.py`** — the CI gate for the data contracts. Structural
  violations fail the build; unfilled placeholders are reported loudly and fail the
  build under `--strict`.
- **`.github/workflows/ci.yml`** — CI runs the validator, the eval, the unit tests
  and a byte-compile check, with `MODEL_PROVIDER=mock` so it never needs a key.
- **`LICENSE` (MIT), `.gitignore`, `.env.example`, `pyproject.toml`, `.gitattributes`**
  — the repo scaffold.

**Fixed today:** `Plan` now actually carries the `i2c`, `power` and `mech` sections
that `SPEC.md` §8 promises — the I²C resolution was previously computed and thrown
away. The signal-profiles schema immediately caught a level shifter declaring an
empty signal list, which is correct for a passive part; the schema now says so.

### Later the same day — the spec layer

**`llm/providers.py`** — one `chat()` signature with two backends. `MetaProvider`
talks to the Meta Model API (`muse-spark-1.3`); `MockProvider` never touches the
network, so CI, judges and the offline demo all run the same code path with no key.

**`llm/spec_gen.py`** — a prompt becomes a schema-validated spec. The model's reply is
validated against `spec/project_spec.schema.json`; a malformed or invalid reply is
retried with the error fed back, up to three times, and then the **local fallback
parser** takes over. That parser maps the words in the prompt onto parts that are
actually in the database — whole-word matches only, one part per keyword, counts read
from the text ("two oled displays" → count 2) — and it never invents a part.

**Three real bugs this surfaced, all fixed:**

- `_rule_i2c` ignored `count`, so "two OLEDs" was one device on the bus and the
  address collision went unnoticed. It now expands the count, and R8 fires.
- The keyword matcher was substring-based, so "led" matched inside "oled" and the
  generic word "probe" pulled in the wrong part. Matching is now whole-word, the
  database order breaks ties, and the ambiguous keyword is gone.
- `Plan.refusal_card()` crashed on a Windows console — U+274C cannot be encoded by
  the default code page. The card now falls back to ASCII markers when the terminal
  cannot encode them.

**The flagship prompt now runs end to end, offline:**

```
prompt  → 2× OLED + soil probe on GPIO 25 + servo + buzzer, WiFi, board-only
       → spec: 4 peripherals, the probe's requested pin recorded, WiFi + board-only
       → verdict OFFER · R5 (ADC2 dies with WiFi) · R8 (two devices at 0x3C)
                R12 (servo off the logic rail) · R11 (580 mA against a 300 mA rail)
```

29 unit tests, 20/20 on the solver eval, and the data contracts clean.

**Next:** the parts database gets real sources and caliper measurements, the engine
gets rewritten into modules, and the renderers go in.

---

## 27 Oct – 4 Nov 2026

*(the build — see `PLAN.md` for the day-by-day plan, `TASKS.md` for the work list
with acceptance criteria, and `docs/BUILD_LOG.md` history above)*
