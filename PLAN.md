# PLAN.md — timeline and daily guide

**Your clock:** WIB = ET + 12. Hard deadline: **Nov 5, 09:00 WIB** (= Nov 4, 21:00 ET).
**Submit by Nov 4, 15:00 ET** (= Nov 5, 04:00 WIB). Never use the full window.

**Budget: Rp 0.** Every tool below is a free tier — Meta credits, Wokwi, arduino-cli,
open source. Anything that costs money is a *stretch* task, not a plan task. That
constraint is the plan, not a limitation on it: it means the tool runs for anyone who
clones it, and it means the proof has to be reproducible rather than physical.

## Timeline

| Day | Date (ET) | Theme | End-of-day deliverable |
|---|---|---|---|
| **N0** | Mon Oct 26 | Scaffold · contracts | Repo + CI green; the engine, the rules, the parts DB, the 20-case corpus |
| **D1** | Tue Oct 27 | Parts DB | Every part has a real source; the boards we own are caliper-measured |
| **D2** | Wed Oct 28 | Engine | Modular rewrite; `Plan` carries the full contract; new rules |
| **D3** | Thu Oct 29 | Model + renderers | Muse Spark fills the spec; BOM/wiring/firmware render; the compile gate runs |
| **D4** | Fri Oct 30 | End-to-end + **GATE 1** | one prompt → refusal → fix → recompile; **backup demo video recorded** |
| **D5** | Sat Oct 31 | Simulation + silicon | Wokwi project running; the firmware flashed to a real board, filmed |
| **D6** | Sun Nov 1 | Depth | eval 20 → 100+; a separate LLM spec-quality number; the UI |
| **D7** | Mon Nov 2 | Meta moments + **GATE 2** | Muse Spark Open route; teaching panel; README pass |
| **D8** | Tue Nov 3 | Polish + record | final 3-min video; README; repo public |
| **D9** | Wed Nov 4 | **Submit** | submitted by 15:00 ET |

## Gates

| Gate | When | Must be true | If not |
|---|---|---|---|
| **GATE 0** | Oct 26 | repo + CI green, rules read, parts DB has real sources | nothing else starts |
| **GATE 1** | Oct 30 | end-to-end works + backup video recorded | **cut stretch tiers**, ship the Floor tier |
| **GATE 2** | Nov 2 | (optional) open-weight route, voice, CAD, physical build | cut them |
| **SUBMIT** | Nov 4 15:00 ET | submitted early | — |

**Floor tier (minimum shippable):** prompt → spec → solver → BOM + pin table + wiring +
**compiling** firmware + refusal with costed options + eval table. That is enough to win
an indie-track judgement. Everything else is upside.

## Daily guide

### N0 — Mon Oct 26 (tonight)

- **Read `docs/OFFICIAL_RULES.md`.** It is normative and it wins over every other file.
- **Claim the Meta Model API credits** ($150). This is a **pass/fail gate** — without a
  key there is no Meta model in the loop and the project is out. It needs a form and a
  credit card; do it tonight. Apply to Baseten and Modal as well.
- **Create the public GitHub repo** and push. The rules require a public repo.
- **Join the Discord**: `#intros`, `#team-search` (a second pair of eyes on the
  constraint engine is worth more than anything else you could do alone), `#office-hours`
  (10–11 AM ET daily) with real questions.
- **Verify the free stack works today, not on demo day:**
  - `arduino-cli` installs, and the USB-serial driver (CP2102/CH340) is present, and a
    sketch flashes to the board you own.
  - A Wokwi project opens, runs, and has a shareable link.
- Scaffold: `pyproject.toml`, `.env.example`, `LICENSE` (MIT), the directory tree, and
  CI that runs the validator + eval + tests. **CI green tonight.**

### D1 — Tue Oct 27: Parts DB
- Fill the `source_url` for every part: the listing you actually sell from, or the
  manufacturer's datasheet page. `python scripts/validate_db.py --strict` must pass.
