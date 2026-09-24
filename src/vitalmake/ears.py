"""The ears: turn audio into numbers, words and a picture an LLM can read.

An LLM can't hear, so this module is its stand-in for listening. `listen()`
measures envelope, pitch, spectrum, motion and stereo image; `report()` turns
that into a short text description; `plot()` draws a spectrogram sheet that a
multimodal model can look at. The word labels are heuristics, not perception:
they're thresholds on the measurements, stated next to the numbers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .controls import hz_to_midi, midi_to_note

HOP = 512
NFFT = 4096


def _db(x, floor=1e-6):
    return 20 * np.log10(np.maximum(x, floor))


def note_name(hz: float) -> str:
    if not hz or hz <= 0:
        return "-"
    m = hz_to_midi(hz)
    cents = (m - round(m)) * 100
    return f"{midi_to_note(m)}{cents:+.0f}c"


def stft_mag(mono: np.ndarray, nfft: int = NFFT, hop: int = HOP) -> np.ndarray:
    pad = np.pad(mono, (nfft // 2, nfft // 2))
    n = 1 + (len(pad) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(n)[:, None]
    frames = pad[idx] * np.hanning(nfft)[None, :]
    return np.abs(np.fft.rfft(frames, axis=1))  # (frames, bins)


def _hf_slope(avg_power: np.ndarray, freqs: np.ndarray, lo: float = 2000, hi: float = 16000) -> float:
    """Top-end slope in dB per octave: a line fitted to the peak envelope of the
    average spectrum in 1/3-octave bands between `lo` and `hi`. Steeply falling
    (below about -10 dB/oct) reads as smooth; flat or rising reads as fizzy or harsh,
    because upper partials are as loud as the ones an octave below."""
    edges = lo * 2 ** (np.arange(0, np.log2(hi / lo) + 1e-9, 1 / 3))
    xs, ys = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = (freqs >= a) & (freqs < b)
        if sel.any() and avg_power[sel].max() > 0:
            xs.append(np.log2(np.sqrt(a * b)))
            ys.append(10 * np.log10(avg_power[sel].max()))
    if len(xs) < 3:
        return 0.0
    return float(np.polyfit(xs, ys, 1)[0])


def _envelope_peaks(avg_power: np.ndarray, freqs: np.ndarray, n: int = 3) -> list[float]:
    """Resonant peaks of the smoothed spectral envelope, 150 Hz-5 kHz: vowel formants,
    filter resonance bumps. Harmonics are smoothed away (1/3-octave running max+mean),
    so what's left is the shape a filter or a mouth imposes."""
    grid = 150 * 2 ** (np.arange(0, np.log2(5000 / 150) * 48) / 48)  # quarter-semitone grid
    lg = 10 * np.log10(np.interp(grid, freqs, avg_power) + 1e-20)
    k = 16  # 1/3 octave
    pad = np.pad(lg, k, mode="edge")
    mx = np.array([pad[i : i + 2 * k + 1].max() for i in range(len(lg))])
    sm = np.convolve(mx, np.ones(k) / k, mode="same")
    cand = [i for i in range(k, len(sm) - k) if sm[i] == sm[i - k : i + k + 1].max() and sm[i] > sm.max() - 24]
    cand.sort(key=lambda i: -sm[i])
    chosen: list[int] = []
    for i in cand:  # keep peaks at least half an octave apart
        if all(abs(i - j) >= 24 for j in chosen):
            chosen.append(i)
        if len(chosen) == n:
            break
    return sorted(round(float(grid[i])) for i in chosen)


def _odd_even(avg_power: np.ndarray, freqs: np.ndarray, f0: float) -> float | None:
    """Even-harmonic energy relative to odd (dB) for harmonics 2..16: very negative =
    square/clarinet-like hollow tone, near 0 = saw-like full tone."""
    if not f0 or f0 < 30:
        return None
    odd = even = 0.0
    for k in range(2, 17):
        sel = np.abs(freqs - k * f0) < max(0.03 * k * f0, 6)
        if not sel.any() or k * f0 > freqs[-1]:
            break
        e = avg_power[sel].max()
        if k % 2:
            odd += e
        else:
            even += e
    return float(10 * np.log10((even + 1e-20) / (odd + 1e-20))) if odd > 0 else None


def _onset_rate(fine: np.ndarray, fs: float, t0: int, t1: int) -> tuple[float, float]:
    """Pulse rate from level peaks (onsets) in the fine envelope: (early Hz, late Hz).
    Robust to accelerating gates, where a single periodicity doesn't exist."""
    seg = 20 * np.log10(fine[t0:t1] + 1e-6)
    if len(seg) < fs * 0.5:
        return 0.0, 0.0
    sm = np.convolve(seg, np.ones(9) / 9, mode="same")
    w = max(3, int(fs * 0.025))
    idx = [i for i in range(w, len(sm) - w) if sm[i] == sm[i - w : i + w + 1].max()
           and sm[i] - sm[i - w : i + w + 1].min() > 4]
    if len(idx) < 5:
        return 0.0, 0.0
    t = np.array(idx) / fs
    rates = 1 / np.diff(t)
    half = len(rates) // 2
    return float(np.median(rates[: max(half, 1)])), float(np.median(rates[half:]))


