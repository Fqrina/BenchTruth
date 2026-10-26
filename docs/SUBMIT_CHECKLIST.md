# SUBMIT_CHECKLIST.md — do this on Nov 3, not Nov 4

## Package

- [ ] **Repo public**, on GitHub, with a visible `LICENSE` (MIT)
- [ ] No API keys anywhere in the history (`git log -p | grep -i "sk-\|api_key"`)
- [ ] `.env.example` present, `.env` gitignored
- [ ] `README.md` complete:
  - [ ] the problem, in two sentences
  - [ ] how it works (one diagram, ASCII is fine)
  - [ ] **the refusal example, verbatim** (screenshot + text)
  - [ ] the eval table (the 20-case results)
  - [ ] which Meta models are used and what each one does
  - [ ] **honest limitations** (DB size, measurement confidence, simulation caveat)
  - [ ] how to run: two commands, plus "works offline with `MODEL_PROVIDER=mock`"
  - [ ] screenshots of the UI, the simulation, and the board
- [ ] **Demo video** ≤ 3:00, public on YouTube/Vimeo, no copyrighted music, shows it working
- [ ] Description text (500–1000 words) written and proofread — this is what a judge skims
- [ ] Track chosen (Indie or Startup) and theme chosen, consistent with the write-up
- [ ] `eval/RESULTS.md` committed and its numbers match what you say in the video

## Before you press Submit

- [ ] Re-run `python eval/run_eval.py` → 20/20
- [ ] Re-run `python tests/run_tests.py` → all pass
- [ ] Re-run `python scripts/validate_db.py` → no blocking problems
- [ ] Cold start: clone into a fresh folder, follow the README, does it run?
- [ ] The demo video link opens publicly (in a logged-out browser, in an incognito window)
- [ ] The app/hosted demo is reachable and does not need your API key

## Timing

- [ ] **Submit by Nov 4, 15:00 ET** (= Nov 5, 04:00 WIB). Do not use the full window.
- [ ] Press **Submit**, not Save.
- [ ] Keep everything up until judging ends (Nov 8) — some judges test projects.

## After submitting

- [ ] Don't touch the repo for 24 h unless something is broken.
- [ ] If you get asked questions in Discord/email, answer with the README's numbers.
