# Constraint Ruleset v0.1 — ESP32 DevKitC

Deterministic, code-implementable rules. Each rule has an ID (used by the test suite),
a severity, an auto-fix policy, and a refusal message template.

**Severity semantics**
- `FATAL` — the build physically cannot work as specified. Never silently fix. Refuse.
- `WARN` — works, but with a caveat the user must know about. Fix and report, or report and continue.
- `INFO` — worth telling the user, no action needed.

**Auto-fix policy**
- `AUTO` — the solver may fix it and report the change (e.g. pick a different free pin).
- `OFFER` — the solver must present costed options and let the user choose (e.g. add a level shifter).
- `NONE` — refuse. Do not guess.

---

## R1 — `PIN_OUT_ONLY`
**Severity:** FATAL · **Auto-fix:** AUTO
A signal output was assigned to an input-only GPIO (34–39 on ESP32).
Message: `GPIO {pin} is input-only on {board}. It cannot drive {signal}.`
Fix: reassign to a free PWM/digital-out capable pin.

## R2 — `PIN_FLASH_RESERVED`
**Severity:** FATAL · **Auto-fix:** AUTO
Pin 6–11 are wired to the SPI flash on ESP32 modules. Not usable.
Message: `GPIO {pin} is reserved for the SPI flash and is not exposed for peripherals.`

## R3 — `PIN_STRAPPING`
**Severity:** WARN · **Auto-fix:** AUTO
Boot-strapping pins (0, 2, 5, 12, 15) are sampled at reset. Using them can prevent the board from booting, or change flash mode.
Message: `GPIO {pin} is a boot-strapping pin (levels are sampled at reset). It works only if the board is reset with the right level.`
Fix: prefer a non-strapping pin; if the user insists, keep it and mark the build "requires a specific reset sequence".

## R4 — `PIN_UART_BOOT`
**Severity:** WARN · **Auto-fix:** NONE
GPIO 0, 1 (TX0), 3 (RX0) interfere with the boot log and USB serial, which you need to see when things go wrong.
Message: `GPIO {pin} is used by the USB serial / boot log. Wiring a load here can stop the board from booting or hide the error messages.`

## R5 — `ADC2_WIFI_CONFLICT`
**Severity:** FATAL · **Auto-fix:** AUTO
Analog reads on ADC2 pins (0, 2, 4, 12–15, 25–27) return garbage while WiFi is enabled.
Message: `GPIO {pin} is an ADC2 channel. ADC2 is unusable while WiFi is active, so the reading would be invalid in this build (WiFi is required).`
Fix: move the analog input to an ADC1 channel (32–39).

## R6 — `ANALOG_NOT_ADC`
**Severity:** FATAL · **Auto-fix:** AUTO
An analog sensor was placed on a digital-only pin.
Message: `GPIO {pin} cannot read an analog signal.`

## R7 — `PIN_DOUBLE_ASSIGNED`
**Severity:** FATAL · **Auto-fix:** AUTO
Two different functions on the same pin.
Message: `GPIO {pin} is already used by {other}. Every peripheral needs its own pin.`

## R8 — `I2C_ADDR_COLLISION`
**Severity:** FATAL · **Auto-fix:** OFFER
Two devices on the same bus resolved to the same address.
Message: `{part_a} and {part_b} both resolve to I2C address {addr}. A bus can hold only one device per address.`
Options (costed, in order of preference):
1. Change the address strap of one device if the part supports an alternative → `AUTO`
2. Add a TCA9548A I2C multiplexer → `OFFER` (+ part, + cost)
3. Drop one of the two devices → `OFFER`

## R9 — `I2C_MISSING_PULLUP`
**Severity:** WARN · **Auto-fix:** OFFER
I2C bus has no pull-up resistors and the module does not have them on-board.
Message: `The I2C bus needs 4.7 kΩ pull-ups on SDA and SCL. {part} does not have them on-board.`
Fix: offer a 4.7 kΩ pull-up pair (2 cents).

