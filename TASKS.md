# TASKS.md — the work list

Format: `T-xx | owner: agent | status | depends | acceptance criteria`.

**Status values:** `done` · `building` · `planned` · `stretch` — a stretch task is
optional. It gets done if there is time; it is never a promise, and nothing depends on
it. **Do not start a task whose dependencies are open.**

---

## Tier 0 — GATE 0 (Oct 26)

- **T-01** Read the official rules. Save the rules page.
  - **Status:** done · `docs/OFFICIAL_RULES.md` is the extraction.
  - **AC:** you can answer: submission format, required fields, is any model required,
    may judges run the project, prize split, judging rubric, countries excluded.
  - **Note:** if the rules contradict `CONTEXT.md`, `CONTEXT.md` loses. Update both.
- **T-02** Scaffold the repo: `pyproject.toml`, `requirements.txt`, `.env.example`,
  `LICENSE` (MIT), `.gitignore`, `.gitattributes`, the directory tree, and a CI
  workflow that runs the validator + the eval + the tests.
  - **Status:** done · **AC:** CI is green; `MODEL_PROVIDER=mock` path exists.
- **T-03** Claim the Meta Model API credits ($150). Apply to Baseten and Modal too.
  - **Status:** planned — **the single highest-priority task in this file.** No key
    means no Meta model in the loop, and the Meta requirement is a pass/fail gate.
  - **AC:** a key is in `.env` and one live call to `muse-spark-1.3` succeeds.
- **T-04** Create the public GitHub repo and push.
  - **Status:** planned · **AC:** the URL opens in a logged-out browser, LICENSE visible.
- **T-05** Verify the free stack end to end: `arduino-cli` installs, the USB-serial
  driver is present, a sketch flashes to the board you own, a Wokwi project opens and
  runs.
  - **Status:** planned · **AC:** a real LED blinks and a Wokwi project loads. Do this
    on D0 — never discover a missing driver on demo day.

---

## Tier 1 — the engine (the spine; nothing else matters if this fails)

- **T-10** `parts/db.schema.json` + `parts/signal_profiles.schema.json` +
  `scripts/validate_db.py` + CI validation of both.
  - **Status:** done · **AC:** an incomplete part fails CI with a readable error;
    `--strict` turns the outstanding placeholders into a build failure.
- **T-11** `benchtruth/db.py` — load the parts DB, the signal profiles, the board
  profiles.
  - **Status:** done · **AC:** `db.part(id)` returns `None` for unknown ids; `db.board(id)`
    raises for unknown boards.
- **T-12** `benchtruth/solver.py` → `pins.py`: the pin allocator.
  - **Status:** planned (works today as one module) · **AC:** allocation order =
    shared buses → analog → PWM → digital in → digital out; every allocation carries a
    `reason`; requested pins are honoured.
- **T-13** → `i2c.py`: address resolver + costed fix options.
  - **Status:** planned · **AC:** a collision produces R8 with options: strap-alternative
    / TCA9548A mux / drop device, each with a price band from the DB.
- **T-14** → `power.py`: rail budget including the 240 mA WiFi reserve.
  - **Status:** planned · **AC:** a servo on the 3V3 rail produces R11 **and** R12.
- **T-15** → `mech.py`: grid layout + fit check.
  - **Status:** planned · **AC:** parts exceeding the envelope produce R14 with the
    actual numbers.
- **T-16** → `rules.py`: R1–R18, severity + autofix policy from `SPEC.md`.
  - **Status:** planned · **AC:** every rule has a unit test; IDs match `ruleset.md`.
- **T-17** → `engine.py` + `report.py`: orchestration + the refusal card.
  - **Status:** planned · **AC:** the verdict derivation matches `SPEC.md` §7 exactly;
    `Plan` carries the `i2c`, `power` and `mech` sections of `SPEC.md` §8.
- **T-18** `eval/golden_specs.json` + `eval/run_eval.py`.
  - **Status:** done (20 cases) · **AC:** `python eval/run_eval.py` prints **20/20** and
    exits 0.
- **T-19** `eval/RESULTS.md` — the table you will screenshot for the README.
  - **Status:** done · **AC:** contains the per-case rule, the expected vs the actual
    verdict, and the aggregate.
- **T-22** **R18 — refuse what cannot be proven.** A part with no simulator counterpart
  cannot be approved, because the product's promise is proof.
  - **Status:** planned · **AC:** the rule fires with a clear headline, and a build
    containing such a part is never `BUILD`.
- **T-23** Expand the corpus to 100+ cases, with more positive controls.
  - **Status:** planned · **AC:** the false-refusal count stays 0 as the corpus grows.

---

## Tier 2 — the model + the renderers (Oct 29–30)

- **T-30** `llm/providers.py` — one `chat()` signature, `meta` + `mock` backends.
  - **Status:** done · **AC:** mock returns fixtures; no network in the tests. ✓
