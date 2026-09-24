"""Human-unit access to Vital's 772 controls.

Vital stores every knob as a raw float with a hidden scaling (quartic envelope
times, exponential LFO rates, cutoff as a MIDI note...). This module converts
between what the GUI shows ("1.2 secs", "800 Hz", "Ladder") and the raw value,
so a patch can be written the way a person would describe it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache

import vita

SYNCED_RATES = ("Freeze", "32/1", "16/1", "8/1", "4/1", "2/1", "1/1", "1/2", "1/4", "1/8", "1/16", "1/32", "1/64")
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLATS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}


def note_to_midi(note: str | int) -> int:
    """'C4' -> 60, 'F#2' -> 42, 60 -> 60."""
    if isinstance(note, (int, float)):
        return int(note)
    m = re.fullmatch(r"\s*([A-Ga-g])([#b]?)(-?\d+)\s*", note)
    if not m:
        raise ValueError(f"not a note name: {note!r}")
    name = m.group(1).upper() + m.group(2)
    name = _FLATS.get(name, name)
    return NOTE_NAMES.index(name) + 12 * (int(m.group(3)) + 1)


def midi_to_note(midi: float) -> str:
    n = int(round(midi))
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"


def hz_to_midi(hz: float) -> float:
    return 69 + 12 * math.log2(hz / 440.0)


def midi_to_hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


@dataclass(frozen=True)
class Control:
    name: str
    display_name: str
    min: float
    max: float
    default: float
    scale: str  # linear | quadratic | cubic | quartic | square_root | exponential | indexed
    multiply: float
    offset: float
    units: str
    options: tuple[str, ...]
    discrete: bool

    @property
    def inverted(self) -> bool:
        """Vital displays exponential *_frequency knobs as a period (1/Hz)."""
        return self.scale == "exponential" and self.units == "secs" and self.name.endswith("frequency")

    @property
    def pitch_like(self) -> bool:
        """Raw value is a MIDI note number (filter cutoffs, EQ cutoffs, ...)."""
        return self.units == "semitones" and self.scale == "linear" and self.min >= 0 and self.max >= 100

    # raw <-> display --------------------------------------------------------
    def to_display(self, raw: float) -> float:
        s = self.scale
        if s == "quadratic":
            v = raw * raw
        elif s == "cubic":
            v = raw ** 3
        elif s == "quartic":
            v = raw ** 4
        elif s == "square_root":
            v = math.sqrt(max(raw, 0.0))
        elif s == "exponential":
            v = 2.0 ** raw
            if self.inverted:
                v = 1.0 / v
        else:
            v = raw
        return v * self.multiply + self.offset

    def from_display(self, disp: float) -> float:
        v = (disp - self.offset) / self.multiply
        s = self.scale
        if s == "quadratic":
            raw = math.sqrt(max(v, 0.0))
        elif s == "cubic":
            raw = math.copysign(abs(v) ** (1 / 3), v)
        elif s == "quartic":
            raw = max(v, 0.0) ** 0.25
        elif s == "square_root":
            raw = v * v
        elif s == "exponential":
            if v <= 0:
                raw = self.min
            else:
                raw = math.log2(1.0 / v) if self.inverted else math.log2(v)
        else:
            raw = v
        return raw

    def clamp(self, raw: float) -> float:
        raw = min(max(raw, self.min), self.max)
        return float(round(raw)) if self.discrete else raw

    def describe_range(self) -> str:
        if self.options:
            return " | ".join(self.options)
        lo, hi = self.to_display(self.min), self.to_display(self.max)
        if self.inverted:
            lo, hi = hi, lo
        extra = ""
        if self.pitch_like:
            extra = f" (= {midi_to_hz(self.min):.0f} Hz .. {midi_to_hz(self.max):.0f} Hz; accepts '800Hz' or 'A4')"
        elif self.inverted:
            extra = f" (= {2 ** self.min:.3g} Hz .. {2 ** self.max:.3g} Hz; accepts '2Hz' or '0.5s')"
        return f"{_fmt(lo)} .. {_fmt(hi)} {self.units}".rstrip() + extra


def _fmt(x: float) -> str:
    return f"{x:.4g}"


_SCALE = {
    "Linear": "linear",
    "Quadratic": "quadratic",
    "Cubic": "cubic",
    "Quartic": "quartic",
    "SquareRoot": "square_root",
    "Exponential": "exponential",
    "Indexed": "indexed",
}


@lru_cache(maxsize=1)
def catalog() -> dict[str, Control]:
    synth = vita.Synth()
    out = {}
    for name in synth.get_controls():
        d = synth.get_control_details(name)
        scale = _SCALE.get(str(d.scale).split(".")[-1], "linear")
        options = tuple(d.options)
        if name.endswith("_tempo") and len(options) < d.max + 1:
            # vita truncates the shared synced-rate list to (max - min + 1) names,
            # but raw values still index the full list (delay_tempo 9 = "1/8").
            options = SYNCED_RATES[: int(d.max) + 1]
        out[name] = Control(
            name=name,
            display_name=d.display_name,
            min=d.min,
            max=d.max,
            default=d.default_value,
            scale=scale,
            multiply=d.display_multiply,
            offset=d.post_offset,
            units=d.display_units.strip(),
            options=options,
            discrete=bool(d.is_discrete),
        )
    return out


def get(name: str) -> Control:
    try:
        return catalog()[name]
    except KeyError:
        close = search(name.replace("_", " "), limit=5)
        hint = f" Did you mean: {', '.join(c.name for c in close)}?" if close else ""
        raise KeyError(f"unknown control {name!r}.{hint}") from None


def search(query: str, limit: int = 30) -> list[Control]:
    words = query.lower().split()
    scored = []
    for c in catalog().values():
        hay = f"{c.name} {c.display_name}".lower()
        score = sum(w in hay for w in words)
        if score:
            scored.append((-score, len(c.name), c))
    scored.sort(key=lambda t: (t[0], t[1], t[2].name))
    return [c for *_, c in scored[:limit]]


_UNIT_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?(?:e-?\d+)?)\s*([a-zA-Z%]*)\s*$")


def to_raw(name: str, value) -> float:
    """Convert a human value into Vital's raw control value.

    Accepted forms:
      * number            -> the value the Vital GUI displays (secs, %, semitones, dB...)
      * "Ladder", "On"    -> option name for switch / menu controls
      * True / False      -> 1 / 0
      * "800Hz", "2kHz"   -> for cutoffs (pitch-like) and LFO/effect rates
      * "A4", "C#2"       -> note name for cutoff-style controls
      * "250ms", "1.5s"   -> times; for rate knobs a period
      * "40%", "-6dB", "12st"
      * {"raw": x} / "raw:x"   -> Vital's internal value, untouched
      * {"norm": x} / "norm:x" -> 0..1 knob position (VST-style)
    """
    c = get(name)
    if isinstance(value, bool):
        return c.clamp(1.0 if value else 0.0)
    if isinstance(value, dict):
        if "raw" in value:
            return c.clamp(float(value["raw"]))
        if "norm" in value:
            return c.clamp(c.min + float(value["norm"]) * (c.max - c.min))
        raise ValueError(f"{name}: unsupported value {value!r}")
    if isinstance(value, (int, float)):
        return c.clamp(c.from_display(float(value)))
    if not isinstance(value, str):
        raise ValueError(f"{name}: unsupported value {value!r}")

    v = value.strip()
    for i, opt in enumerate(c.options):
        if v.lower() == opt.lower():
            return float(i)
    if v.lower().startswith("raw:"):
        return c.clamp(float(v[4:]))
    if v.lower().startswith("norm:"):
        return c.clamp(c.min + float(v[5:]) * (c.max - c.min))
    if c.pitch_like and re.fullmatch(r"[A-Ga-g][#b]?-?\d+", v):
        return c.clamp(float(note_to_midi(v)))

    m = _UNIT_RE.match(v)
    if not m:
        opts = f" Options: {', '.join(c.options)}" if c.options else ""
        raise ValueError(f"{name}: can't parse {value!r}.{opts}")
    x, unit = float(m.group(1)), m.group(2).lower()

    if unit in ("hz", "khz"):
        hz = x * (1000 if unit == "khz" else 1)
        if c.pitch_like:
            return c.clamp(hz_to_midi(hz))
        if c.scale == "exponential" and c.name.endswith("frequency"):
            return c.clamp(math.log2(hz))
        raise ValueError(f"{name}: Hz makes no sense for this control ({c.describe_range()})")
    if unit in ("s", "sec", "secs", "ms"):
        secs = x / 1000 if unit == "ms" else x
        if c.units == "ms":
            return c.clamp(c.from_display(secs * 1000))
        if c.units == "secs":
            return c.clamp(c.from_display(secs))
        raise ValueError(f"{name}: time makes no sense for this control ({c.describe_range()})")
    if unit == "%":
        if c.units == "%" or c.multiply == 100:
            return c.clamp(c.from_display(x))
        return c.clamp(c.from_display(x / 100))
    if unit in ("db", "st", "semitones", "v", "voices", "cents", ""):
        return c.clamp(c.from_display(x))
    raise ValueError(f"{name}: unknown unit {unit!r} in {value!r}")


def human(name: str, raw: float) -> str:
    """Raw value -> short GUI-style text ("Ladder", "1.2 s", "830 Hz (+8.6 st)")."""
    c = get(name)
    if c.options:
        i = int(round(raw))
        return c.options[i] if 0 <= i < len(c.options) else str(i)
    d = c.to_display(raw)
    if c.pitch_like:
        return f"{midi_to_hz(raw):.0f} Hz ({midi_to_note(raw)})"
    if c.inverted:
        return f"{2 ** raw:.3g} Hz"
    units = c.units
    if units == "secs":
        return f"{d * 1000:.0f} ms" if d < 1 else f"{d:.3g} s"
    return f"{d:.3g}{(' ' + units) if units and units not in ('%',) else units}"
