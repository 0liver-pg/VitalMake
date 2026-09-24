"""Generate Vital wavetables and LFO shapes from compact, text-friendly specs.

A wavetable is up to 256 frames of 2048 samples; Vital interpolates between
keyframes. Each keyframe here is one small dict:

    {"shape": "saw"}                         basic shapes: sine saw square triangle pulse(width)
    {"harmonics": [1, 0, 0.33, 0, 0.2]}      additive: amplitude per partial (1-based)
    {"partials": 64, "falloff": 1, "odd": true}   1/n^falloff series, optional odd-only
    {"expr": "sin(2*pi*x + 2*sin(4*pi*x))"}  numpy expression over phase x in [0, 1)
    {"noise": 1, "seed": 3}                  a frozen random cycle (grit)
    {"text": "hello"}                        letters as harmonics: a=1/26 ... z=26/26 loudness,
                                             one partial per character, spaces are silent partials

Any frame may carry "position" (0-255) and "phases" (for harmonics, in cycles).
"""

from __future__ import annotations

import base64

import numpy as np

N = 2048
X = np.arange(N) / N


def _additive(amps, phases=None) -> np.ndarray:
    spec = np.zeros(N // 2 + 1, dtype=complex)
    for i, a in enumerate(amps):
        k = i + 1
        if k >= N // 2 or a == 0:
            continue
        ph = 0.0 if phases is None or i >= len(phases) else phases[i]
        # sin(2*pi*k*x + 2*pi*ph)
        spec[k] = a * (N / 2) * np.exp(1j * (2 * np.pi * ph - np.pi / 2))
    return np.fft.irfft(spec, n=N)


_SAFE = {
    name: getattr(np, name)
    for name in "sin cos tan tanh arctan exp log abs sign sqrt floor ceil clip where minimum maximum mod pi".split()
}


def frame(spec: dict) -> np.ndarray:
    if "shape" in spec:
        shape = spec["shape"]
        n_harm = 256
        k = np.arange(1, n_harm + 1)
        if shape == "sine":
            w = np.sin(2 * np.pi * X)
        elif shape == "saw":
            w = _additive(1 / k)
        elif shape == "square":
            w = _additive(np.where(k % 2 == 1, 1 / k, 0))
        elif shape == "triangle":
            w = _additive(np.where(k % 2 == 1, (-1) ** ((k - 1) // 2) / k**2, 0))
        elif shape == "pulse":
            width = spec.get("width", 0.25)
            w = _additive(np.sin(np.pi * k * width) / k * 2, phases=np.full(n_harm, 0.25))
        else:
            raise ValueError(f"unknown shape {shape!r}")
    elif "harmonics" in spec:
        w = _additive(spec["harmonics"], spec.get("phases"))
    elif "partials" in spec:
        n = int(spec["partials"])
        k = np.arange(1, n + 1, dtype=float)
        a = 1 / k ** spec.get("falloff", 1.0)
        if spec.get("odd"):
            a[1::2] = 0
        if "even_gain" in spec:
            a[1::2] *= spec["even_gain"]
        w = _additive(a, spec.get("phases"))
    elif "expr" in spec:
        w = eval(spec["expr"], {"__builtins__": {}}, {**_SAFE, "x": X, "np": np})  # noqa: S307
        w = np.broadcast_to(np.asarray(w, dtype=float), X.shape).copy()
    elif "noise" in spec:
        rng = np.random.default_rng(spec.get("seed", 0))
        w = rng.standard_normal(N)
        smooth = int(spec.get("smooth", 0))
        if smooth > 1:
            w = np.convolve(np.tile(w, 3), np.ones(smooth) / smooth, mode="same")[N : 2 * N]
    elif "text" in spec:
        amps = [((ord(ch) - 96) / 26 if "a" <= ch <= "z" else 0.0) for ch in spec["text"].lower()]
        w = _additive(amps, spec.get("phases"))
    else:
        raise ValueError(f"frame needs shape/harmonics/partials/expr/noise/text: {spec}")

    w = w - w.mean()
    peak = np.abs(w).max()
    return (w / peak if peak > 0 else w).astype("<f4")


def build(frames: list[dict], name: str = "Claude") -> dict:
    """Frames -> the JSON wavetable object Vital stores in a preset."""
    n = len(frames)
    keyframes = []
    for i, spec in enumerate(frames):
        pos = spec.get("position", 0 if n == 1 else round(i * 255 / (n - 1)))
        data = frame(spec)
        keyframes.append({"position": int(pos), "wave_data": base64.b64encode(data.tobytes()).decode()})
    keyframes.sort(key=lambda k: k["position"])
    return {
        "author": "",
        "full_normalize": True,
        "remove_all_dc": True,
        "name": name,
        "version": "1.0.7",
        "groups": [
            {
                "components": [
                    {"interpolation": 1, "interpolation_style": 1, "type": "Wave Source", "keyframes": keyframes}
                ]
            }
        ],
    }


def decode(wavetable: dict) -> list[tuple[int, np.ndarray]]:
    """Wavetable JSON -> [(position, samples)] for Wave Source keyframes."""
    out = []
    for g in wavetable.get("groups", []):
        for comp in g.get("components", []):
            for kf in comp.get("keyframes", []):
                if "wave_data" in kf:
                    out.append((kf["position"], np.frombuffer(base64.b64decode(kf["wave_data"]), dtype="<f4")))
    return out


# LFOs ------------------------------------------------------------------------
# Vital stores LFO points as (x, y) with y=0 at the TOP of the editor. Here
# "value" runs the intuitive way: 1 = top (max modulation), 0 = bottom.

def _lfo_points(shape: str, n: int = 32):
    t = np.linspace(0, 1, n)
    if shape == "sine":
        return list(zip(t, 0.5 - 0.5 * np.cos(2 * np.pi * t)))
    if shape == "triangle":
        return [(0, 0), (0.5, 1), (1, 0)]
    if shape in ("ramp_up", "saw_up"):
        return [(0, 0), (1, 1)]
    if shape in ("ramp_down", "saw_down"):
        return [(0, 1), (1, 0)]
    if shape == "square":
        return [(0, 1), (0.5, 1), (0.5, 0), (1, 0)]
    if shape == "decay":  # one-shot exponential fall, great with sync_type Envelope
        return list(zip(t, np.exp(-5 * t)))
    raise ValueError(f"unknown lfo shape {shape!r}")


def lfo(spec: dict) -> dict:
    """{"shape": "sine"} or {"points": [[x, value], ...], "powers": [...], "smooth": bool}."""
    pts = spec["points"] if "points" in spec else _lfo_points(spec["shape"])
    flat = []
    for x, v in pts:
        flat += [float(x), float(1.0 - v)]
    powers = spec.get("powers", [0.0] * len(pts))
    return {
        "name": spec.get("name", spec.get("shape", "Custom")),
        "num_points": len(pts),
        "points": flat,
        "powers": [float(p) for p in powers],
        "smooth": bool(spec.get("smooth", False)),
    }