- **T-31** `llm/spec_gen.py` — prompt → schema-validated spec, ≤3 retries with the
  validation error fed back.
  - **Status:** done · **AC:** a malformed model response is retried, then falls back
    to the local parser. ✓ The parser reads whole-word matches only, takes the count
    from the text, and never invents a part.
- **T-32** `render/wiring_table.py`, `render/bom.py`, `render/prices.py`.
  - **Status:** planned · **AC:** the BOM shows the part id, the human name, the qty,
    the price band + date, and the source link.
- **T-33** `render/firmware.py` + templates; **arduino-cli installed and compiling**.
  - **Status:** planned · **AC:** `scripts/compile_golden.sh` compiles the golden
    project with zero errors; the generated code uses exactly the pins from the plan;
    each non-obvious line has a "why" comment.
- **T-34** `api/main.py` + minimal `web/` — prompt box, plan view, refusal card.
  - **Status:** planned · **AC:** a prompt in the browser produces a plan and a refusal
    card.
- **T-35** `llm/explain.py` — the teaching panel derived from the **plan + fired rules**,
  not from the original prompt.
  - **Status:** planned · **AC:** 3–5 concepts, each naming a specific pin/address/supply
    decision.
- **T-36** **GATE 1 check** — end to end + **record the backup demo video (2 min)**.
  - **Status:** planned · **AC:** the backup video exists and plays. Insurance; do it
    even if everything else is unfinished.

---

## Tier 3 — the proof (Oct 31 – Nov 1)

- **T-40** `render/diagram_json.py` + `parts/wokwi_map.json` → the Wokwi
  `diagram.json`.
  - **Status:** planned · **AC:** the generated project opens in Wokwi and runs. Parts
    with no Wokwi counterpart are excluded and listed in `plan.notes`.
  - **Note:** this is now a *primary* artifact, not a fallback.
- **T-41** **The silicon receipt** — flash the generated firmware to the board you own
  and film it.
  - **Status:** planned · **AC:** a real board runs the tool's output, on camera. The
    onboard LED is enough.
- **T-42** **The parts DB gets real sources and real measurements.**
  - **Status:** planned · **AC:** every `source_url` is a real listing or datasheet page
    (`validate_db.py --strict` passes), and the parts we own are `confidence: measured`
    with a photo next to a ruler.
- **T-43** Muse Image → the annotated wiring diagram, generated from the validated plan.
  - **Status:** planned · **AC:** the diagram matches the plan's pins and addresses.
- **T-44** The open-weight route: run the spec/explain layer on
  `meta-models/muse-spark-open-1026` (Baseten) or Muse Glimmer locally.
  - **Status:** planned · **AC:** one visible feature runs on the open-weight model →
  the **$10k** bonus.

---

## Tier 4 — depth and polish (Nov 2–3)

- **T-50** Teaching panel polish; Muse Voice Transcribe → hands-free Q&A.
  - **Status:** planned.
- **T-51** A separate LLM spec-quality number: "valid spec on N/20 prompts".
  - **Status:** planned · **AC:** reported separately from the solver's 20/20, never
    mixed with it (`SPEC.md` §10).
- **T-52** **GATE 2** — go/no-go on the stretch tiers below. Cut what is not green.
  - **Status:** planned.
- **T-60** Full end-to-end rehearsal ×3, timed. Find the flakiness.
  - **Status:** planned.
- **T-61** Record the final 3-minute video per `docs/DEMO_SCRIPT.md`.
  - **Status:** planned.
- **T-62** README complete: the problem, how it works, the refusal example, the eval
  table, the Meta-model map, honest limitations, how to run (2 commands), screenshots.
  - **Status:** building.
- **T-63** Repo public, `LICENSE` visible, **no keys in git history**, the instructions
  work from a clean clone, mock mode works offline.
  - **Status:** planned.
- **T-64** Submission text written and proofread (500–1000 words).
  - **Status:** planned.
- **T-65** **Submit by Nov 4, 15:00 ET.** Press Submit, not Save.
  - **Status:** planned.
- **T-66** Keep the project reachable through judging (Nov 8). Update
  `docs/SUBMIT_CHECKLIST.md` and tick everything.
  - **Status:** planned.

---

## Stretch — do them if there is time; nothing depends on them

- **T-70** `render/cad.py` + OpenSCAD templates → a plate STL from the grid layout.
  - **AC:** the STL renders headless and slices; the holes land on the grid.
- **T-71** `render/cad.py` → a drill template SVG/PDF.
- **T-72** A physical build: the parts you own, on a breadboard, filmed.
  - **AC:** it runs. This is the strongest receipt if it happens, and the most
    expensive in money and time. It is not on the critical path.
- **T-73** `vision/build_check.py` — SAM 3.1 on a photo of a real build; presence and
  placement diffed against the plan.
  - **AC:** "5/6 parts present · servo not seated in zone B". Only meaningful if T-72
    happens.
