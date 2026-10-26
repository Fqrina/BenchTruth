# OFFICIAL_RULES.md — extracted from the Meta participant guide (Oct 26, 2026)

Source: "Meta Global AI Developer Hackathon Participant Guide" (Cerebral Valley). This file
is the **normative** version of the rules. If it conflicts with `CONTEXT.md`, **this file wins**.

## Hard constraints (violating these = disqualification)

1. **Your project must incorporate Meta's models.** Stage One is a pass/fail gate on
   "reasonably used Meta Model API and/or Meta's open-weight models". Non-negotiable.
2. **New work only.** "What you present must have been built during the event." Judges can
   disqualify "at Judges sole discretion" if the contribution is not clear.
   - Building period: **Oct 27 – Nov 4**. Kickoff Oct 26 12:00 ET.
   - Mitigation: commit from Oct 27 onward with a readable history; state in the README
     exactly what was designed before the event and what was built during it.
   - Startups may build on existing codebases but must identify what is new. Indie projects
     get less latitude — keep the "new work" surface large and obvious.
3. **Repository must be public.**
4. **Demo must only highlight what you built during the hackathon.** Judges must be able to
   clearly identify your original contributions.
5. **Team size max 4.** Solo is allowed.
6. **No code, data, or assets you don't have the rights to.**
7. **3-minute demo video**, one of the primary judged artifacts, alongside code and the
   live product.

## BANNED project patterns (do not build these)

- AI that generates medical / mental-health / skin-diagnosis advice
- **Basic RAG applications**
- **Simple image analyzers**
- **Simple "AI for Education" chatbots**
- AI job-application screeners
- AI nutrition coaches
- Personality analyzers
- Sports analyzers or coaches
- Anything political or involving war

### How this constrains BenchTruth

- The **teaching panel must never be positioned as an education chatbot**. It is a
  *diagnostic side panel of an engineering tool*, derived from the validated plan.
- Do not frame the project as "AI teaching electronics". Frame it as
  **"a hardware build verifier: it refuses impossible builds, and explains why."**
- No RAG, no chatbot front-end, no "ask it anything" product surface.
- Keep competitor comparisons in the README (or drop them) — out of the demo video,
  which must only show what you built.

## Judging rubric (Stage Two, four criteria, equally weighted, 0–10)

| Criterion | What it asks | BenchTruth's answer |
|---|---|---|
| **Impact** | real-world potential, who benefits, could people use it | makers and students who waste evenings on dead builds; classrooms without a lab |
| **Use of Meta AI Tooling** | "Did they go beyond a basic integration? Did they surface capabilities that surprised even us?" | **the weakest axis — see below** |
| **Technical Depth & Execution** | sound engineering, thoughtfully refined, real craft | the constraint engine, compile gate, fit-check, eval harness — the strongest axis |
| **Demo** | working, impressive, holds up live, genuinely cool to watch | the refusal → fix → real hardware running |

**Stage Three:** top 5 per track → final round, judges watch the video demos live, same
rubric. So the video is the finals exam, not a formality.

### Closing the "Use of Meta AI Tooling" gap

The solver is deterministic, so on its own it scores nothing on that axis. Ship **three
visible Meta moments**:

