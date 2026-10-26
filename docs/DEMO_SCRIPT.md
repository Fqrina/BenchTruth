# DEMO_SCRIPT.md — the 3-minute video

Judges watch dozens of these. The first 30 seconds decides whether they keep watching.
Record **two** videos: the full cut and a 2-minute backup (software only, no browser
simulation, no hardware).

## Shot list (full cut)

| # | Time | Shot | On screen / voiceover |
|---|---|---|---|
| 1 | 0:00–0:12 | Title card, then the tool | "This build was supposed to work. It doesn't." → cuts to the prompt box |
| 2 | 0:12–0:28 | The prompt typed in the web UI | *"ESP32 desk plant monitor: two OLEDs, a soil-moisture probe on GPIO 25, a servo vent, a buzzer. WiFi, and it has to run off the board."* |
| 3 | 0:28–0:42 | The spec appears (JSON), **pin column empty** | "Muse Spark writes the intent. Notice: no pins, no code, no geometry." |
| 4 | 0:42–1:15 | **The refusal card** | One violation at a time. Highlight the numbers: *two displays both want 0x3C*, *GPIO 25 is an ADC2 channel and WiFi is on*, *the servo wants 250 mA and the rail is rated 300 mA*. |
| 5 | 1:15–1:28 | The costed options; you click "A" | "Every refusal comes with a price. Pick one." → rebuild |
| 6 | 1:28–1:44 | The pin table **side by side** with the ESP32 capability table | "Every pin is justified: GPIO 33 is ADC1, GPIO 21/22 are the shared I²C bus, and the probe moved off ADC2." |
| 7 | 1:44–1:58 | **The compile gate** | The generated sketch compiles. Terminal output, zero errors, and the pins in the code match the pins in the plan. |
| 8 | 1:58–2:20 | **The simulation** | The approved build, running in a browser: two displays alive on separate addresses, the pot turning, the servo sweeping, the buzzer firing. |
| 9 | 2:20–2:32 | **The silicon receipt** | Cut to camera: the board, the LED blinking, the serial output. "This is the same firmware, on real hardware." |
| 10 | 2:32–2:44 | The teaching panel | "Why GPIO 33 · Why the servo needs its own supply · Why the probe moved off ADC2" |
| 11 | 2:44–2:56 | The eval table on screen | "20 conflicting specs, 20 correct refusals, 0 false refusals on valid builds." |
| 12 | 2:56–3:00 | Close | Repo link · "every part has a real source, a dated price, and a measurement you can check" |

## Rules for the recording

- **Screen-record the software and film the board separately**, then splice. One long
  take reads as an amateur demo; cuts read as a product.
- Show **real numbers on screen** (mA, pin numbers, addresses, prices). Vague claims
  read as fake.
- Keep the refusal card on screen long enough to read the *why*, not just the headline.
- No copyrighted music. Check the rules for what's allowed.
- Keep it under 3:00. Judges are not required to watch beyond 3 minutes.
- Public repo, `LICENSE` visible, no API keys in history.
- Have the project hosted and reachable — some judges will try to run it.
- **Do not claim the simulation proves the physics.** It proves *behaviour*. The mA and
  volt numbers come from the solver's arithmetic, and the video should say so.

## Backup cut (record on Oct 30, before anything else is finished)

Shots 1–7, 10 and 11. That is the entire argument without the browser simulation and
without the hardware. If the simulation or the board misbehaves on recording day, you
ship this and lose one scene, not the demo.

## The one sentence to say out loud

> "Anyone can prompt a chatbot for a wiring diagram. Only one of them will tell you your
> build is impossible — with the reason, the price, and a compile and simulation proof."
