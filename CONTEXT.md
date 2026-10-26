# CONTEXT.md — why this project exists

## The situation

This is a **Meta Global AI Developer Hackathon 2026** entry (Meta + Cerebral Valley),
Oct 26 → Nov 4, 2026, $1M pool, tracks *Indie Developer* / *Startup*, themes
*Build for Your World* / *Push the Frontier*.

- Applications: Oct 13–25 (rolling review, 20,000 cap). **Application is only a
  selection gate** — Meta scores the form on (1) idea clarity/feasibility/theme fit and
  (2) technical skill shown. It does **not** bind what you build.
- Building: Oct 26 → Nov 4, 9:00 PM ET. Judging: Nov 4–8. Winners: Nov 9.
- Submission needs: public repo (+LICENSE), description text, demo video ≤3 min
  (YouTube/Vimeo, public). Judges may test the project; keep it reachable through judging.
- **No interviews.** Judges score from your description, video, and repo. Therefore the
  video and README must pre-empt every question a judge *would* have asked.
- $150 in Meta Model API credits per accepted builder. Budget them.
- Official rules land at the kickoff livestream (Oct 26) — **read them first, and re-read
  them if this document disagrees with them.** This file is a snapshot.

## Available models (Meta Model API)

| Model | Use in this project |
|---|---|
| `muse-spark-1.3` | Fills `project_spec.json`; writes the teaching panel; troubleshooting dialogue |
| `muse-image` | Annotated wiring diagram, enclosure preview, corrective arrows on the user's photo |
| `muse-voice-transcribe` | Hands-free Q&A at the bench |
| `sam-3.1` | Build-check: segment the user's assembled build, diff against the plan |
| Muse Code | Built the solver and CI (say so in the README) |
| Muse Glimmer / Spark Open | Offline on-device mode for classrooms (stretch) |

**Open-weight option (also a bonus-prize route):** Baseten serves
`meta-models/muse-spark-open-1026` with an OpenAI-compatible chat-completions API, and
Modal hosts open-weight models on Endpoints. Running the spec/explain layer on Muse
Spark Open (or Muse Glimmer locally) makes the project eligible for the
**$10k "Best Build on Meta Open Weight Models"** bonus. Use it for at least one visible
feature — the provider abstraction already makes this a one-line change.

Nothing is required — "use every model" is not a rule. But the rubric *does* score "Use
of Meta AI Tooling" at 25%, and a deterministic solver scores zero there on its own. Ship
visible, surprising Meta moments (SAM 3.1 build-check, an open-weight model in the loop,
Muse Code as a build collaborator). The story to tell: **"the models do what models are
good at; the deterministic engine decides what is true."**

## The competitive landscape (why not the obvious thing)

Two project directions were considered:

**(A) Prompt → buildable hardware kit.** (This project.) The pipeline — BOM + wiring +
enclosure + firmware from a prompt — is a **commodity**. As of Oct 2026 there are at least
eight products doing exactly that: Schemr (prompt → BOM with part numbers/prices, wiring,
3D CAD, firmware, build-confidence score), sensbench (live-priced BOM, pin-by-pin table,
compile-gated firmware, browser sim), Codey Online, Schematik, Banana Board, Cirkit
Designer, PleaseDontCode, CircuitMind-copilot. Two of them (Schemr, sensbench) are
*retailers with a chat interface* — they own supply and pricing.

**(B) Phone video → engineering-grade inspection report** ("Patina"). Uses SAM 3.1 for
mask-based measurement and video tracking. Rejected for this project because:
- Its hard numbers (area in cm², growth rate, cycle counts) need **scale calibration**
  and a **static defect** that its own pitch never specifies — "3.17 cm²" from a mask is
  pixels, not centimetres.
- Its diagnosis layer is prose from a frontier model — exactly the "just video-call Gemini"
  criticism.
- Its "regenerated clean cutaway" would hallucinate the geometry of the photographed part.
- It requires manufacturing/NDT domain depth that this builder does not have.
- It is not this builder's idea to begin with.

**Why (A) survives:** its hard part — *does it fit, does it compile, does it run* — has
**ground truth that can be checked**, while (B)'s hard part — *is this number right* — has
ground truth you must *define*. And (A) has **graceful degradation**: stripped to its
floor it is still a coherent, defensible product, whereas (B) stripped of its calibration
is a chatbot.

**How this project answers "isn't it just a prompt?"**

> Anyone can prompt a chatbot for a wiring diagram. Only one of them will tell you your
> build is *impossible* — with the reason, the cost, and a compile + simulation proof.

The differentiator is not generation. It is **verification**, and the **refusal**.

## Positioning

- **The concept inversion:** a generator that says no.
- **The moat:** a parts database with a real source per entry, caliper measurements for
  the parts we own, + a deterministic constraint engine + a verification corpus. None of
  it is generatable by a model.
- **The receipt:** the approved build **compiles**, **simulates** in a browser, and the
  generated firmware **runs on a real board**. None of those three need a budget.
- **The teaching layer:** the "why" panel derived from the *validated plan* (this pin,
  this address, this supply) — not from a chat prompt. Note honestly: "ask a chatbot to
  teach" is a fair criticism; teaching is the **retention story**, verification is the
  **headline**. Do not lead with a learning platform.
- **Theme:** *Build for Your World* fits if the flagship build is the builder's own
  problem (a gas/smell alarm). *Push the Frontier* fits if the pitch is
  "understand and control a physical system" (generate → verify → build → check the
  build). Either is defensible; pick one and be consistent in the write-up.

## Honest limitations to state in the README (credibility is free)

- The parts DB is **18 parts** and growing. It is not "all of electronics". The tool
  **refuses** anything outside it (R15) rather than guessing.
- Dimensions from clones vary. R16 flags uncertainty; a 3 mm-tolerant grid is the
  mitigation, and the parts we own get measured with a caliper.
- The simulation is **behavioural, not electrical**: it shows the fixed build working.
  The power and level numbers come from the solver's arithmetic, not the simulator. Say
  so plainly.
- Prices are dated bands from listings, not live commerce.
- There is no budget behind this. Every tool is a free tier, and the whole thing runs
  for anyone who clones it. Say that too — it is a feature, not a caveat.

## The demo (see docs/DEMO_SCRIPT.md for the shot list)

The money shot, in order:
1. Prompt: "ESP32 gas alarm with a servo vent, an OLED, and a buzzer."
2. The tool **refuses**: GPIO 34 is input-only; the SG90 stalls at 250 mA and the 3V3
   rail dies at 300 mA; two I2C devices want 0x3C.
3. It offers **costed options A/B/C**.
4. You pick A → it rebuilds → **recompiles** → the pin table lands next to the ESP32
   capability table.
5. The approved build **runs** — simulated in the browser, and the same firmware
   **flashed to a real board** on camera.
6. The eval: "20/20 conflicting specs refused with the correct rule; 0 false refusals."
