"""Check that a patch's performance controls do what their names promise.

For every macro that drives something, plus the mod wheel, velocity and
aftertouch when the patch uses them, render the same probe note at the low and
high end and report what measurably changed. Also writes a short "tour" MP3 per
control: the probe played at 0, 1/3, 2/3 and 1, back to back, so a person can
hear the sweep.

vita can't send aftertouch, so aftertouch is tested by temporarily swapping it
with the mod wheel (the patch's own mod-wheel routes then sit idle).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import ears as E
from . import patch as P
from . import render as R


@dataclass
class Control:
    key: str  # macro_control_1 | mod_wheel | velocity | aftertouch
    label: str


def controls_used(spec: dict) -> list[Control]:
    srcs = {m.get("source") for m in spec.get("mods", [])}
    out = []
    for k in range(1, 5):
        if f"macro_control_{k}" in srcs:
            m = spec.get("macros", {}).get(str(k), f"MACRO {k}")
            out.append(Control(f"macro_control_{k}", f"M{k} {m['name'] if isinstance(m, dict) else m}"))
    if "mod_wheel" in srcs:
        out.append(Control("mod_wheel", "Mod wheel"))
    if "aftertouch" in srcs:
        out.append(Control("aftertouch", "Aftertouch"))
    if "velocity" in srcs:
        out.append(Control("velocity", "Velocity"))
    return out


def _probe_play(spec: dict) -> dict:
    if "tour" in spec:
        return spec["tour"]
    notes, _ = R.parse_play(spec.get("play"))
    first = [n for n in notes if n.start == 0] or notes[:1]
    dur = min(max(n.dur for n in first), 1.5)
    return {"notes": [{"pitch": n.pitch, "start": 0, "dur": dur, "vel": n.vel} for n in first], "tail": 0.7}


def _variant(spec: dict, ctl: Control, value: float) -> tuple[dict, dict]:
    s = copy.deepcopy(spec)
    play = copy.deepcopy(_probe_play(spec))
    s.setdefault("params", {})
    # the control under test must not also be pinned by the probe's per-note "set"
    key = "mod_wheel" if ctl.key == "aftertouch" else ctl.key
    for holder in [play] + play.get("notes", []):
        if isinstance(holder.get("set"), dict):
            holder["set"] = {k: v for k, v in holder["set"].items() if k != key} or None
    if ctl.key == "velocity":
        for n in play.get("notes", []):
            n["vel"] = max(0.05, value)
        play["vel"] = max(0.05, value)
    elif ctl.key == "aftertouch":
        # swap the two sources: vita's aftertouch is always 0, so the patch's own
        # mod-wheel routes go quiet while aftertouch routes ride the wheel. Nothing is
        # removed, so modulation slot numbers (and "mod:<id>" targets) stay intact.
        swap = {"aftertouch": "mod_wheel", "mod_wheel": "aftertouch"}
        s["mods"] = [dict(m, source=swap.get(m.get("source"), m.get("source"))) for m in s["mods"]]
        s["params"]["mod_wheel"] = value
    else:
        s["params"][ctl.key] = value
    return s, play


def _render(spec: dict, play: dict) -> tuple[np.ndarray, float]:
    audio = R.render(P.to_vital_json(P.build(spec)), play)
    notes, _ = R.parse_play(play)
    return audio, max(n.dur for n in notes)


def _partial_shift(a: E.Listening, b: E.Listening) -> float | None:
    """Median pitch distance (cents) from each of a's strongest partials to the nearest in b."""
    fa = [float(p.split("Hz")[0]) for p in a.peaks[:6]]
    fb = [float(p.split("Hz")[0]) for p in b.peaks[:8]]
    if not fa or not fb:
        return None
    d = [min(abs(1200 * np.log2(x / y)) for y in fb) for x in fa]
    return float(np.median(d))


