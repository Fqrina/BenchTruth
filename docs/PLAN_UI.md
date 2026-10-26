# PLAN_UI.md — the middle panel: a pin map that shows *why* a build fails

**Audience:** an engineer or an LLM building this with no other context. Everything
you need is in this file plus the repository. Do not invent a different product.

---

## 1. What you are building

BenchTruth is a hardware build verifier. A prompt becomes a validated *spec* (intent
only). A deterministic solver turns the spec into a *plan* (pins, I²C addresses, power
budget, mechanical fit) and, when the build is impossible, a list of **violations** —
each with a rule id, the physics, and costed ways out.

**Your job is the middle panel of the web UI:** an SVG that draws the board, the parts
and every wire, **with each violation drawn on the wire it belongs to**.

The point of the panel is that a viewer sees *why* a build fails without reading a
single line of prose: the wire that carries too much current is red, the two devices
fighting over `0x3C` are on a red bus trunk, and the pin that had to move is shown
being moved.

### Non-goals — do not build these

- **No 3D.** No Three.js, no GLTF, no procedural geometry. A 3D render is table
  stakes, it cannot be verified, and it does not show a refusal.
- **No bundler, no npm, no node_modules, no build step.** The app must run with
  `pip install -r requirements.txt && uvicorn api.main:app`. Plain HTML, one
  JavaScript file, one CSS file, and vendor any library you use into the repo.
- **No geometry from a model.** Every dimension comes from `parts/parts_db.json`.
- **Do not touch the solver.** `benchtruth/solver.py` and `llm/` are owned by the repo
  owner. If you believe the plan contract is wrong, write it down and move on.

---

## 2. Repository layout — where your files go

```
api/main.py              FastAPI app (owned by the repo owner; you add routes if asked)
web/index.html           the three-panel shell
web/app.js               the interaction layer, one file
web/style.css            the styles
web/vendor/              any vendored JS library, committed
render/svg.py            YOUR MAIN DELIVERABLE: plan -> SVG
tests/test_svg.py        your tests (the repo has a zero-dependency runner)
docs/fixtures/*.json     real plan fixtures -- build against these
```

---

## 3. The input contract

The renderer takes **one argument: a plan object** (SPEC.md §8). The committed
fixtures are real output from the real solver:

| Fixture | State | Use it for |
|---|---|---|
| `docs/fixtures/plan_flagship_offer.json` | `OFFER` · R5, R8, R12, R11 | the main case: four violations, four kinds of wire |
| `docs/fixtures/plan_build.json` | `BUILD` · no violations | the approved state: everything neutral/green |
| `docs/fixtures/plan_refuse.json` | `REFUSE` · R15 | the hard refuse: a part that is not in the database |