- Measure the parts you own with a caliper: a photo next to a ruler, dimensions in mm,
  `confidence: measured`. **This is the moat** — it is the only thing in the repo a model
  cannot produce, and it cannot be done by anyone else.
- Expand the database (18 → 30+). More parts means more refusals the engine can make.
- Add the `wokwi_name` for every part, including documented substitutions (a soil probe
  is a variable resistor — a potentiometer models it).
- Verify the board profile pin by pin against the Espressif datasheet. **30 minutes here
  prevents 3 hours of wrong pins.**

### D2 — Wed Oct 28: Engine
- Rewrite the engine as modules: `pins / i2c / power / mech / rules / engine / report`.
  Every allocation carries a `reason`; the order is shared buses → analog → PWM →
  digital in → digital out.
- The I²C resolver with priced options; the power budget with the 240 mA WiFi reserve;
  the grid layout and fit check.
- **Add the rules the real work revealed** — a rule discovered while building is worth
  more than a rule inherited from the design. R18 ("we refuse what we cannot prove")
  is the first one: a part with no simulator counterpart cannot be approved, because
  the product's promise is proof.
- Keep: rule IDs stable (`R1`…`R18`), the verdict derivation in `SPEC.md` §7, the
  golden specs passing.

### D3 — Thu Oct 29: Model + renderers
- `llm/providers.py` (Meta | mock), `llm/spec_gen.py` (schema validation, ≤3 retries
  with the validation error fed back, then the local fallback parser).
- Renderers: wiring table, BOM (dated price bands + source links), firmware.
- **The compile gate**: `arduino-cli` compiles the generated sketch. A plan is only
  approved if its code builds.
- API + minimal web UI: prompt box → plan → refusal card.

### D4 — Fri Oct 30: **GATE 1**
- End-to-end: fix whatever breaks; polish the refusal card (it is the money screen).
- Teaching panel v1, derived from the plan.
- `eval/RESULTS.md` final; paste the table into the README.
- **Record the backup demo video (2 min).** Do this even if everything else is
  unfinished. It is insurance.
- **GATE 1 decision at 23:00.**

### D5 — Sat Oct 31: Simulation + silicon
- Wokwi `diagram.json` (+ `wokwi_map.json`); verify the part names against Wokwi's
  library. The approved build must open and run.
- **Flash the generated firmware to the board you own and film it.** The onboard LED
  is enough. This is the silicon receipt, and it costs nothing.
- Muse Image: the annotated wiring diagram, generated from the validated plan.
- Tag a fallback release.

### D6 — Sun Nov 1: Depth
- Expand the eval corpus (20 → 100+ cases). Add positive controls so the no-false-
  refusal claim stays true as the corpus grows.
- A **separate** number for LLM spec quality ("valid spec on N/20 prompts") — never mix
  it with the solver number.
- Web UI polish.

### D7 — Mon Nov 2: **GATE 2**
- The open-weight route: run the spec/explain layer on `meta-models/muse-spark-open-1026`
  (Baseten) or Muse Glimmer locally → the **$10k** bonus.
- Teaching panel v2; Muse Voice hands-free Q&A.
- **GATE 2 at 12:00**: cut what isn't green.
- README full pass + architecture diagram.
- *Stretch, if there is time:* SAM 3.1 on a photo of a real build, the CAD plate and
  drill template, a physical build.

### D8 — Tue Nov 3: Polish + record
- Rehearse the whole flow three times; find the flakiness.
- **Record the final 3-minute video** (`docs/DEMO_SCRIPT.md`).
- README, RESULTS, screenshots; repo public + LICENSE; clean-clone test.
- Write the submission text **today**, proofread it, sleep early.

