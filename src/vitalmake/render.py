"""Turn a patch + a "play" description into audio.

vita renders one note per call, so chords and sequences are rendered note by
note and mixed. Each note gets a fresh Synth loaded from the same preset JSON,
which makes renders deterministic and lets them run in parallel threads
(vita releases the GIL while rendering).

    "play": {"note": "C3", "dur": 1.5, "tail": 1.5}
    "play": {"chord": ["C3", "Eb3", "G3"], "dur": 3, "tail": 3, "vel": 0.7}
    "play": {"sequence": "C2 C2 _ Eb2 C2 _ G1 Bb1", "step": 0.18, "gate": 0.6, "tail": 1}
    "play": {"notes": [{"note": "C3", "start": 0, "dur": 1, "vel": 0.9}, ...], "tail": 2}
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
import vita

from .controls import note_to_midi

SR = 44100


@dataclass
class Note:
    pitch: int
    start: float
    dur: float
    vel: float = 0.8


def parse_play(play: dict | None) -> tuple[list[Note], float]:
    play = dict(play or {})
    vel = float(play.get("vel", 0.8))
    tail = float(play.get("tail", 1.5))
    notes: list[Note] = []
    if "notes" in play:
        for n in play["notes"]:
            notes.append(Note(note_to_midi(n.get("note", n.get("pitch", 48))), float(n.get("start", 0)),
                              float(n.get("dur", 1)), float(n.get("vel", vel))))
    elif "sequence" in play:
        step = float(play.get("step", 0.25))
        gate = float(play.get("gate", 0.8))
        tokens = play["sequence"].split() if isinstance(play["sequence"], str) else play["sequence"]
        for i, tok in enumerate(tokens):
            if tok in ("_", "-", "."):
                continue
            accent = tok.endswith("!")
            tok = tok.rstrip("!")
            notes.append(Note(note_to_midi(tok), i * step, step * gate, min(1.0, vel * (1.25 if accent else 1.0))))
    else:
        dur = float(play.get("dur", 1.5))
        chord = play.get("chord", [play.get("note", "C3")])
        for n in chord:
            notes.append(Note(note_to_midi(n), 0.0, dur, vel))
    return notes, tail


def render(preset_json: str, play: dict | None = None, sr: int = SR, threads: int = 8) -> np.ndarray:
    """Render to a float32 array shaped (2, samples)."""
    notes, tail = parse_play(play)
    total = max(n.start + n.dur for n in notes) + tail

    def one(n: Note) -> tuple[Note, np.ndarray]:
        synth = vita.Synth()
        synth.set_sample_rate(sr)
        synth.load_json(preset_json)
        return n, synth.render(n.pitch, n.vel, n.dur, n.dur + tail)

    out = np.zeros((2, int(total * sr) + 1), dtype=np.float32)
    with ThreadPoolExecutor(max_workers=max(1, min(threads, len(notes)))) as pool:
        for n, audio in pool.map(one, notes):
            i = int(n.start * sr)
            seg = audio[:, : out.shape[1] - i]
            out[:, i : i + seg.shape[1]] += seg
    return out


def write_wav(audio: np.ndarray, path: str | Path, sr: int = SR, normalize_db: float | None = -1.0) -> Path:
    """Write 24-bit WAV. Peak-normalizes to `normalize_db` dBFS unless None."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    a = audio.astype(np.float64)
    peak = np.abs(a).max()
    if normalize_db is not None and peak > 0:
        a *= 10 ** (normalize_db / 20) / peak
    sf.write(path, a.T, sr, subtype="PCM_24")
    return path


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), always_2d=True, dtype="float32")
    return data.T, sr