Regenerate them with `python scripts/make_fixtures.py` (the solver contract may
change; the fixtures are the contract's test data).

### 3.1 The plan object

```jsonc
{
  "db_version": "0.3",
  "board": "esp32-devkitc-v4",
  "verdict": "BUILD" | "OFFER" | "REFUSE" | "WARN" | "FIXED",

  "signals": [                       // one entry per allocated signal
    { "part_id": "sg90", "kind": "pwm_out", "direction": "out",
      "gpio": 32, "reason": "PWM/LEDC capable", "requested": false, "bus": null }
  ],

  "i2c": {
    "bus": "i2c0", "sda": 21, "scl": 22,
    "devices": [ { "part_id": "ssd1306-096", "name": "0.96in SSD1306 OLED…",
                   "address": "0x3C" } ]
  },

  "power": {
    "rails": [ { "name": "3v3", "peak_ma": 580, "capacity_ma": 300, "reserve_ma": 240 },
               { "name": "5v",   "peak_ma": 0,   "capacity_ma": 500 },
               { "name": "external", "peak_ma": 250, "capacity_ma": null } ],
    "breakdown": [ { "part": "SG90 micro servo", "rail": "external", "peak_ma": 250 } ]
  },

  "mech": { "mount_style": "free", "envelope": null, "cells": [ … ], … },

  "violations": [
    { "rule_id": "R11", "severity": "FATAL", "autofix": "OFFER",
      "headline": "3V3 rail needs 580 mA but the board is rated 300 mA",
      "why": "Breakdown on the 3V3 rail: …",
      "applied": false, "verdict": "OFFER",
      "affected": [ { "kind": "rail", "name": "3v3" },
                    { "kind": "part", "part_id": "sg90" } ],
      "fixes": [ { "id": "A", "label": "Move the load to VIN (5 V)…",
                   "cost_idr": [40000, 120000], "effort": "2 extra wires" } ] }
  ],

  "notes": [ … ]
}
```

### 3.2 The two data files the renderer also needs

- **`parts/parts_db.json`** → `parts[]`: `id`, `name`, `logic_v`, `supply_v_min/max`,
  `current_idle_ma`, `current_peak_ma`, `iface{type, pins[], i2c_addr_default,
  i2c_addr_options[]}`, `dims{w_mm, d_mm, h_mm, confidence, shape_class}`,
  `needs_flyback`, `needs_external_supply`, `price_idr_min/max`.
  → `boards[]`: `id`, `name`, `logic_v`, `pins{input_only[], flash_reserved[],
  strapping[], usb_native[], uart0[], boot[], adc1[], adc2[], dac[], touch[],
  pwm_ledc[], i2c_default{sda,scl}, spi_vpsi{}}`, `rails{"3v3"{recommended_max_ma…},
  "5v_vin"{…}}`, `dims{w_mm,d_mm,h_mm}`.
- **`parts/signal_profiles.json`** → per part: `power_rail` (`3v3`|`5v`|`external`),
  `onboard_pullups`, `pullups_needed`, `wokwi_name` (null = no simulator counterpart),
  `library`, `keywords`.

---

## 4. The output contract: an SVG string

`render/svg.py` exposes:

```python
def render_plan_svg(plan: dict, db=None) -> str:
    """Return a complete, standalone SVG document for this plan."""
```

Rules:

- It returns a **string** of one `<svg>` element. No HTML, no `<script>`, no external
  references, no CSS blocks inside the SVG (put the styles in `web/style.css` and
  target the classes — the SVG is injected into the page, so page CSS applies).
- **Deterministic**: the same plan must always produce byte-identical SVG. No
  `random`, no timestamps, no dict iteration order dependence. There is a test for
  this and it is the one property worth being proud of.
- It is a **pure function of the plan plus the two data files**. It never calls the
  solver, never reads the prompt, never makes a network call.
- It must not raise on a plan it does not understand: an unknown part, a missing pin,
  a null rail capacity. **Draw a red "unknown" box with the rule id instead of
  crashing.** A renderer that crashes on a weird plan is useless in a demo.

### 4.1 Required element hooks

The JavaScript binds to these. The `id`/`class`/`data-*` names are the contract —
do not rename them without updating this file and `web/app.js` together.

```svg
<svg viewBox="0 0 1200 860" class="plan-svg" data-verdict="OFFER">
  <g id="rails">
    <g class="rail" data-rail="3v3" data-over="true">
      <text class="rail-name">3V3</text>
      <text class="rail-load">580 / 300 mA</text>
      <rect class="rail-bar" …/>
    </g>
  </g>

  <g id="board" data-board="esp32-devkitc-v4">
    <g class="pin" data-gpio="33" data-caps="adc1,pwm" data-header="">
      <rect class="pin-body"/><text class="pin-label">33</text>
    </g>
  </g>

  <g id="parts">
    <g class="part" data-part="sg90" data-rail="external" data-fault="r12,r11">
      <rect class="part-body"/><text class="part-name">SG90 micro servo</text>
      <text class="part-meta">external · 250 mA</text>
    </g>
  </g>

  <g id="wires">
    <path class="wire" data-wire="w7" data-part="sg90" data-gpio="32"
          data-rail="external" data-fault="r12,r11" d="…"/>
    <path class="wire rejected" data-wire="w7r" data-part="soil-capacitive"
          data-gpio="25" data-fault="r5" d="…"/>
    <path class="bus" data-bus="i2c0" data-fault="r8" d="…"/>
  </g>

  <g id="badges">
    <g class="badge" data-rule="r11" data-severity="FATAL" data-x="…" data-y="…">
      <rect/><text>R11</text><text>580 mA on a 300 mA rail</text>
    </g>
  </g>
</svg>
```

`data-fault` is a **space-separated list of lower-cased rule ids** (`"r11"`, not
`"R11"`). One wire can carry several faults.

---

## 5. The layout

One canvas, `viewBox="0 0 1200 860"`, dark theme. Three vertical zones:

```
 0        260              640    700                       1200
 |  RAILS |  BOARD (pins)   |     |        PARTS             |
 |        |                 |     |                         |
```

### 5.1 Rails column (x 0 → 250)

One card per rail that appears in `plan.power.rails` (skip a rail with
`capacity_ma: null` — it has no budget to violate, but still show the external rail
if parts use it). Each card:

- the rail name (`3v3`, `5v`, `external`)
- `peak_ma / capacity_ma`
- a horizontal bar: filled to `peak_ma / capacity_ma`, **clamped to 100%**, and
  `data-over="true"` when `peak_ma > capacity_ma`
- the WiFi reserve shown separately: `reserve_ma` in a smaller, muted line
- when over budget, the card gets the FATAL treatment (see §6)

### 5.2 Board (x 260 → 640)

- A rounded rectangle for the board body, with the board name and its real
  dimensions from `boards[].dims` (`52.4 × 27.9 mm`).
- **Two pin strips**:
  - the **left strip** is the power side: `3V3`, `GND`, `5V`, `GND`, `VIN`, `EN`,
    plus any other rail pins the parts need. Derive the set from the parts'
    `power_rail` values; it is at most four entries. These are *not* GPIOs, so
    `data-gpio` is empty.
  - the **right strip** is the signal side: one pin per GPIO the plan actually uses.
    Sort by GPIO number ascending. The label is the GPIO number.
- **Pin capability marks.** From `boards[].pins`, a pin can carry several marks.
  Draw a small 4 px dot beside the pin:
  - `input_only` → red (it cannot drive anything)
  - `adc2` → purple (it dies while WiFi is on)
  - `adc1` → green
  - `strapping` → amber
  - `uart0` / `boot` → blue
  - `flash_reserved` → these pins are never used; skip them entirely
- If a pin appears in `plan.signals` with `requested: true`, mark it with a small
  "you asked for this" glyph (a hollow ring) — it is the user's own choice, not the
  solver's.

### 5.3 Parts (x 700 → 1200)

- One box per distinct part id in the plan, ordered by the order the part first
  appears in `plan.signals` (deterministic).
- Box: 480 wide, 68 tall, rounded, with
  - the part name from the parts DB (not the id),
  - a meta line: `rail · peak current` (e.g. `external · 250 mA`), and for an I²C
    part its address (`0x3C`),
  - a "not measured" marker when `dims.confidence` is `clone-typical` — the tool
    says so out loud (rule R16), and it belongs on the part.
- **Connection ports**: each part needs one port per wire that reaches it, spaced
  12 px apart down the left edge of the box. The port for a signal is the pin it
  uses; the port for power is the rail it draws from. Ports are ordered:
  power first, then signals in `plan.signals` order. This ordering is what makes
  the drawing deterministic.

### 5.4 Wires

- Orthogonal polylines only: `M x1,y1 H mid V y2 H x2`, with a 6 px corner radius
  approximated by a quadratic curve at each corner. No diagonal lines.
- A **signal wire** runs from the pin on the board's right strip to the part's port.
  It is routed in the 60 px gutter between the board and the parts column, so wires
  never cross the board.
- A **power wire** runs from the rail card on the left to the part's power port.
  Power wires are routed in the gutter between the rails column and the board, and
  they must pass **behind** the board (draw them before the board group).
- A **bus trunk** is drawn when `plan.i2c.sda` is not null: a vertical line in the
  gutter next to the board's right strip, with a short stub from the SDA pin and
  from the SCL pin into the trunk, and one branch from the trunk to each device in
  `plan.i2c.devices`. The trunk is what rule R8 is about, so it is the thing that
  turns red.
- A **rejected wire** is drawn dashed, in a muted grey-red, for every violation that
  carries `gpio` and `moved_to`: it runs from the *rejected* pin to the same part.
  It is labelled `GPIO 25 → rejected`. This is the "you asked for 25, we moved it to
  35" story, and it is the clearest single idea in the whole panel.

### 5.5 Violation badges

One badge per violation, placed next to the wire it is about:

- `affected` tells you where it goes (see §7). Place the badge near the first
  affected wire, offset by 16 px so it does not overlap the line.
- The badge shows the rule id, and a **short label with the numbers** — the whole
  point is that the numbers are on screen:
  - R11 → `580 mA on a 300 mA rail`
  - R12 → `servo needs its own supply`
  - R8 → `two devices at 0x3C`
  - R5 → `ADC2 pin + WiFi → moved to 35`
- The badge text must fit in 260 px. Truncate with an ellipsis if it does not, and
  put the full text in a `<title>` element so a tooltip can show it.

---

## 6. The visual language

Dark theme, one accent colour, three severity colours. Use exactly these.

| Element | Colour | Notes |
|---|---|---|
| canvas background | `#0d1117` | |
| board body | fill `#161b22`, stroke `#30363d` | |
| neutral wire | `#6e7681` | 2 px |
| faulted wire | `#f85149` | 2.5 px |
| rejected wire | `#8b949e` | 1.5 px, `stroke-dasharray="6 4"` |
| bus trunk | `#58a6ff` | 3 px |
| power wire | `#7ee787` | 2 px |
| text | `#c9d1d9` | |
| muted text | `#8b949e` | |
| accent | `#58a6ff` | |
| FATAL | bg `#3d1418`, border/text `#ff7b72` | |
| WARN | bg `#3b2a12`, border/text `#e3b341` | |
| FIXED | bg `#12261e`, border/text `#3fb950` | |
| rail over budget | bar fill `#f85149` | |

Font: `system-ui, -apple-system, "Segoe UI", sans-serif`. Sizes: 13 px for part
names, 11 px for meta text, 11 px for badges, 10 px for pin labels.

**A faulted wire is never only red** — it also gets `stroke-dasharray="8 4"` and a
`data-fault` attribute, so the failure is legible without relying on colour alone.

---

## 7. How a violation maps to a wire

Every violation carries `affected`: a list of machine-readable references. This is
the contract that makes the drawing possible — the solver already produces it.

| `affected` ref | What to highlight |
|---|---|
| `{"kind": "signal", "part_id", "signal", "gpio", "moved_to"?}` | the wire from that GPIO to that part. If `moved_to` is present, the wire from `gpio` is the **rejected** one, and the live wire is the one from `moved_to` (the plan's `signals` already has it). |
| `{"kind": "part", "part_id", "name"?}` | every wire of that part: its signal wires and its power wire |
| `{"kind": "rail", "name"}` | that rail card and every power wire on that rail |
| `{"kind": "bus", "name": "i2c0"}` | the bus trunk and every branch of it |
| `{"kind": "i2c", "address", "part_id"}` | that device's branch of the bus, and its address badge |
| `{"kind": "envelope", "width_mm", "depth_mm"}` | the mechanical area — draw a dashed rectangle the size of the envelope with the area numbers on it |

A wire is faulted if **any** violation references it. A part is faulted if any
violation references the part or one of its wires. A rail card is faulted if a
violation references the rail or a part on it.

Two devices on the same address (R8) are two entries in `plan.i2c.devices` with the
same `address`. Give them distinct positions: sort the devices by address, then by
the order they appear, and offset the second and later ones of the same address
vertically by 18 px, so the collision is visible rather than overlapping.

---

## 8. The API the UI calls

These endpoints are the backend's contract. **The repo owner is implementing the
backend in parallel.** Build the UI against this contract; if an endpoint is not
there yet, stub it with a fixture and note it.

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/api/parts` | — | `[{id, name, price_idr_min, price_idr_max, price_date, power_rail, current_peak_ma, i2c_addr_default, dims_confidence, wokwi_name, has_source}]` |
| `POST` | `/api/spec` | `{"prompt": "..."}` | the validated spec object |
| `POST` | `/api/plan` | the spec object | the plan object (§3.1) |
| `POST` | `/api/plan.svg` | the spec object | `{"svg": "<svg…"}` (or the raw SVG with `image/svg+xml`) |
| `POST` | `/api/rebuild` | `{"spec": {...}, "rule_id": "R8", "fix_id": "A"}` | `{"spec": {...}, "plan": {...}}` — the fix applied and the plan re-solved |

`/api/rebuild` is the A/B/C picker. The mapping from a fix to a change in the spec
lives in the backend; the UI only posts the choice and re-renders what comes back.

**Offline:** every endpoint must work with `MODEL_PROVIDER=mock`. There is no
network dependency anywhere in the UI.

---

## 9. The three panels

| Panel | Width | Content | Interaction |
|---|---|---|---|
| **Left** — the catalogue | 280 px | every part in the database, with its rail, peak current, price band, and two badges: *measured* / *has a simulator* | a search box; clicking a part adds it to the spec and re-plans. **Type a part that is not in the list → it shows as "not in the database" → the plan refuses with R15.** That moment is worth building. |
| **Middle** — the plan | flex | the SVG of §4 | hovering a badge highlights the wires it is about; clicking a faulted wire scrolls the right panel to that violation |
| **Right** — the session | 380 px | the prompt box at the top; below it the model's spec (collapsible JSON), then the refusal card with the violations and their A/B/C options | typing a prompt calls `/api/spec`; picking a fix calls `/api/rebuild`; the middle panel updates |

The right panel must show the **spec JSON**, not a chat transcript. The point is
that the model's output is intent — no pins, no code — and the pins appear only
after the solver has allocated them. A transcript would imply a chatbot, which the
project rules ban.

---

## 10. Acceptance criteria

The work is done when all of these are true.

1. `render/svg.py` renders all three fixtures without raising.
2. **Determinism:** rendering the same plan twice produces byte-identical SVG
   (a test in `tests/test_svg.py`).
3. **No crash on a weird plan:** a plan with an unknown part, a null rail capacity
   and a signal with `gpio: null` still renders (a test).
4. Every violation in the flagship fixture produces a visible badge and at least
   one faulted wire. A test asserts: for each violation, at least one element in the
   SVG has `data-fault` containing that rule id, **or** the corresponding reference
   kind is one the panel does not draw (only `envelope` may be skipped).
5. The SVG contains no `<script>`, no `on*` attribute, and no external URL
   (`http`, `https://`, `//`).
6. The panel is legible at 1200 × 860 with no overlapping badges and no text
   overflowing its box.
7. The page runs from a clean clone with no build step:
   `pip install -r requirements.txt && uvicorn api.main:app --reload`.
8. The three panels work at 1440 × 900 (the demo resolution) and degrade to a
   stacked layout below 1100 px wide.

---

## 11. Build order

1. `render/svg.py` — board, pin strips, parts, plain wires. No faults yet.
   Check it against `plan_build.json` (the clean case) first: if the green case
   looks right, the geometry is right.
2. Bus trunk and power wires.
3. Faults: `data-fault` propagation from `affected`, the red wire, the badges.
4. The rejected wire for `moved_to`.
5. `web/index.html` + `style.css` + `app.js`: the three panels, the fetch loop,
   the A/B/C picker.
6. The left panel's catalogue and its R15 moment.
7. Polish: badge placement, text truncation, tooltips.

---

## 12. Open questions — decide, do not ask

- **Physical header positions.** The plan says GPIO, not "J3 pin 12". If a mapping
  from GPIO to the physical header is added to the board profile later, render it
  as a second label under the GPIO number. **Do not invent the pinout** — an
  incorrect header map is worse than no header map. Until it exists, GPIO numbers
  only.
- **Part icons.** No icons, no SVG assets per part. A name and a spec line are
  enough, and it keeps the whole thing deterministic.
- **Animation.** A CSS transition on the wires is fine. Do not animate in the SVG
  itself (`<animate>`), it breaks the byte-identical property.
