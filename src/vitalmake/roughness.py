"""Sensory roughness: the buzzy, grating quality psychoacoustics links to harshness.

Roughness comes from partials close enough to beat inside one critical band,
at 20-150 Hz (strongest near 70 Hz). Slower beating (unison detune under
~15 Hz) is "fluctuation" and reads as warmth or movement, not harshness.

Method (a light version of Daniel & Weber 1997): split the signal into
1/3-octave bands, take each band's Hilbert envelope, measure how much of the
envelope's energy sits at 20-150 Hz (weighted toward 70 Hz), and average the
band modulation depths weighted by band loudness. 0 = smooth; a pure tone ~0;
two equal sines 70 Hz apart ~1.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt

CENTERS = 125 * 2 ** (np.arange(0, 19) / 3)  # 125 Hz .. 8 kHz


def _mod_weight(f):
    # peaks at 70 Hz, falls to ~0 at 20 and 200 Hz (log-Gaussian)
    return np.exp(-0.5 * (np.log2(np.maximum(f, 1) / 70) / 0.7) ** 2) * ((f > 15) & (f < 250))


def roughness(audio: np.ndarray, sr: int = 44100, start: float = 0.05, dur: float = 1.0) -> tuple[float, float]:
    """Returns (roughness 0..~1, frequency in Hz of the roughest band)."""
    mono = np.atleast_2d(audio).mean(0).astype(np.float64)
    a = int(start * sr)
    seg = mono[a : a + int(dur * sr)]
    if len(seg) < sr // 4 or np.abs(seg).max() < 1e-5:
        return 0.0, 0.0
    seg = seg / (np.abs(seg).max() + 1e-12)
    depths, weights = [], []
    for fc in CENTERS:
        lo, hi = fc / 2 ** (1 / 6), min(fc * 2 ** (1 / 6), sr / 2 * 0.95)
        sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
        band = sosfiltfilt(sos, seg)
        env = np.abs(hilbert(band))[::22]  # ~2 kHz envelope rate
        fs_env = sr / 22
        mean = env.mean()
        if mean < 1e-6:
            depths.append(0.0)
            weights.append(0.0)
            continue
        spec = np.abs(np.fft.rfft((env - mean) * np.hanning(len(env))))
        f = np.fft.rfftfreq(len(env), 1 / fs_env)
        # amplitude of modulation relative to the mean (hann window gain 0.5)
        mod = np.sqrt(np.sum((spec * _mod_weight(f)) ** 2)) / (0.5 * len(env)) / mean
        depths.append(float(mod))
        weights.append(float(np.sqrt(np.mean(band**2))) ** 0.6)  # rough loudness weighting
    depths, weights = np.array(depths), np.array(weights)
    if weights.sum() == 0:
        return 0.0, 0.0
    r = float((depths * weights).sum() / weights.sum())
    worst = float(CENTERS[int(np.argmax(depths * weights))])
    return r, worst