## R10 — `LEVEL_MISMATCH`
**Severity:** FATAL · **Auto-fix:** OFFER
A 5 V output is wired into a 3.3 V input, or the reverse.
Message: `{part_a} drives {signal} at {v} V, but the ESP32 pin is 3.3 V tolerant. Connecting them directly can damage the board.`
Options:
1. Add a 4-channel BSS138 level shifter → `OFFER` (+ part, + cost)
2. Use a resistor divider on the specific signal → `OFFER` (only for slow, one-way signals)
3. Swap to a 3.3 V-native variant of the part → `OFFER` (if it exists in the DB)

## R11 — `RAIL_POWER_BUDGET`
**Severity:** FATAL · **Auto-fix:** OFFER
Total peak current on a rail exceeds the rail's recommended capacity.
Message: `The 3V3 rail on {board} is recommended for {cap} mA. This build asks for {total} mA peak ({breakdown}), which is {over}x over budget.`
Fix options: move the load to VIN (5 V) with a common ground, or declare an external supply.

## R12 — `MOTOR_ON_LOGIC_RAIL`
**Severity:** FATAL · **Auto-fix:** OFFER
A servo, motor, relay coil, or LED strip is powered from the 3.3 V logic rail.
Message: `{part} needs up to {peak} mA. The 3V3 rail cannot supply that, and the stall current will brown out the ESP32.`
Fix: separate supply + common ground. For a breadboard build, say so plainly.

## R13 — `MISSING_FLYBACK`
**Severity:** FATAL · **Auto-fix:** OFFER
An inductive load (relay coil, solenoid, stepper, motor) without a flyback path.
Message: `{part} is inductive. Without a flyback diode the collapsing field produces a voltage spike that can kill the ESP32 pin or reset the board.`
Fix: add a 1N4007 across the coil (or note that the ULN2003 board already includes them).

## R14 — `MECH_FIT`
**Severity:** FATAL · **Auto-fix:** OFFER
The part's footprint (measured bbox + holes + keepouts) does not fit the chosen plate/cavity.
Message: `{part} needs {w} x {d} mm plus {keepout} clearance. The available area at {location} is {avail_w} x {avail_d} mm.`
Fix: move the part to a free grid position, shrink the layout, or use an adapter plate.

## R15 — `PART_UNKNOWN`
**Severity:** FATAL · **Auto-fit:** NONE
A part is not in the parts database.
Message: `{part} is not in the verified parts database, so its pinout, voltage, current and dimensions are unknown. I will not guess a build around a part I cannot verify.`
Fix: offer to add it (with a measurement task), or swap for a known equivalent.

## R16 — `DIM_UNMEASURED`
**Severity:** WARN · **Auto-fix:** NONE
The part exists in the DB but its dimensions are still `clone-typical`, not `measured`.
Message: `Mechanical dimensions for {part} are from a similar clone, not from your actual unit. The mount may be off by up to {tol} mm.`
Fix: offer a 3 mm tolerance grid / adapter plate so an error is still printable, or list the measurement task.

---

## Refusal message template

```
❌ CANNOT BUILD AS SPECIFIED
{board} · {n} peripherals

{rule_id}: {one-line diagnosis}

Why it matters:
  {consequence in physical terms, not jargon}

{auto-fix block, if applicable}
  A. {option} · {cost} · {extra effort}
  B. {option} · {cost} · {extra effort}
  C. {option} · {cost} · {extra effort}

Pick one (A/B/C) and I will rebuild, recompile and re-simulate.
```

## The refusal is the product

A tool that always says yes is a generator. A tool that says "no, and here is the physics,
the cost, and the two ways out" is an engineer. Every FATAL rule must produce a
refusal with at least one concrete way out. A refusal without a way out is a dead end —
and a bad demo.

## R17 - `ANALOG_OVER_RANGE`
**Severity:** FATAL · **Auto-fix:** OFFER
A 5 V analog source would drive the ESP32 ADC past its 3.3 V full scale.
Message: `{part} analog output can exceed the 3.3 V ADC range.`
Fix: measure the actual output and add a resistor divider, or power the sensor from 3.3 V if it allows.

---

## Verdict derivation (normative, mirrors SPEC.md section 7)

| Autofix | Applied? | Verdict |
|---|---|---|
| NONE | - | REFUSE if FATAL, else WARN |
| OFFER | - | OFFER |
| AUTO | yes | FIXED |
| AUTO | no | WARN |

Overall verdict = most severe of REFUSE > OFFER > FIXED > WARN > BUILD.
