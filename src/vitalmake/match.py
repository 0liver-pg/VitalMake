"""Fit patch parameters to a target sound (sound matching by optimisation).

The LLM picks the patch *structure* (which oscillators, filter model, which
modulations exist) and which knobs are free; CMA-ES then turns those knobs to
minimise a multi-resolution spectrogram distance to the target. This is the
"ears in the loop" version of sound design: no taste involved, only distance.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import cma
import numpy as np
import vita

from . import controls as C
from . import ears as E
from . import patch as P
from . import render as R


@dataclass
class Free:
    name: str
    lo: float  # raw
    hi: float  # raw

    @classmethod
    def parse(cls, text: str) -> "Free":
        name, _, rng = text.partition("=")
        c = C.get(name.strip())
        if rng:
            lo_s, hi_s = rng.split("..")
            lo, hi = C.to_raw(c.name, _num(lo_s)), C.to_raw(c.name, _num(hi_s))
        else:
            lo, hi = c.min, c.max
        return cls(c.name, min(lo, hi), max(lo, hi))

    def raw(self, u: float) -> float:
        return C.get(self.name).clamp(self.lo + float(np.clip(u, 0, 1)) * (self.hi - self.lo))


def _num(s: str):
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return s


def match(target: np.ndarray, base_spec: dict, free: list[Free], budget: int = 400, threads: int = 8,
          seed: int = 0, restarts: int = 2, log=print) -> tuple[dict, np.ndarray, list[float]]:
    base_json = P.to_vital_json(P.build(base_spec))
    notes, tail = R.parse_play(base_spec.get("play"))
    n = notes[0]  # matching uses the first note of the play block
    render_dur = n.dur + tail
    target_mono = np.atleast_2d(target)
    length = int(render_dur * R.SR)
    tgt = np.zeros((target_mono.shape[0], length), np.float32)
    k = min(length, target_mono.shape[1])
    tgt[:, :k] = target_mono[:, :k]
    tgt_norm = tgt / (np.abs(tgt).max() + 1e-9)

    def evaluate(u: np.ndarray) -> tuple[float, np.ndarray]:
        s = vita.Synth()
        s.load_json(base_json)
        ctl = s.get_controls()
        for f, x in zip(free, u):
            ctl[f.name].set(f.raw(x))
        a = s.render(n.pitch, n.vel, n.dur, render_dur)[:, :length]
        peak = np.abs(a).max()
        if peak < 1e-5:
            return 10.0, a
        return E.distance(tgt_norm, a / peak), a

    x0 = []
    for f in free:  # start from the base patch's value where one is given
        c = C.get(f.name)
        raw0 = C.to_raw(f.name, base_spec["params"][f.name]) if f.name in base_spec.get("params", {}) else c.default
        x0.append(float(np.clip((raw0 - f.lo) / (f.hi - f.lo + 1e-12), 0.05, 0.95)))
    best = (np.inf, None, None)
    history = []
    t0 = time.time()
    rng = np.random.default_rng(seed)
    per_run = budget // (restarts + 1)
    with ThreadPoolExecutor(threads) as pool:
        for run in range(restarts + 1):
            # run 0 starts from the base patch; restarts start from random points,
            # because knobs trade off (cutoff vs. envelope amount) and CMA-ES can
            # settle in the wrong valley
            start = x0 if run == 0 else list(rng.uniform(0.1, 0.9, len(free)))
            es = cma.CMAEvolutionStrategy(start, 0.3, {"bounds": [0, 1], "seed": seed + run + 1, "verbose": -9,
                                                       "popsize": max(8, 4 + int(3 * np.log(len(free))) * 2)})
            while es.countevals < per_run and not es.stop():
                xs = es.ask()
                results = list(pool.map(evaluate, xs))
                losses = [r[0] for r in results]
                es.tell(xs, losses)
                i = int(np.argmin(losses))
                if losses[i] < best[0]:
                    best = (losses[i], np.array(xs[i]), results[i][1])
                history.append(best[0])
                if len(history) % 10 == 0:
                    log(f"  run {run} evals {es.countevals:4d}  best distance {best[0]:.4f}  ({time.time() - t0:.0f}s)")
    spec = json.loads(json.dumps(base_spec))
    spec.setdefault("params", {})
    for f, x in zip(free, best[1]):
        raw = f.raw(x)
        c = C.get(f.name)
        spec["params"][f.name] = c.options[int(raw)] if c.options else {"raw": round(raw, 5)}
        spec.setdefault("fitted", {})[f.name] = C.human(f.name, raw)
    spec["fit_distance"] = round(best[0], 4)
    return spec, best[2], history


def match_cli(args) -> None:
    from . import studio

    target, sr = R.read_wav(args.target)
    if sr != R.SR:
        raise SystemExit(f"target must be {R.SR} Hz (got {sr})")
    base = json.loads(Path(args.base).read_text())
    free = [Free.parse(p) for p in args.param]
    d0 = None
    print(f"fitting {len(free)} controls with a budget of {args.budget} renders...")
    spec, audio, hist = match(target, base, free, budget=args.budget)
    spec["name"] = args.name or f"{base.get('name', 'Match')} (fitted)"
    res = studio.make(spec)
    print(res["report"])
    print("fitted:", json.dumps(spec["fitted"], indent=2))
    print(f"distance: start {hist[0]:.4f} -> best {hist[-1]:.4f}" if hist else d0)