def _centroid(mag: np.ndarray, freqs: np.ndarray, range_db: float = 40.0) -> np.ndarray:
    """Magnitude-weighted spectral centroid per frame, ignoring bins more than
    `range_db` below the frame's loudest bin. Magnitude weighting tracks
    perceived brightness better than power weighting (which pins every saw near
    its 3rd harmonic); the gate stops faint broadband hiss from dominating it."""
    floor = mag.max(1, keepdims=True) * 10 ** (-range_db / 20)
    m = np.where(mag >= floor, mag, 0.0)
    return (m * freqs).sum(1) / (m.sum(1) + 1e-20)


def _f0_autocorr(x: np.ndarray, sr: int, fmin=30.0, fmax=2000.0) -> tuple[float, float]:
    """YIN-style f0 estimate. Returns (hz, clarity 0..1)."""
    x = x - x.mean()
    n = len(x)
    if n < 2048 or np.abs(x).max() < 1e-5:
        return 0.0, 0.0
    fft = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(fft * np.conj(fft))[:n]
    energy = np.cumsum(x[::-1] ** 2)[::-1]
    d = energy[0] + energy - 2 * ac  # difference function
    d[0] = 0
    lo, hi = int(sr / fmax), min(int(sr / fmin), n // 2)
    cmnd = d[1:hi] * np.arange(1, hi) / np.maximum(np.cumsum(d[1:hi]), 1e-12)
    cmnd = np.concatenate([[1.0], cmnd])
    # First dip that is nearly as deep as the deepest one: avoids locking onto a
    # loud formant/partial (too high) without jumping an octave down.
    gmin = cmnd[lo:hi].min()
    cand = np.where(cmnd[lo:hi] < max(0.2, gmin + 0.05) if gmin < 0.2 else cmnd[lo:hi] < gmin + 0.05)[0]
    cand = cand[cmnd[lo + cand] < gmin + 0.08] if len(cand) else cand
    if len(cand):
        tau = lo + cand[0]
        while tau + 1 < hi and cmnd[tau + 1] < cmnd[tau]:
            tau += 1
    else:
        tau = lo + int(np.argmin(cmnd[lo:hi]))
    if 1 <= tau < hi - 1:
        a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
        denom = a - 2 * b + c
        tau = tau + (0.5 * (a - c) / denom if denom != 0 else 0)
    clarity = float(max(0.0, 1 - cmnd[int(round(tau))]))
    return float(sr / tau), clarity


def _glide(mono: np.ndarray, sr: int, step_s: float = 0.025, nfft: int = 2048, hop: int = 256):
    """How the whole spectrum slides in pitch over time (cents per second).

    Resamples each frame onto a log-frequency axis (10-cent bins, 60 Hz-8 kHz) and
    finds the shift that best aligns frames `step_s` apart. Returns (median drift
    in semitones/s, fraction of steps moving the same way as the median).
    Catches Shepard tones, risers, pitch dives and glides that a single f0 misses.
    """
    mag = stft_mag(mono, nfft, hop)  # shorter frames than the main analysis: fast dives smear in 93 ms windows
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    e = _db(np.sqrt((mag**2).sum(1)))
    active = e > e.max() - 30
    grid = 120 * 2 ** (np.arange(0, np.log2(10000 / 120) * 1200, 10) / 1200)
    logspec = np.array([np.interp(grid, freqs, np.log(m + 1e-7)) for m in mag])
    d = max(1, int(step_s * sr / hop))
    shifts = []
    max_lag = 60  # +-600 cents per step
    for i in range(0, len(logspec) - d, d):
        if not (active[i] and active[i + d]):
            continue
        a, b = logspec[i] - logspec[i].mean(), logspec[i + d] - logspec[i + d].mean()
        best, best_lag = -np.inf, 0
        for lag in range(-max_lag, max_lag + 1):
            if lag >= 0:
                c = np.dot(a[: len(a) - lag], b[lag:])
            else:
                c = np.dot(a[-lag:], b[: len(b) + lag])
            if c > best:
                best, best_lag = c, lag
        shifts.append(best_lag * 10 / (d * hop / sr) / 100)  # semitones per second
    if len(shifts) < 4:
        return 0.0, 0.0
    shifts = np.array(shifts)
    med = float(np.median(shifts))
    agree = float(np.mean(np.sign(shifts) == np.sign(med))) if med else 0.0
    return med, agree


def _pitch_track(mono: np.ndarray, sr: int, t0: float, t1: float, hop_s: float = 0.02) -> np.ndarray:
    """Pitch offset in cents of each frame relative to the first, over [t0, t1].

    Each frame's log spectrum is whitened (harmonic peaks kept, spectral envelope
    removed) and cross-correlated with the reference frame on a 2-cent log grid.
    Works for chords and unison stacks as long as the whole sound moves together,
    which is what vibrato, tape wow and pitch bends do.
    """
    # 46 ms frames (short enough to follow a 6 Hz vibrato), zero-padded 4x so the
    # log-frequency interpolation is smooth
    nwin, nfft, hop = 2048, 8192, int(hop_s * sr)
    a, b = int(t0 * sr), int(t1 * sr)
    if b - a < nwin + 4 * hop:
        return np.zeros(0)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    grid = 150 * 2 ** (np.arange(0, np.log2(6000 / 150) * 1200, 2) / 1200)
    win = np.hanning(nwin)
    k = np.ones(151) / 151  # ~3 semitone smoothing for the envelope
    rows = []
    starts = list(range(a, b - nwin, hop))
    energy = np.array([np.sum(mono[i : i + nwin] ** 2) for i in starts])
    keep = energy > np.max(energy) * 10 ** (-12 / 10)  # drop frames 12 dB under the loudest (gate troughs)
    starts = [i for i, k in zip(starts, keep) if k]
    if len(starts) < 8:
        return np.zeros(0)
    for i in starts:
        m = np.log(np.abs(np.fft.rfft(mono[i : i + nwin] * win, nfft)) + 1e-7)
        g = np.interp(grid, freqs, m)
        rows.append(np.maximum(g - np.convolve(g, k, mode="same"), 0))
    ref = rows[0]
    lags = np.arange(-60, 61)  # +-120 cents
    out, conf = [], []
    for r in rows:
        c = np.array([np.dot(ref[max(0, -L) : len(ref) - max(0, L)], r[max(0, L) : len(r) - max(0, -L)]) for L in lags])
        j = int(np.argmax(c))
        conf.append(c[j] / (np.sqrt(np.dot(ref, ref) * np.dot(r, r)) + 1e-12))
        if 0 < j < len(c) - 1:  # parabolic refinement
            den = c[j - 1] - 2 * c[j] + c[j + 1]
            off = 0.5 * (c[j - 1] - c[j + 1]) / den if den != 0 else 0
        else:
            off = 0
        out.append((lags[j] + off) * 2)
    if np.median(conf) < 0.5:  # too little harmonic detail above 150 Hz to follow (dark bass, noise)
        return np.zeros(0)
    return np.array(out)


def _dominant_rate(sig: np.ndarray, fs: float, fmin=0.15, fmax=20.0):
    """Strongest periodicity in a control signal (envelope, brightness)."""
    if len(sig) < 16:
        return 0.0, 0.0
    t = np.arange(len(sig))
    sig = sig - np.polyval(np.polyfit(t, sig, 2), t)  # drop slow trends (decays, sweeps)
    spec = np.abs(np.fft.rfft(sig * np.hanning(len(sig)), 8 * len(sig)))
    f = np.fft.rfftfreq(8 * len(sig), 1 / fs)
    band = (f >= fmin) & (f <= fmax)
    if not band.any():
        return 0.0, 0.0
    i = np.argmax(np.where(band, spec, 0))
    depth = float(np.percentile(sig, 95) - np.percentile(sig, 5))
    # periodicity strength: peak vs median of band
    strength = float(spec[i] / (np.median(spec[band]) + 1e-12))
    return (float(f[i]), depth) if strength > 6 else (0.0, depth)


BANDS = [("sub", 20, 60), ("bass", 60, 250), ("low-mid", 250, 1000), ("mid", 1000, 4000),
         ("presence", 4000, 10000), ("air", 10000, 22050)]


@dataclass
class Listening:
    duration: float
    peak_db: float
    rms_db: float
    crest_db: float
    attack_ms: float
    rise50_ms: float
    peak_time: float
    sustain_db: float | None  # level just before note-off, relative to peak
    decay_20db: float | None  # seconds from peak until 20 dB down (before note-off)
    release_60db: float | None  # seconds after note-off until 60 dB below peak
    f0_hz: float
    f0_note: str
    pitch_clarity: float
    pitch_start: str
    pitch_end: str
    peaks: list[str]
    centroid_hz: float
    centroid_start: float
    centroid_end: float
    attack_centroid_hz: float
    onset_sweep: str
    rolloff_hz: float
    flatness: float
    hf_slope_db_oct: float
    envelope_peaks_hz: list
    even_odd_db: float | None
    tail_300ms_db: float | None
    roughness: float | None
    roughness_band_hz: float | None
    harmonicity: float | None
    bands: dict[str, float]
    tremolo_hz: float
    tremolo_db: float
    pulse_rate_early_hz: float
    pulse_rate_late_hz: float
    wobble_hz: float
    wobble_pct: float
    glide_st_per_s: float
    glide_consistency: float
    width: float
    pitch_wobble_cents: float
    vibrato_hz: float
    autopan_hz: float
    autopan_db: float
    correlation: float
    clipped: int
    timeline: list[dict] = field(default_factory=list)
    words: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def listen(audio: np.ndarray, sr: int = 44100, note_off: float | None = None) -> Listening:
    audio = np.atleast_2d(audio).astype(np.float64)
    if audio.shape[0] > audio.shape[1]:
        audio = audio.T
    left, right = audio[0], audio[-1]
    mono = 0.5 * (left + right)
    side = 0.5 * (left - right)
    dur = len(mono) / sr
    peak = np.abs(audio).max()
    rms = np.sqrt(np.mean(mono**2))

    mag = stft_mag(mono)
    freqs = np.fft.rfftfreq(NFFT, 1 / sr)
    times = np.arange(mag.shape[0]) * HOP / sr
    power = mag**2
    frame_e = power.sum(1)
    env = np.sqrt(frame_e / (np.hanning(NFFT) ** 2).sum() / (NFFT / 2))  # ~rms per frame
    env_db = _db(env)
    pk_i = int(np.argmax(env))
    pk_db = env_db[pk_i]
    active = env_db > pk_db - 50

    # envelope ---------------------------------------------------------------
    env_amp = env / (env.max() + 1e-12)
    # Attack is timed on a fine (3 ms) envelope; the STFT frames are too long.
    fine_hop = 32
    fine = np.sqrt(np.convolve(mono**2, np.ones(128) / 128, mode="same")[::fine_hop])
    fine /= fine.max() + 1e-12
    # "Arrived" level: 90% of the typical loud level, so LFO bumps on top of a
    # sustained note don't count as a slow attack.
    body_f = int((note_off if note_off else dur) * sr / fine_hop)
    plateau = min(1.0, float(np.percentile(fine[: max(body_f, 2)], 80)))
    f10 = int(np.argmax(fine >= 0.1 * plateau))
    f90 = int(np.argmax(fine >= 0.9 * plateau))
    attack_ms = max(0.0, (f90 - f10) * fine_hop / sr * 1000)
    rise50_ms = max(0.0, (int(np.argmax(fine >= 0.5 * plateau)) - f10) * fine_hop / sr * 1000)
    t10, t90 = f10 * fine_hop // HOP, f90 * fine_hop // HOP
    sustain_db = decay_20 = release_60 = None
    if note_off is not None and note_off < dur:
        off_i = min(int(note_off * sr / HOP), len(env_db) - 1)
        pre = max(pk_i, off_i - int(0.05 * sr / HOP))
        if note_off > 0.25:  # too short a note to have a sustain stage worth naming
            sustain_db = float(env_db[pre] - pk_db)
        after = np.where(env_db[off_i:] < pk_db - 60)[0]
        release_60 = float(after[0] * HOP / sr) if len(after) else None
        seg = env_db[pk_i:off_i]
    else:
        seg = env_db[pk_i:]
    tail_db = None
    if note_off is not None and note_off + 0.3 < dur:
        tail_db = float(env_db[min(int((note_off + 0.3) * sr / HOP), len(env_db) - 1)] - pk_db)
    down = np.where(seg < pk_db - 20)[0]
    decay_20 = float(down[0] * HOP / sr) if len(down) else None

    # spectrum ---------------------------------------------------------------
    w = frame_e * active
    centroid_t = _centroid(mag, freqs)
    centroid = float((centroid_t * w).sum() / (w.sum() + 1e-20))
    avg = (power * active[:, None]).sum(0) / max(active.sum(), 1)
    cum = np.cumsum(avg)
    rolloff = float(freqs[np.searchsorted(cum, 0.85 * cum[-1])])
    band = (freqs > 40) & (freqs < 12000)
    p = avg[band] + 1e-20
    flatness = float(np.exp(np.mean(np.log(p))) / np.mean(p))
    tot = avg.sum() + 1e-20
    bands = {name: round(float(avg[(freqs >= lo) & (freqs < hi)].sum() / tot * 100), 1) for name, lo, hi in BANDS}

    hf_slope = _hf_slope(avg, freqs)
    formants = _envelope_peaks(avg, freqs)

    # strongest spectral peaks (chord / partial content)
    amp = np.sqrt(avg)
    amp_db = _db(amp, 1e-12)
    loc = np.where((amp[1:-1] > amp[:-2]) & (amp[1:-1] > amp[2:]))[0] + 1
    loc = loc[(freqs[loc] > 25) & (amp_db[loc] > amp_db.max() - 40)]
    loc = loc[np.argsort(amp[loc])[::-1]][:8]
    peaks = []
    for i in sorted(loc):  # parabolic interpolation for sub-bin frequency
        a, b, c = amp_db[i - 1], amp_db[i], amp_db[i + 1]
        off = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0
        hz = (i + off) * sr / NFFT
        peaks.append(f"{hz:.0f}Hz {note_name(hz)} ({b - amp_db.max():.0f}dB)")

    # pitch ------------------------------------------------------------------
    body_end = note_off if note_off else dur
    a0 = int(min(max(pk_i * HOP / sr + 0.05, 0.05), body_end * 0.5) * sr)
    a1 = int(body_end * sr)
    body = mono[a0:a1] if a1 - a0 > 4096 else mono
    f0, clarity = _f0_autocorr(body[: min(len(body), 16384)], sr)
    track = []
    win = 4096
    for s in range(int(0.01 * sr), max(int(body_end * sr) - win, 1), int(0.05 * sr)):
        hz, cl = _f0_autocorr(mono[s : s + win], sr)
        if cl > 0.6:
            track.append(hz)
    p_start = note_name(np.median(track[:3])) if track else "-"
    p_end = note_name(np.median(track[-3:])) if track else "-"

    odd_even = _odd_even(avg, freqs, f0) if clarity > 0.75 else None
    harmonicity = None
    if f0 > 0 and clarity > 0.6:
        h = np.zeros_like(freqs, dtype=bool)
        for k in range(1, int(min(freqs[-1], 12000) / f0) + 1):
            h |= np.abs(freqs - k * f0) < max(0.03 * k * f0, 12)
        harmonicity = float(avg[h & band].sum() / (avg[band].sum() + 1e-20))

    # motion (during the held part of the note) -------------------------------
    fs_ctrl = sr / HOP
    s0 = int(min(t90 + 0.05 * fs_ctrl, len(env_db) - 1))
    s1 = int(note_off * fs_ctrl) if note_off else len(env_db)
    held = slice(s0, max(s1, s0 + 1))
    loud = np.where(env_db[held] > pk_db - 35)[0] if s1 > s0 else np.array([], dtype=int)
    trem_hz = trem_db = wob_hz = wob_oct = trem_early = trem_late = 0.0
    if len(loud) > 0.5 * fs_ctrl:  # need half a second of held sound to call it modulation
        held = slice(s0, s0 + loud[-1] + 1)
        trem_hz, trem_db = _dominant_rate(env_db[held], fs_ctrl)
        # pulse rate early vs late, from level peaks: catches accelerating gates
        fs_fine = sr / fine_hop
        if trem_db >= 6:  # only a real gate/tremolo has onsets worth counting
            trem_early, trem_late = _onset_rate(fine, fs_fine, int(s0 * HOP / fine_hop),
                                                int((s0 + loud[-1]) * HOP / fine_hop))
        log_c = np.log2(np.maximum(centroid_t[held], 20))
        wob_hz, wob_oct = _dominant_rate(log_c, fs_ctrl)
    on = int(t10)
    attack_c = float(np.median(centroid_t[on : on + max(2, int(0.03 * sr / HOP))]))
    c_act = centroid_t[active]
    c_start = float(np.median(c_act[: max(3, len(c_act) // 10)])) if len(c_act) else 0.0
    c_end = float(np.median(c_act[-max(3, len(c_act) // 10) :])) if len(c_act) else 0.0

    # two time scales: fast dives (zaps, kicks) and slow drifts (risers, Shepard tones)
    fast, slow = _glide(mono, sr), _glide(mono, sr, step_s=0.2, nfft=4096, hop=512)
    cands = [g for g in (fast, slow) if abs(g[0]) > 0.5 and g[1] > 0.6]
    glide_st, glide_agree = max(cands, key=lambda g: g[1]) if cands else (0.0, 0.0)

    rough = rough_hz = None
    if note_off is None or note_off >= 0.6:
        from .roughness import roughness as _rough

        # measured on the held part, after the attack transient
        r0 = t90 * HOP / sr + 0.05
        r1 = (note_off if note_off else dur) - 0.02
        if r1 - r0 >= 0.4:
            rough, rough_hz = _rough(audio, sr, start=r0, dur=min(1.0, r1 - r0))

    # onset pitch sweep (kicks, zaps): upward zero crossings of the first 200 ms
    sweep = ""
    if clarity > 0.7:
        seg = mono[f10 * fine_hop : f10 * fine_hop + int(0.2 * sr)]
        up = np.where((seg[:-1] < 0) & (seg[1:] >= 0))[0]
        if len(up) > 6:
            inst = sr / np.diff(up)
            f_first, f_last = float(np.median(inst[:2])), float(np.median(inst[-3:]))
            # must land on the detected pitch, else it's a filter sweep fooling the zero crossings
            lands = abs(f_last - f0) < 0.1 * f0
            ratio = max(f_first, f_last) / min(f_first, f_last)
            harmonic_jump = abs(ratio - round(ratio)) < 0.04 * ratio  # a bright overtone fading, not a sweep
            if lands and ratio > 1.5 and not harmonic_jump:
                k = np.argmax(np.abs(inst - f_last) < 0.1 * f_last)
                sweep = f"{f_first:.0f} Hz -> {f_last:.0f} Hz within {up[k + 1] / sr * 1000:.0f} ms"

    # stereo -----------------------------------------------------------------
    mid_rms = np.sqrt(np.mean(mono**2)) + 1e-12
    width = float(np.sqrt(np.mean(side**2)) / mid_rms)
    corr = float(np.corrcoef(left, right)[0, 1]) if np.std(left) > 0 and np.std(right) > 0 else 1.0

    # pitch wobble (vibrato, tape wow) during the held part
    vib_hz = vib_cents = 0.0
    if len(loud) > 0.5 * fs_ctrl and not (clarity > 0.75 and f0 < 80):  # skip deep bass: too few partials to track
        track = _pitch_track(mono, sr, s0 * HOP / sr, (s0 + loud[-1]) * HOP / sr)
        if len(track) > 16:
            t = np.arange(len(track))
            detr = track - np.polyval(np.polyfit(t, track, 1), t)
            vib_cents = float(np.percentile(detr, 95) - np.percentile(detr, 5))
            vib_hz, _ = _dominant_rate(detr, 1 / 0.02, fmin=0.3, fmax=12)
            if vib_cents < 4:
                vib_hz = 0.0

    # auto-pan: periodic swing of the left/right balance
    pan_hz = pan_db = 0.0
    if audio.shape[0] > 1 and len(loud) > 0.5 * fs_ctrl:
        frames = range(s0, s0 + loud[-1] + 1)  # 23 ms windows, fine enough for tremolo-rate panning
        eL = np.array([np.sum(left[i * HOP : i * HOP + 1024] ** 2) for i in frames])
        eR = np.array([np.sum(right[i * HOP : i * HOP + 1024] ** 2) for i in frames])
        bal = 10 * np.log10((eL + 1e-12) / (eR + 1e-12))
        pan_hz, pan_db = _dominant_rate(bal, fs_ctrl)
        if pan_db < 1.0:
            pan_hz = 0.0

    # coarse timeline --------------------------------------------------------
    timeline = []
    slices = 10
    for k in range(slices):
        a, b = int(k * len(env_db) / slices), int((k + 1) * len(env_db) / slices)
        e = frame_e[a:b].sum()
        timeline.append({
            "t": round(times[a], 2),
            "level_db": round(float(_db(np.sqrt(e / max(b - a, 1)) / np.sqrt((np.hanning(NFFT) ** 2).sum() * NFFT / 2)) - 0), 1),
            "centroid_hz": round(float((centroid_t[a:b] * frame_e[a:b]).sum() / (e + 1e-20))) if e > 1e-10 * frame_e.max() else 0,
        })

    L = Listening(
        duration=round(dur, 3), peak_db=round(float(_db(peak)), 1), rms_db=round(float(_db(rms)), 1),
        crest_db=round(float(_db(peak) - _db(rms)), 1), attack_ms=round(attack_ms, 1), rise50_ms=round(rise50_ms, 1),
        peak_time=round(pk_i * HOP / sr, 3),
        sustain_db=None if sustain_db is None else round(sustain_db, 1),
        decay_20db=None if decay_20 is None else round(decay_20, 3),
        release_60db=None if release_60 is None else round(release_60, 3),
        f0_hz=round(f0, 2), f0_note=note_name(f0) if clarity > 0.75 else "-", pitch_clarity=round(clarity, 2),
        pitch_start=p_start, pitch_end=p_end, peaks=peaks,
        centroid_hz=round(centroid), centroid_start=round(c_start), centroid_end=round(c_end),
        attack_centroid_hz=round(attack_c), onset_sweep=sweep,
        rolloff_hz=round(rolloff), flatness=round(flatness, 4), hf_slope_db_oct=round(hf_slope, 1), envelope_peaks_hz=formants,
        even_odd_db=None if odd_even is None else round(odd_even, 1),
        tail_300ms_db=None if tail_db is None else round(tail_db, 1),
        roughness=None if rough is None else round(rough, 3), roughness_band_hz=rough_hz,
        harmonicity=None if harmonicity is None else round(harmonicity, 3), bands=bands,
        tremolo_hz=round(trem_hz, 2), tremolo_db=round(trem_db, 1),
        pulse_rate_early_hz=round(trem_early, 2), pulse_rate_late_hz=round(trem_late, 2),
        wobble_hz=round(wob_hz, 2), wobble_pct=round((2 ** wob_oct - 1) * 100, 1),
        glide_st_per_s=round(glide_st, 2), glide_consistency=round(glide_agree, 2),
        width=round(width, 3), pitch_wobble_cents=round(vib_cents, 1), vibrato_hz=round(vib_hz, 2),
        autopan_hz=round(pan_hz, 2), autopan_db=round(pan_db, 1), correlation=round(corr, 3), clipped=int((np.abs(audio) > 0.999).sum()),
        timeline=timeline,
    )
    L.words = describe(L)
    return L


def describe(L: Listening) -> list[str]:
    w = []
    # envelope
    if L.attack_ms < 15 or L.rise50_ms < 4:
        w.append("percussive attack" if (L.decay_20db or 99) < 0.6 or L.release_60db is not None and L.sustain_db is None
                 else "hard attack")
    elif L.attack_ms < 120:
        w.append("soft attack")
    else:
        w.append(f"slow swell ({L.attack_ms / 1000:.1f}s attack)")
    if L.decay_20db is not None and L.decay_20db < 0.4:
        w.append("short, plucky decay")
    elif L.sustain_db is not None and L.sustain_db > -6:
        w.append("sustained")
    if L.release_60db is not None and L.release_60db > 1.5:
        w.append(f"long tail ({L.release_60db:.1f}s)")
    # tone
    c = L.centroid_hz
    w.append("dark" if c < 600 else "warm" if c < 1500 else "bright" if c < 3500 else "very bright / sizzly")
    if L.flatness > 0.3:
        w.append("noisy")
    elif L.flatness > 0.08:
        w.append("breathy / grainy")
    elif L.harmonicity is not None and L.harmonicity < 0.6:
        w.append("inharmonic / metallic")
    else:
        w.append("clean tone")
    if L.hf_slope_db_oct > -6 and L.centroid_hz > 400:
        w.append(f"fizzy top end ({L.hf_slope_db_oct:+.0f} dB/oct above 2 kHz)")
    elif L.hf_slope_db_oct < -14:
        w.append("smooth top end")
    if L.bands.get("sub", 0) + L.bands.get("bass", 0) > 60:
        w.append("bass-heavy")
    # motion
    if L.centroid_start and L.centroid_end:
        ratio = L.centroid_end / L.centroid_start
        if ratio > 1.6:
            w.append(f"opens up over time (x{ratio:.1f} brighter)")
        elif ratio < 0.6:
            w.append(f"closes down over time (x{1 / ratio:.1f} darker)")
    if L.tremolo_hz and L.tremolo_db > 1.5:
        w.append(f"pulsing ~{L.tremolo_hz:.1f} Hz ({L.tremolo_db:.0f} dB)")
    if L.wobble_hz and L.wobble_pct > 15:
        w.append(f"wobbling brightness ~{L.wobble_hz:.1f} Hz")
    if abs(L.glide_st_per_s) > 0.5 and L.glide_consistency > 0.6:
        w.append(f"spectrum glides {'up' if L.glide_st_per_s > 0 else 'down'} ({L.glide_st_per_s:+.1f} st/s)")
    if L.pitch_clarity >= 0.9 and L.pitch_start != "-" and L.pitch_end != "-":  # chords make this meaningless
        if abs(_cents(L.pitch_start) - _cents(L.pitch_end)) > 40:
            w.append(f"pitch moves {L.pitch_start} -> {L.pitch_end}")
    if L.pitch_wobble_cents >= 8:
        w.append(f"vibrato {L.pitch_wobble_cents:.0f}c @ {L.vibrato_hz:.1f} Hz" if L.vibrato_hz
                 else f"pitch drifts ({L.pitch_wobble_cents:.0f}c, tape-like)")
    if L.autopan_hz:
        w.append(f"auto-panning ~{L.autopan_hz:.1f} Hz")
    # space
    w.append("mono" if L.width < 0.05 else "narrow stereo" if L.width < 0.3 else "wide stereo" if L.width < 0.8 else "very wide")
    if L.correlation < 0:
        w.append("phasey (L/R anti-correlated: may vanish in mono)")
    if L.clipped:
        w.append(f"hot: {L.clipped} samples over 0 dBFS (turn volume down)")
    return w


def _cents(name: str) -> float:
    from .controls import note_to_midi

    import re

    m = re.fullmatch(r"([A-G]#?-?\d+)([+-]\d+)c", name)
    return note_to_midi(m.group(1)) * 100 + int(m.group(2)) if m else 0.0


def phrase_line(L: Listening) -> str:
    """One-line summary for a whole phrase (sequence/chord), next to a single-note report."""
    return (f"Phrase: {L.duration:.1f}s, peak {L.peak_db} dBFS, rms {L.rms_db} dBFS, centroid {L.centroid_hz} Hz, "
            f"width {L.width}, partials: " + "; ".join(p.split(" (")[0] for p in L.peaks[:8]))


def report(L: Listening, title: str = "") -> str:
    lines = []
    if title:
        lines.append(f"== {title} ==")
    lines.append("Character: " + ", ".join(L.words))
    env = f"attack {L.attack_ms:.0f} ms (half-level in {L.rise50_ms:.0f} ms), peak at {L.peak_time:.2f}s"
    if L.decay_20db is not None:
        env += f", -20 dB after {L.decay_20db:.2f}s"
    if L.sustain_db is not None:
        env += f", sustain {L.sustain_db:+.0f} dB"
    if L.release_60db is not None:
        env += f", release to -60 dB in {L.release_60db:.2f}s"
    lines.append(f"Level: peak {L.peak_db} dBFS, rms {L.rms_db} dBFS, crest {L.crest_db} dB | Envelope: {env}")
    if L.f0_note == "-":
        pitch = f"Pitch: no single clear pitch (chord, noise or inharmonic; clarity {L.pitch_clarity}); see partials"
    else:
        pitch = f"Pitch: {L.f0_note} ({L.f0_hz} Hz, clarity {L.pitch_clarity})"
    if L.f0_note != "-" and L.pitch_start != "-" and abs(_cents(L.pitch_start) - _cents(L.pitch_end)) > 40:
        pitch += f", start {L.pitch_start} -> end {L.pitch_end}"
    lines.append(pitch)
    lines.append("Strongest partials: " + "; ".join(L.peaks))
    h = f", harmonicity {L.harmonicity:.2f}" if L.harmonicity is not None else ""
    lines.append(f"Spectrum: centroid {L.centroid_hz} Hz (start {L.centroid_start} -> end {L.centroid_end}), "
                 f"85% rolloff {L.rolloff_hz} Hz, flatness {L.flatness:.3f}{h}, top-end slope {L.hf_slope_db_oct:+.1f} dB/oct (2-16 kHz)")
    if L.onset_sweep:
        lines.append(f"Onset pitch sweep: {L.onset_sweep}")
    if L.attack_centroid_hz > 1.8 * max(L.centroid_hz, 1):
        lines.append(f"Transient: first 30 ms is much brighter ({L.attack_centroid_hz} Hz) than the body - a click/zap/pitch-drop onset")
    shape = [f"spectral-envelope peaks {', '.join(str(f) for f in L.envelope_peaks_hz)} Hz"] if L.envelope_peaks_hz else []
    if L.even_odd_db is not None:
        shape.append(f"even vs odd harmonics {L.even_odd_db:+.0f} dB ({'hollow, square-like' if L.even_odd_db < -8 else 'full, saw-like'})")
    if L.tail_300ms_db is not None:
        shape.append(f"level 300 ms after release {L.tail_300ms_db:+.0f} dB re peak")
    if shape:
        lines.append("Shape: " + "; ".join(shape))
    if L.roughness is not None:
        lines.append(f"Roughness (20-150 Hz beating, held part): {L.roughness:.3f}, worst near {L.roughness_band_hz:.0f} Hz"
                     " (pure tone ~0, two sines 70 Hz apart ~0.32)")
    lines.append("Energy by band: " + ", ".join(f"{k} {v}%" for k, v in L.bands.items()))
    mot = []
    if L.tremolo_hz:
        mot.append(f"level pulses at {L.tremolo_hz} Hz ({L.tremolo_db} dB p-p)")
    if L.pulse_rate_early_hz and L.pulse_rate_late_hz and abs(L.pulse_rate_late_hz / L.pulse_rate_early_hz - 1) > 0.2:
        mot.append(f"pulse rate changes {L.pulse_rate_early_hz} -> {L.pulse_rate_late_hz} Hz across the note")
    if L.wobble_hz:
        mot.append(f"brightness wobbles at {L.wobble_hz} Hz (±{L.wobble_pct / 2:.0f}%)")
    if L.pitch_wobble_cents >= 6:
        kind = f"vibrato at {L.vibrato_hz} Hz" if L.vibrato_hz else "irregular drift (wow / random)"
        mot.append(f"pitch wobbles {L.pitch_wobble_cents:.0f} cents p-p, {kind}")
    if L.autopan_hz:
        mot.append(f"stereo image swings L/R at {L.autopan_hz} Hz ({L.autopan_db} dB balance p-p)")
    if abs(L.glide_st_per_s) > 0.5 and L.glide_consistency > 0.6:
        mot.append(f"partials glide {L.glide_st_per_s:+.1f} semitones/s ({L.glide_consistency:.0%} of the time)")
    lines.append("Motion: " + ("; ".join(mot) if mot else "no periodic modulation or glide detected"))
    lines.append(f"Stereo: width {L.width} (side/mid), L/R correlation {L.correlation}")
    lines.append("Timeline (t: level dB, centroid Hz): " + "  ".join(
        f"{p['t']}s:{p['level_db']:.0f}/{p['centroid_hz']}" for p in L.timeline))
    return "\n".join(lines)


def plot(audio: np.ndarray, path: str | Path, sr: int = 44100, title: str = "", L: Listening | None = None,
         note_off: float | None = None) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    audio = np.atleast_2d(audio)
    mono = audio.mean(0)
    mag = stft_mag(mono, nfft=2048, hop=256)
    freqs = np.fft.rfftfreq(2048, 1 / sr)
    t = np.arange(mag.shape[0]) * 256 / sr
    S = _db(mag / (mag.max() + 1e-12))

    fig = plt.figure(figsize=(12, 7.2), dpi=100, facecolor="#101418")
    gs = fig.add_gridspec(3, 4, height_ratios=[1, 3, 0.05], width_ratios=[3, 3, 3, 2], hspace=0.35, wspace=0.3)
    style = dict(color="#c9d1d9")

    ax0 = fig.add_subplot(gs[0, :3])
    tt = np.arange(audio.shape[1]) / sr
    ax0.plot(tt, mono, color="#58a6ff", lw=0.4, label="mid")
    if audio.shape[0] > 1:
        ax0.plot(tt, 0.5 * (audio[0] - audio[1]), color="#f78166", lw=0.4, alpha=0.7, label="side")
    ax0.legend(loc="upper right", fontsize=7, facecolor="#101418", labelcolor="#c9d1d9")
    ax0.set_xlim(0, tt[-1])
    ax0.set_title(title or "waveform", **style, loc="left", fontsize=11)
    ax0.set_ylabel("amp", **style)

    ax1 = fig.add_subplot(gs[1, :3], sharex=ax0)
    ax1.pcolormesh(t, freqs[1:], S.T[1:], vmin=-90, vmax=0, cmap="magma", shading="auto")
    ax1.set_yscale("log")
    ax1.set_ylim(30, sr / 2)
    ax1.set_ylabel("Hz", **style)
    ax1.set_xlabel("seconds", **style)
    power = mag**2
    cen = _centroid(mag, freqs)
    live = _db(np.sqrt(power.sum(1))) > _db(np.sqrt(power.sum(1))).max() - 50
    ax1.plot(t[live], cen[live], ".", ms=1.5, color="#7ee787", label="centroid")
    if note_off:
        for a in (ax0, ax1):
            a.axvline(note_off, color="#8b949e", ls="--", lw=0.8)
    ax1.legend(loc="upper right", fontsize=8, facecolor="#101418", labelcolor="#c9d1d9")

    ax2 = fig.add_subplot(gs[1, 3])
    avg = _db(np.sqrt((power).mean(0)))
    avg -= avg.max()
    ax2.plot(avg[1:], freqs[1:], color="#d2a8ff", lw=0.8)
    ax2.set_yscale("log")
    ax2.set_ylim(30, sr / 2)
    ax2.set_xlim(-90, 3)
    ax2.set_xlabel("dB (avg spectrum)", **style)
    if L:
        txt = "\n".join([L.f0_note, f"{L.centroid_hz} Hz ctr", f"width {L.width}"])
        ax2.text(-88, 40, txt, color="#c9d1d9", fontsize=8, va="bottom")
    ax3 = fig.add_subplot(gs[0, 3])
    ax3.axis("off")
    if L:
        ax3.text(0, 1, "\n".join(_wrap(", ".join(L.words), 34)), color="#c9d1d9", fontsize=8.5, va="top")

    for a in (ax0, ax1, ax2):
        a.set_facecolor("#0d1117")
        a.tick_params(colors="#8b949e", labelsize=8)
        for s in a.spines.values():
            s.set_color("#30363d")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return path


def _wrap(s: str, n: int) -> list[str]:
    out, line = [], ""
    for word in s.split(" "):
        if len(line) + len(word) + 1 > n:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return out + [line]


def distance(a: np.ndarray, b: np.ndarray, sr: int = 44100) -> float:
    """Multi-resolution log-magnitude spectrogram distance (lower = more similar)."""
    a, b = np.atleast_2d(a).mean(0), np.atleast_2d(b).mean(0)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    total = 0.0
    for nfft in (256, 1024, 4096):
        A, B = stft_mag(a, nfft, nfft // 4), stft_mag(b, nfft, nfft // 4)
        total += np.mean(np.abs(np.log(A + 1e-4) - np.log(B + 1e-4)))
        total += np.linalg.norm(A - B) / (np.linalg.norm(A) + 1e-9)
    return float(total / 3)
