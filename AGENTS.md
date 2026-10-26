# AGENTS.md — operating instructions for whoever builds BenchTruth

You are working on **BenchTruth**, a hackathon project for the **Meta Global AI Developer
Hackathon 2026** (Oct 26 – Nov 4, 2026, $1M prize pool). Read this file first, then
`CONTEXT.md` (why), `PLAN.md` (when), `TASKS.md` (what), `SPEC.md` (contracts).

## The one-sentence goal

**An LLM proposes a hardware build; a deterministic toolchain disposes of it.**
The product is not a generator — it is a **verifier that refuses**. A build is not
"generated" until it compiles, fits, and has a power budget that closes.

## Three claims that must be true on Nov 4 (submit day)

1. It **refuses** physically impossible builds, with the correct rule, the physics, and
   costed fixes.
2. Every build it approves **compiles** (arduino-cli), **simulates** (Wokwi), and
   **fits** (measured dimensions).
3. The generated firmware **runs on a real board** — flashed to hardware, on camera.

If (1) and (2) are green, you can submit even if everything else is cut.
If (1) is not green by **D4 (Oct 30, end of day)**, cut Tier 2–5 and ship the Floor tier.

## The "new work only" rule — read this before you write anything

The official rules: *"What you present must have been built during the event."* The
indie track gets **less latitude** than startups, and the instruction is to keep the
new work surface **large and obvious**.

Therefore, for every task you take on:

- **Prefer work that cannot have existed yesterday.** New renderers, the Meta model
  layer, the compile gate, the simulation, the UI, the silicon receipt, the
  re-measured parts database — all of it counts. A refactor counts less; a *new
  capability* counts more.
- **Every commit should add a capability, a measurement, or a piece of evidence.**
- **Never rewrite history or back-date a commit.** `docs/BUILD_LOG.md` says so
  explicitly; do not break that promise.
- **Rebuild the moat.** The parts database is called the moat in these docs. Right now
  zero parts are `measured` and every `source_url` is a TODO. Measuring parts with a
  caliper and filling in real listings is the single largest block of genuinely new
  work available, and it fixes the honesty problem at the same time.
- **Update `docs/BUILD_LOG.md` and the README's status table as you land things.**
  They are the statement of what exists, and a stale one is worse than none.
- **Park, do not cancel.** Work that is not on the critical path stays in `TASKS.md`
  marked *stretch* — it gets done if there is time, and it is not a promise.


## Non-negotiables

> **Read `docs/OFFICIAL_RULES.md` before anything else. It is normative and it wins over
> every other file here.** Three of its rules change how you build:
>
> 1. **The project MUST incorporate Meta's models** (Stage One is a pass/fail gate on it).
> 2. **"Simple AI for Education chatbots" and "Simple Image Analyzers" are BANNED.**
>    The teaching panel is a *diagnostic side panel of an engineering tool* — never an
>    education chatbot, never a chatbot front-end, no RAG.
> 3. **New work only.** Building period is **Oct 27 – Nov 4**. Commit with a readable
>    history and make the new work obvious.

- **Never let an LLM write into `parts/parts_db.json`.** Unknown parts → rule R15 → refuse.
- **The LLM writes intent, never artifacts.** It fills `project_spec.schema.json`. It never
  names pins, never writes code, never writes geometry. The solver assigns pins.
- **Geometry comes from templates, not from generation** — if the CAD layer gets built
  at all. Never let a model draw a bracket.
- **Every FATAL violation must offer costed ways out** (from the parts DB price band).
  A refusal without options is a dead end and a bad demo.
- **Ground truth is code, not prose.** The compile gate, the constraint solver, and the
  parts DB are what make the claim true. Keep docs and code in sync —
  `ruleset.md` IDs must match `solver.py` rule IDs exactly.
- **Never commit API keys.** `.env.example` only. `MODEL_PROVIDER=mock` must work with
  zero network access, because CI and judges may not have keys.
- **The demo video must show only what you built during the hackathon.** Keep competitor
  comparisons and background in the README, out of the video.