def _changes(a: E.Listening, b: E.Listening) -> list[str]:
    out = []

    def ratio(x, y):
        return (y + 1e-9) / (x + 1e-9)

    if abs(b.rms_db - a.rms_db) >= 1.5:
        out.append(f"level {a.rms_db:+.0f} -> {b.rms_db:+.0f} dB")
    r = ratio(a.centroid_hz, b.centroid_hz)
    if r > 1.2 or r < 1 / 1.2:
        out.append(f"brightness {a.centroid_hz} -> {b.centroid_hz} Hz (x{r:.2f})")
    if abs(b.hf_slope_db_oct - a.hf_slope_db_oct) >= 4:
        out.append(f"top-end slope {a.hf_slope_db_oct:+.0f} -> {b.hf_slope_db_oct:+.0f} dB/oct")
    if abs(b.attack_ms - a.attack_ms) >= max(15, 0.3 * min(a.attack_ms, b.attack_ms)):
        out.append(f"attack {a.attack_ms:.0f} -> {b.attack_ms:.0f} ms")
    da, db = a.decay_20db or 0, b.decay_20db or 0
    if (a.decay_20db is None) != (b.decay_20db is None) or abs(db - da) > 0.08:
        fmt = lambda v: "none" if v is None else f"{v:.2f}s"  # noqa: E731
        out.append(f"decay to -20 dB {fmt(a.decay_20db)} -> {fmt(b.decay_20db)}")
    if abs(b.pitch_wobble_cents - a.pitch_wobble_cents) >= 4:
        rate = lambda L: f" @ {L.vibrato_hz:.1f} Hz" if L.vibrato_hz else ""  # noqa: E731
        out.append(f"pitch wobble {a.pitch_wobble_cents:.0f}c{rate(a)} -> {b.pitch_wobble_cents:.0f}c{rate(b)}")
    if abs(b.autopan_db - a.autopan_db) >= 1.5:
        out.append(f"auto-pan {a.autopan_hz or 0:.1f} Hz/{a.autopan_db:.0f} dB -> {b.autopan_hz or 0:.1f} Hz/{b.autopan_db:.0f} dB")
    fa, fb = a.envelope_peaks_hz, b.envelope_peaks_hz
    if fa and fb and (len(fa) != len(fb) or any(abs(np.log2(x / y)) > 0.2 for x, y in zip(fa, fb))):
        out.append(f"spectral-envelope peaks {fa} -> {fb} Hz")
    if a.even_odd_db is not None and b.even_odd_db is not None and abs(b.even_odd_db - a.even_odd_db) >= 4:
        out.append(f"even vs odd harmonics {a.even_odd_db:+.0f} -> {b.even_odd_db:+.0f} dB")
    if a.tail_300ms_db is not None and b.tail_300ms_db is not None and abs(b.tail_300ms_db - a.tail_300ms_db) >= 3:
        out.append(f"level 300 ms after release {a.tail_300ms_db:+.0f} -> {b.tail_300ms_db:+.0f} dB")
    ra_, rb_ = a.release_60db, b.release_60db
    if (ra_ is None) != (rb_ is None) or (ra_ is not None and abs(rb_ - ra_) > max(0.15, 0.3 * ra_)):
        fmt = lambda v: "beyond the render" if v is None else f"{v:.2f}s"  # noqa: E731
        out.append(f"tail to -60 dB {fmt(ra_)} -> {fmt(rb_)}")
    if abs(b.width - a.width) >= 0.12:
        out.append(f"stereo width {a.width} -> {b.width}")
    if (a.tremolo_hz or b.tremolo_hz) and abs(b.tremolo_db - a.tremolo_db) >= 2:
        out.append(f"pulsing {a.tremolo_hz or 0:.1f} Hz/{a.tremolo_db:.0f} dB -> {b.tremolo_hz or 0:.1f} Hz/{b.tremolo_db:.0f} dB")
    acc = lambda L: (L.pulse_rate_late_hz / L.pulse_rate_early_hz) if L.pulse_rate_early_hz and L.pulse_rate_late_hz else 1.0  # noqa: E731
    if abs(acc(b) - acc(a)) > 0.2:
        out.append(f"pulse rate early->late x{acc(a):.2f} -> x{acc(b):.2f}")
    if (a.wobble_hz or b.wobble_hz) and abs(b.wobble_pct - a.wobble_pct) >= 15:
        out.append(f"brightness wobble ±{a.wobble_pct / 2:.0f}% -> ±{b.wobble_pct / 2:.0f}%")
    if a.roughness is not None and b.roughness is not None and abs(b.roughness - a.roughness) >= 0.04:
        out.append(f"roughness {a.roughness:.2f} -> {b.roughness:.2f}")
    cents = _partial_shift(a, b)
    if cents is not None and cents >= 12:
        out.append(f"partials shift by {cents:.0f} cents (median) - detune/bend")
    ra = ratio(a.attack_centroid_hz, b.attack_centroid_hz)
    if ra > 1.3 or ra < 1 / 1.3:
        out.append(f"onset brightness {a.attack_centroid_hz} -> {b.attack_centroid_hz} Hz")

    def names(L):  # note names of the strongest partials, cents dropped
        return [p.split()[1].rstrip("c").rstrip("0123456789").rstrip("+-") for p in L.peaks[:4]]

    if sorted(names(a)) != sorted(names(b)):
        out.append(f"strongest partials {' '.join(names(a))} -> {' '.join(names(b))}")
    if (a.glide_st_per_s or b.glide_st_per_s) and abs(b.glide_st_per_s - a.glide_st_per_s) > 1:
        out.append(f"pitch glide {a.glide_st_per_s:+.1f} -> {b.glide_st_per_s:+.1f} st/s")
    if abs(b.peak_db - a.peak_db) >= 3 and b.peak_db > -1:
        out.append(f"peak reaches {b.peak_db:+.1f} dBFS")
    return out


