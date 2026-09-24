"""Blind match: hide a patch, keep only its audio, and recover the knobs by ear.

The optimiser sees the structure (saw -> filter, env_2 on cutoff) but not the
values. It only gets the spectral distance between its render and the target.

    uv run python experiments/blind_match.py
"""

import json
import time
from pathlib import Path

from vitalmake import controls as C
from vitalmake import ears as E
from vitalmake import patch as P
from vitalmake import render as R
from vitalmake import studio
from vitalmake.match import Free, match

HERE = Path(__file__).parent
PLAY = {"note": "A2", "dur": 0.6, "tail": 0.8}
STRUCTURE = [{"source": "env_2", "dest": "filter_1_cutoff", "amount": 0.3}]

hidden = {
    "name": "Hidden Pluck",
    "params": {
        "osc_1_unison_voices": 3, "osc_1_unison_detune": "15%", "osc_1_random_phase": "0%",
        "filter_1_on": "On", "filter_1_style": "24dB",
        "filter_1_cutoff": "700Hz", "filter_1_resonance": "55%",
        "env_1_attack": "0ms", "env_1_decay": "450ms", "env_1_sustain": 0.1,
        "env_2_attack": "0ms", "env_2_decay": "160ms", "env_2_sustain": 0,
        "modulation_1_amount": 0.33,
    },
    "mods": STRUCTURE,
    "play": PLAY,
}
FREE = [
    "filter_1_cutoff=60Hz..8kHz",
    "filter_1_resonance",
    "env_1_decay=20ms..3s",
    "env_1_sustain",
    "env_2_decay=10ms..2s",
    "modulation_1_amount=0..0.8",
]


def main():
    target = R.render(P.to_vital_json(P.build(hidden)), PLAY)
    R.write_wav(target, HERE / "hidden-target.wav")
    base = {
        "name": "Blind Guess",
        "params": {k: v for k, v in hidden["params"].items()
                   if k.split("=")[0] not in [f.split("=")[0] for f in FREE]},
        "mods": STRUCTURE,
        "play": PLAY,
    }
    free = [Free.parse(f) for f in FREE]
    t0 = time.time()
    spec, audio, hist = match(target, base, free, budget=900)
    elapsed = time.time() - t0
    spec["name"] = "Blind Match"
    res = studio.make(spec, slug="blind-match")
    base_audio = R.render(P.to_vital_json(P.build(base)), PLAY)

    rows = ["| control | hidden truth | recovered |", "|---|---|---|"]
    for f in free:
        truth = C.human(f.name, C.to_raw(f.name, hidden["params"][f.name]))
        rows.append(f"| `{f.name}` | {truth} | {spec['fitted'][f.name]} |")
    summary = "\n".join([
        f"# Blind match ({len(hist)} generations, {elapsed:.0f}s)",
        "",
        f"Spectral distance: starting guess {E.distance(target, base_audio):.3f} -> fitted {hist[-1]:.3f}",
        "",
        *rows,
    ])
    (HERE / "blind-match.md").write_text(summary + "\n")
    print(summary)
    print("\n" + res["report"])


if __name__ == "__main__":
    main()
