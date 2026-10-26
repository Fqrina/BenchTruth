"""llm.spec_gen -- a prompt becomes a schema-validated project spec.

This is the only place a model is allowed to touch the project. It writes *intent*:
which parts, what each one is for, which constraints the user stated. It never
names a pin (except when the user asked for a specific one), never writes code and
never writes geometry. The solver does all of that.

The pipeline:

    prompt -> provider -> JSON -> schema validation -> (retry) -> validated spec
                                                  \-> (still broken) -> local parser

The local fallback parser is what makes the tool work with no key and no network:
it maps the words in the prompt onto parts that are actually in the database.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Optional

from jsonschema import Draft7Validator

from .providers import Provider, ProviderError, get_provider

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC_SCHEMA_PATH = ROOT / "spec" / "project_spec.schema.json"

SYSTEM_PROMPT = """\
You turn a hardware request into a project specification for an ESP32 build.

Rules you must follow, in order of importance:

1. You produce JSON only. One object, no prose, no code fences.
2. You state INTENT. You never assign a pin number, never write code, never
   describe geometry. If the user names a specific pin ("put the servo on GPIO 13"),
   record it in "requested_pins" and nothing else -- the solver will judge it.
3. Every part_id must be an id from the parts database. If the part is not there,
   use "UNKNOWN:<name>" so the tool refuses instead of guessing.
4. "signals_needed" says what the microcontroller must PROVIDE, never a pin number.
   Leave it out entirely and the part's default signals are used.
5. Only put a constraint in "constraints" if the user actually said it.