### D9 — Wed Nov 4: Submit
- 08:00 ET: re-check everything end to end; confirm the video link is public.
- 10:00 ET: final proof-read.
- **15:00 ET: SUBMIT.**

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | fastest for you; all the tooling is Python-friendly |
| API | FastAPI + uvicorn | one process serves API + static UI |
| Frontend | plain HTML + vanilla JS, **no bundler** | `git clone && uvicorn api.main:app` just works |
| LLM | Meta Model API, `muse-spark-1.3` | the $150 of credits; the Stage One gate |
| Provider swap | `providers/{meta,mock}.py` | CI and judges need no key |
| Image | Muse Image | the annotated wiring diagram, from the validated plan |
| Voice | Muse Voice Transcribe | hands-free Q&A — stretch |
| Vision | SAM 3.1 | build-check on a photo of a real build — stretch |
| Open weights | Muse Spark Open on Baseten | the $10k bonus |
| Compile gate | arduino-cli | ground truth: the code builds |
| Simulation | Wokwi `diagram.json` | the approved build, running in a browser |
| CAD | OpenSCAD + drill SVG/PDF | stretch — no printer, no demo payoff |
| Validation | jsonschema | CI-enforced contracts |
| Tests | pytest **or** the bundled zero-dep runner | `python tests/run_tests.py` |
| State | JSON + git | every measurement is a reviewable commit |

## Risk register

| Risk | Trigger | Fallback |
|---|---|---|
| **No Meta API key** | any | the Stage One gate fails. Fallbacks: Baseten, Modal, Muse Glimmer locally. **Treat this as the top risk and clear it on D0.** |
| Wokwi account / link blocked | D5 | ship `diagram.json` + a "simulate in your browser" button; ground truth stays compile + fit-check |
| Flashing does not work (driver) | D5 | the silicon receipt is dropped; compile + simulation carry the proof, and the README says so |
| The Wokwi part name is wrong | D5 | check the name against Wokwi's library; a part with no counterpart is excluded from the simulation and `plan.notes` says so |
| The parts DB stays unmeasured | D1 | R16 warns on any mount build; say so plainly in the README |
| The API errors / credit burn | any | mock provider + cached fixtures; the refusal demo needs zero LLM calls |
| Running out of time | D4 | cut to the Floor tier |
| Judges can't run it (no key) | D8 | `MODEL_PROVIDER=mock` + inline artifacts in the README |
| Nobody runs your app at all | D8 | the README is the demo for most judges — put the refusal, the eval table, the pin table and the artifacts inline |

## Budget

| Item | Rp |
|---|---|
| Everything | **0** |
| Meta Model API | $150 credit (free) |
| Baseten / Modal | $100 credit each (free) |
| Wokwi, arduino-cli, OpenSCAD, Python | free tiers / open source |

The cost of the whole tool is zero, which is why the proof has to be reproducible
rather than physical: a judge can clone it, compile it, and run it themselves.

## Judging map (official rubric, four criteria, equally weighted)

| Criterion | What satisfies it | Where it shows | Risk |
|---|---|---|---|
| **Impact** | makers and students who lose evenings to dead builds — especially those with no lab: no caliper, no scope, no parts drawer | the "why this exists" opening | low |
| **Use of Meta AI Tooling** | Muse Spark 1.3 in the loop; the open-weight route; Muse Image; Muse Code as a build collaborator | the spec screen + a line in the README | **highest — ship at least three** |
| **Technical Depth & Execution** | the constraint engine, the compile gate, the fit check, the eval harness, the measured parts DB | README architecture + the eval table | low (this is the moat) |
| **Demo** | live refusal → priced fix → recompile → the build running → the eval table; 3 minutes | the whole video | medium (depends on Wokwi + the flash) |

**Bonus-prize targets (flag them in round one):**
- $20k Most Viral → post the demo on X on Nov 4, submit the link, re-post Nov 5.
- $10k Best Build on Meta Open Weight Models → run the spec/explain layer on
  `meta-models/muse-spark-open-1026` (Baseten) or Muse Glimmer locally.
- $10k Community Vote → get people to vote before Nov 16.
- $5k Best Agentic Use-Case → the build loop, and Muse Code in the loop.
- $5k Best Creative Build → Muse Image doing something genuinely nice, not decoration.

**Startup track:** swap the emphasis to production-readiness — dated local prices,
costed fixes, a hosted demo, a repo that runs without keys.