## Where you can score points you don't yet

The rubric is four equally weighted criteria: **Impact · Use of Meta AI Tooling ·
Technical Depth & Execution · Demo.** The solver carries Technical Depth, but carries
**nothing** on Use of Meta AI Tooling unless you ship visible Meta moments:

1. **Muse Spark 1.3** → fills the spec. This one is mandatory: no Meta model in the
   loop is a pass/fail gate, not a lost bonus.
2. **Muse Spark Open** (`meta-models/muse-spark-open-1026` on Baseten, or Muse Glimmer
   locally) → run the spec/explain layer on an open-weight model. Qualifies the project
   for the **$10k Best Build on Meta Open Weight Models** bonus.
3. **Muse Image** → the annotated wiring diagram, generated from the *validated plan*,
   not decoration.
4. **Muse Code** → write real parts of the renderer/UI, and say so. The build loop
   (prompt → spec → verify → refuse → rebuild → explain → diagnose) is a genuine
   agentic workflow → **$5k Best Agentic Use-Case** bonus.

Stretch: **SAM 3.1** on a photo of a real build, diffed against the plan. Only if there
is a physical build to photograph.

Also: **post the demo on X on Nov 4 and submit the link** → **$20k Most Viral Project**.
And tell people to vote → **$10k Community Vote** (winner Nov 16).

## Gates (do not skip, do not move)

| Gate | When (ET) | What must be true |
|---|---|---|
| GATE 0 | Oct 26 | Repo scaffolded, CI green, official rules read, parts DB has real sources |
| **GATE 1** | **Oct 30** | **End-to-end works: prompt → plan → refusal + artifacts. Backup demo video recorded.** |
| **GATE 2** | **Nov 2** | Go/no-go on stretch tiers (SAM 3.1 build-check, voice, CAD) |
| SUBMIT | Nov 4, before 15:00 ET | Submitted early. **Never use the full window.** |

## Working style

- Ship a *working vertical slice* every day. A broken half-feature is worth nothing;
  a boring working thing is worth a lot.
- When something is cut, remove it from the demo script too. A video that shows a
  half-built feature is worse than a video that doesn't mention it.
- Keep the demo video script in `docs/DEMO_SCRIPT.md` and update it the moment scope changes.
- If you are blocked for more than 90 minutes on one thing, cut it and move on.
  Tier 1 must exist before Tier 2 does.
- **The budget is Rp 0.** Everything runs on free tiers: Meta credits, Wokwi, open
  source. If a task needs money, it is a stretch task, not a plan task.

## Reference implementation status

`benchtruth/` is a **working reference solver** with a green test suite (see
`eval/RESULTS.md`). It is deliberately small and readable. You may replace any module —
but if you do, keep:
- rule IDs stable (`R1`…`R17`),
- the verdict derivation in `SPEC.md` §7,
- the golden specs in `eval/golden_specs.json` passing.

`eval/run_eval.py` must print **20/20 correct verdict** before you ship.

## Where things live

| Path | What |
|---|---|
| `parts/parts_db.json` | Parts + board profiles, with a real source per part. **The moat.** |
| `parts/signal_profiles.json` | Electrical signal profile per part (signals needed, rail, pull-ups) |
| `parts/db.schema.json`, `parts/signal_profiles.schema.json` | Schemas for the data files (CI-enforced) |
| `ruleset.md` | R1–R17, severity, autofix policy, refusal template |
| `spec/project_spec.schema.json` | What the LLM is allowed to produce |
| `eval/cases.json` | 20 conflict cases with expected verdicts |
| `eval/golden_specs.json` | Hand-written specs for those cases (deterministic eval) |
| `eval/run_eval.py` | The headline number |
| `scripts/validate_db.py` | The CI gate for the data contracts |
| `docs/BUILD_LOG.md` | What was built, day by day |
| `docs/DEMO_SCRIPT.md` | Shot list for the 3-minute video |
| `docs/SUBMIT_CHECKLIST.md` | Everything that must exist before you press Submit |