def tour(spec: dict, out_dir: Path | None = None) -> tuple[str, list[dict]]:
    """Report of what each control changes; optional tour WAVs in out_dir."""
    lines, files = [], []
    offline_blind = {"portamento_time", "portamento_slope", "legato", "portamento_force", "portamento_scale"}
    for ctl in controls_used(spec):
        dests = {m.get("dest") for m in spec.get("mods", []) if m.get("source") == ctl.key}
        if dests and dests <= offline_blind:
            msg = "not testable offline (glide needs overlapping notes; vita renders one note at a time)"
            lines.append(f"{ctl.label}: {msg}")
            files.append({"control": ctl.label, "file": None, "changes": msg, "range": ""})
            continue
        lo_v, hi_v = (0.3, 1.0) if ctl.key == "velocity" else (0.0, 1.0)
        renders = {}
        for v in (lo_v, hi_v):
            s, play = _variant(spec, ctl, v)
            audio, off = _render(s, play)
            renders[v] = (audio, E.listen(audio, R.SR, note_off=off))
        ch = _changes(renders[lo_v][1], renders[hi_v][1])
        change_text = "; ".join(ch) if ch else "NO MEASURABLE CHANGE"
        lines.append(f"{ctl.label} ({lo_v:g} -> {hi_v:g}): " + change_text)
        if out_dir is not None:
            steps = [lo_v + (hi_v - lo_v) * k / 3 for k in range(4)]
            parts = []
            for v in steps:
                s, play = _variant(spec, ctl, v)
                parts.append(_render(s, play)[0])
                parts.append(np.zeros((2, int(0.12 * R.SR)), np.float32))
            wav = out_dir / f"tour-{ctl.key}.mp3"
            R.write_mp3(np.concatenate(parts, axis=1), wav)
            files.append({"control": ctl.label, "file": wav.name, "steps": [round(v, 2) for v in steps],
                          "changes": change_text, "range": f"{lo_v:g} -> {hi_v:g}"})
    return "\n".join(lines), files