1. **SAM 3.1 → physical build check.** Point a phone at the assembled breadboard; SAM
   segments the parts; the tool diffs them against the plan ("5/6 parts present, servo
   not seated"). Mask-based measurement is the one thing a chat model cannot do.
2. **Muse Spark Open on your own hardware or a partner endpoint.** Run the spec/explain
   layer through `meta-models/muse-spark-open-1026` on Baseten (or Muse Glimmer locally
   via llama.cpp/vLLM, or Modal). This also qualifies the project for the
   **$10k Best Build on Meta Open Weight Models** bonus.
3. **Muse Code as a build collaborator.** Use it during the event to write real parts of
   the renderer/UI, and say so plainly. Doubles as the **$5k Best Agentic Use-Case**
   bonus: the build loop (prompt → spec → verify → refuse → rebuild → explain →
   diagnose) is a genuine multi-step agentic workflow.

The story to tell: **"the models do what models are good at; the deterministic engine
decides what is true."** That sentence is itself a Meta-tooling story.

## Prizes

| Track | 1st | 2nd | 3rd | 4th | 5th | Total |
|---|---|---|---|---|---|---|
| Indie Developer | $150K | $100K | $75K | $50K | $25K | $400K |
| Startups | $250K | $150K | $75K | $50K | $25K | $550K |

Bonus prizes (Meta, $50K total):
- **Most Viral Project — $20k**: highest engagement on X up to Nov 8 EOD. *You must post
  the demo on X and submit the post link on the platform.* Do this on Nov 4 after
  submitting, and again Nov 5.
- **Best Build on Meta Open Weight Models — $10k**: Muse Glimmer or Muse Spark Open served
  on your hardware or partner inference. Flagged in round 1; the partner verifies.
- **Community Vote — $10k**: most votes in the public gallery; winner Nov 16. *One vote
  per verified account — tell your friends.*
- **Best Agentic Use-Case — $5k**
- **Best Creative Build — $5k** (Muse Image / Muse Wonder)

## Credits & partners

- **Meta Model API: $150 per participant.** Claim link "coming soon" — check the platform
  page. **A credit card must be on the account** before credits work. Set a spend-limit
  notification so you cannot exceed $150.
- **Baseten**: $100 + 2M TPM, up to 2,000 participants, reviewed per use case, **per
  individual**. Model id for the hackathon: `meta-models/muse-spark-open-1026`
  (not `muse-spark-open`). OpenAI-compatible chat-completions API.
- **Modal**: $100 for the first 1,000 participants, for running Meta open-weight models
  through Endpoints + serverless GPUs.
- **Fireworks**: $25 per team, shortlist only.
- Credits are **not guaranteed** and partners may not answer. Do not architect around them.

## Schedule (ET)

| When | What |
|---|---|
| Mon Oct 26 12:00 PM | Kickoff — rules, prizes, judging, Meta speakers |
| Tue Oct 27 12:00–1:00 PM | **Agents 101: Build a Multimodal AI Agent** (Suraj Subramanian, Yash Khare) |
| Wed Oct 28 12:00–1:00 PM | **Agents 102: Best Practices for Verifiable Agents** ← directly relevant |
| Fri Oct 30 12:00–1:00 PM | Building Specialized Intelligence on Fireworks: Muse open models (Sinan Ozdemir) |
| Daily 10–11 AM ET (except weekends) | Discord #office-hours with Meta engineers — **use it** |
| Tue Nov 3 | Last full day for submission questions |
| Wed Nov 4 9:00 PM ET | Final office hours; submissions due via the CV platform |
| Thu Nov 5 – Sun Nov 8 | Judging |
| Mon Nov 9 12:00 PM | Closing ceremony, top 10 announced, live final judging, community vote opens |
| Mon Nov 16 | Community vote winner announced on Discord |

On-demand sessions: The multimodal intelligence of Muse Spark · Building with Muse Spark
and Muse Code · The road ahead: the superintelligence blueprint.

## Submission

- Via the CV platform, by **Nov 4, 9:00 PM ET**. One submission per team.
- A **Representative** submits on the team's behalf.
- Required: public repo, accessible video link, and **everyone who worked on the project
  listed on the submission page**.
- 3-minute demo video is a primary judged artifact.

## Discord (do this tonight)

- **#intros** — introduce yourself, your skills, your project. This is free visibility and
  it feeds the community vote.
- **#team-search** — teams up to 4. Solo is allowed, but a second pair of eyes on the
  constraint engine is worth more than anything else you could do alone.
- **#office-hours** (10–11 AM ET) — ask Meta engineers about Muse Spark structured output
  / JSON mode, SAM 3.1 video behaviour, rate limits, and spend limits. Bring specific
  questions; they answer text.
- Baseten / Modal channels for partner-specific questions.