The object must validate against the schema you are given. Fields: board, goal,
peripherals[{part_id, role, count, power, address_preference, signals_needed}],
requested_pins[{part_id, signal, gpio}], constraints{power, connectivity,
i2c_pullup_mode, mechanical, budget_idr, assembly_level}, learning, notes."""


def load_spec_schema(path=SPEC_SCHEMA_PATH) -> dict:
    with pathlib.Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_spec(spec: dict, schema: Optional[dict] = None) -> list:
    """Return a list of human-readable problems. Empty means valid."""
    schema = schema or load_spec_schema()
    validator = Draft7Validator(schema)
    problems = []
    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        problems.append(f"{where}: {err.message}")
    return problems


def known_part_ids(db=None) -> list:
    if db is None:
        from benchtruth.db import load_db
        db = load_db()
    return sorted(db.raw.get("parts", []) and [p["id"] for p in db.raw["parts"]])


def build_prompt(user_text: str, board: str = "esp32-devkitc-v4", db=None) -> str:
    """The user prompt plus everything the model needs to answer it correctly."""
    parts = known_part_ids(db)
    board_json = json.dumps(board)
    parts_block = "\n".join(f"  - {p}" for p in parts)
    return (
        f"User request:\n{user_text}\n\n"
        f"Default board id: {board_json}\n\n"
        f"Part ids available in the parts database:\n{parts_block}\n\n"
        f"Reply with one JSON object that validates against this schema:\n"
        f"{json.dumps(load_spec_schema())}\n"
    )


def generate_spec(user_text: str, provider: Optional[Provider] = None, db=None,
                  schema: Optional[dict] = None, retries: int = 3) -> dict:
    """Prompt -> a validated spec. Falls back to the local parser if the model
    cannot produce one after `retries` attempts."""
    provider = provider or get_provider()
    schema = schema or load_spec_schema()
    prompt = build_prompt(user_text, db=db)
    try:
        return provider.chat_json(prompt, system=SYSTEM_PROMPT, retries=retries,
                                  validate=lambda s: validate_spec(s, schema))
    except ProviderError:
        return fallback_spec(user_text, db=db, schema=schema)


NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

_NON_BUS_SIGNALS = ("analog_in", "digital_in", "digital_out", "pwm_out")


def _phrase_in(text: str, phrase: str) -> bool:
    """True when `phrase` appears in `text` as whole words.

    Whole words matter: 'led' must not match inside 'oled'.
    """
    pat = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
    return re.search(pat, text.lower()) is not None


def _count_for(text: str, phrase: str, default: int = 1) -> int:
    """The number the user wrote in front of the phrase: 'two oled displays' -> 2."""
    numbers = "|".join(NUMBER_WORDS)
    pat = (r"(?:^|\b)(" + numbers + r")\s+(?:\w+[- ]){0,2}"
           + re.escape(phrase.lower()) + r"(?![a-z0-9])")
    m = re.search(pat, text.lower())
    return NUMBER_WORDS[m.group(1)] if m else default


def match_parts(text: str, db) -> dict:
    """Map the words in the prompt onto parts.

    Rules: whole-word matches only; a keyword is claimed by exactly one part
    (the first one in database order that lists it, so the cheaper/common part
    wins); the longest keyword a part matches is the one that is reported.

    Each result carries the position of the match, so a pin the user names can
    be attached to the part they named it next to.
    """
    claimed: dict = {}          # keyword -> part_id
    for pid, prof in db.profiles.items():
        for kw in sorted(prof.get("keywords", []), key=len, reverse=True):
            if kw in claimed:
                continue
            if _phrase_in(text, kw):
                claimed[kw] = pid
    per_part: dict = {}
    for kw, pid in claimed.items():
        if pid not in per_part or len(kw) > len(per_part[pid]["keyword"]):
            per_part[pid] = {"keyword": kw, "count": _count_for(text, kw),
                             "pos": re.search(
                                 r"(?<![a-z0-9])" + re.escape(kw.lower()) + r"(?![a-z0-9])",
                                 text.lower()).start()}
    return per_part


def fallback_spec(user_text: str, db=None, schema: Optional[dict] = None) -> dict:
    """The offline parser: map the words in the prompt onto real parts.

    It is deliberately simple and deliberately conservative. If it cannot find a
    part, it leaves it out rather than inventing one.
    """
    if db is None:
        from benchtruth.db import load_db
        db = load_db()
    schema = schema or load_spec_schema()
    text = user_text.lower()

    peripherals = []
    matched = match_parts(text, db)
    for pid, info in matched.items():
        prof = db.profile(pid)
        signals = [{"signal": s["signal"], "direction": s.get("direction", "out")}
                   for s in prof.get("default_signals", [])]
        entry = {"part_id": pid, "role": info["keyword"]}
        if info["count"] > 1:
            entry["count"] = info["count"]
        if signals:
            entry["signals_needed"] = signals
        peripherals.append(entry)

    constraints: dict = {}
    if "wifi" in text:
        constraints["connectivity"] = ["wifi"]
    if "ble" in text or "bluetooth" in text:
        constraints.setdefault("connectivity", []).append("ble")
    if any(p in text for p in ("run off the board", "board only", "from the board only")):
        constraints["power"] = {"external_supply_allowed": False}
    if "internal pull" in text:
        constraints["i2c_pullup_mode"] = "internal"
    constraints["mechanical"] = {"mount_style": "free"}

    spec = {
        "board": "esp32-devkitc-v4",
        "goal": user_text.strip()[:280] or "an ESP32 project",
        "peripherals": peripherals or [{"part_id": "UNKNOWN:none", "role": "unspecified"}],
        "constraints": constraints,
    }

    # A pin the user named explicitly. We record it; the solver judges it. It only
    # makes sense for a part that has a pin to assign -- a bus device (an OLED on
    # I2C) has its pins decided by the bus, not by the user. The part is the one in
    # the same clause as the pin: "a soil probe on GPIO 25, a servo" puts the pin on
    # the probe, not on the servo.
    pin = re.search(r"\bgpio\s*(\d{1,2})\b", user_text.lower())
    if pin:
        before = text[:pin.start()]
        clause = re.split(r"[,;.]|\band\b|\bwith\b|\bplus\b|\bthen\b", before)[-1]
        clause_start = before.rfind(clause)
        assignable = []
        for pid, info in matched.items():
            prof = db.profile(pid)
            kind = next((s["signal"] for s in prof.get("default_signals", [])
                         if s.get("signal") in _NON_BUS_SIGNALS), None)
            if kind:
                assignable.append((info["pos"], pid, kind))
        before_parts = [c for c in assignable if c[0] < pin.start()]
        same_clause = [c for c in before_parts if c[0] >= clause_start]
        pool = same_clause or before_parts
        if pool:
            # the part mentioned last before the pin
            pos, pid, kind = max(pool, key=lambda c: c[0])
            spec["requested_pins"] = [{"part_id": pid, "signal": kind,
                                       "gpio": int(pin.group(1))}]

    problems = validate_spec(spec, schema)
    if problems:
        raise ProviderError(
            "the local fallback parser could not build a valid spec: " + "; ".join(problems))
    return spec
