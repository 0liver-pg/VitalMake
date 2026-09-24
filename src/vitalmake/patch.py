"""Patch specs: a compact JSON description of a Vital preset in human units.

    {
      "name": "Glass Choir",
      "description": "what it should sound like",
      "params":  {"osc_1_unison_voices": 7, "filter_1_cutoff": "900Hz", "env_1_attack": "0.8s"},
      "wavetables": {"osc_1": [{"shape": "saw"}, {"harmonics": [1, 0.5, 0.3]}]},
      "lfos": {"lfo_1": {"shape": "sine"}},
      "mods": [{"source": "lfo_1", "dest": "filter_1_cutoff", "amount": 0.2, "bipolar": true}],
      "macros": {"1": "Brightness"},
      "play": {"chord": ["C3", "G3", "E4"], "dur": 3, "tail": 3}
    }

Everything except "params" is optional. Unknown keys are kept as notes.
"""

from __future__ import annotations

import json
from pathlib import Path

import vita

from . import controls as C
from . import wavetable as W

VITAL_VERSION = "1.5.5"
MOD_SOURCES = vita.get_modulation_sources()
MOD_DESTINATIONS = vita.get_modulation_destinations()


class PatchError(ValueError):
    pass


def load_spec(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def _mod_amount(dest: str, amount) -> float:
    """Amount as a fraction of the destination's full range (-1..1).

    Also accepts "+24st" / "-12st" for pitch-like destinations and "50%" / "-50%".
    """
    if isinstance(amount, (int, float)):
        return float(amount)
    s = str(amount).strip().lower()
    if s.endswith("st"):
        c = C.get(dest) if dest in C.catalog() else None
        span = (c.max - c.min) if c else 1.0
        return float(s[:-2]) / span
    if s.endswith("%"):
        return float(s[:-1]) / 100
    return float(s)


def build(spec: dict, synth: vita.Synth | None = None) -> vita.Synth:
    """Apply a patch spec to a (fresh) Synth and return it."""
    synth = synth or vita.Synth()
    synth.load_init_preset()
    controls = synth.get_controls()
    errors = []

    for name, value in spec.get("params", {}).items():
        try:
            raw = C.to_raw(name, value)  # validates the name, with suggestions
            controls[name].set(raw)
        except (KeyError, ValueError) as e:
            errors.append(str(e).strip('"'))

    for i, mod in enumerate(spec.get("mods", []), start=1):
        src, dst = mod.get("source"), mod.get("dest")
        if src not in MOD_SOURCES:
            errors.append(f"mod {i}: unknown source {src!r}; sources: {', '.join(MOD_SOURCES)}")
            continue
        if dst not in MOD_DESTINATIONS:
            close = [d for d in MOD_DESTINATIONS if dst and dst.split("_")[-1] in d][:6]
            errors.append(f"mod {i}: unknown destination {dst!r}; similar: {close}")
            continue
        if not synth.connect_modulation(src, dst):
            errors.append(f"mod {i}: could not connect {src} -> {dst} (duplicate?)")
            continue
        slot = sum(1 for m in json.loads(synth.to_json())["settings"]["modulations"] if m["source"])
        p = f"modulation_{slot}_"
        controls[p + "amount"].set(max(-1.0, min(1.0, _mod_amount(dst, mod.get("amount", 0.5)))))
        controls[p + "bipolar"].set(1.0 if mod.get("bipolar") else 0.0)
        controls[p + "stereo"].set(1.0 if mod.get("stereo") else 0.0)
        controls[p + "power"].set(float(mod.get("power", 0.0)))

    if errors:
        raise PatchError("patch problems:\n  - " + "\n  - ".join(errors))

    # Things the Python API doesn't reach: edit the preset JSON directly.
    preset = json.loads(synth.to_json())
    st = preset["settings"]
    for osc, frames in spec.get("wavetables", {}).items():
        idx = int(osc.split("_")[-1]) - 1
        name = frames.get("name", osc) if isinstance(frames, dict) else f"{spec.get('name', 'Claude')} {idx + 1}"
        frame_list = frames["frames"] if isinstance(frames, dict) else frames
        st["wavetables"][idx] = W.build(frame_list, name=name)
    for lfo_name, lspec in spec.get("lfos", {}).items():
        st["lfos"][int(lfo_name.split("_")[-1]) - 1] = W.lfo(lspec)
    for k, label in spec.get("macros", {}).items():
        preset[f"macro{k}"] = label
    preset["preset_name"] = spec.get("name", "Untitled")
    preset["author"] = spec.get("author", "Claude")
    preset["comments"] = spec.get("description", "")
    preset["preset_style"] = spec.get("style", "Experimental")
    if not synth.load_json(json.dumps(preset)):
        raise PatchError("Vital rejected the generated preset JSON")
    return synth


def to_vital_json(synth: vita.Synth) -> str:
    preset = json.loads(synth.to_json())
    preset["synth_version"] = VITAL_VERSION  # vita reports 99999.9.9, which the plugin would flag
    return json.dumps(preset)


def save_vital(synth: vita.Synth, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_vital_json(synth))
    return path


# Reading existing presets back into words -------------------------------------

_INIT_CACHE: dict | None = None


def _init_settings() -> dict:
    global _INIT_CACHE
    if _INIT_CACHE is None:
        _INIT_CACHE = json.loads(vita.Synth().to_json())["settings"]
    return _INIT_CACHE


def describe_preset(path_or_json: str | Path) -> dict:
    """Summarise a .vital file as a patch-spec-like dict of non-default settings."""
    text = Path(path_or_json).read_text() if Path(str(path_or_json)).exists() else str(path_or_json)
    preset = json.loads(text)
    st, init = preset["settings"], _init_settings()
    cat = C.catalog()
    params = {}
    for name, raw in st.items():
        if name not in cat or name.startswith("modulation_") or not isinstance(raw, (int, float)):
            continue
        if abs(raw - init.get(name, cat[name].default)) > 1e-6:
            params[name] = C.human(name, raw)
    # Hide settings of blocks that are switched off: they don't sound.
    for block in ("osc_1", "osc_2", "osc_3", "filter_1", "filter_2", "filter_fx", "sample", "chorus", "compressor",
                  "delay", "distortion", "eq", "flanger", "phaser", "reverb"):
        if st.get(f"{block}_on", 0) < 0.5:
            params = {k: v for k, v in params.items() if not k.startswith(block + "_") or k == f"{block}_on"}
    mods = []
    for i, m in enumerate(st.get("modulations", []), start=1):
        if m.get("source"):
            amt = st.get(f"modulation_{i}_amount", 0.0)
            mod = {"source": m["source"], "dest": m["destination"], "amount": round(amt, 4)}
            if st.get(f"modulation_{i}_bipolar", 0) > 0.5:
                mod["bipolar"] = True
            if abs(st.get(f"modulation_{i}_power", 0)) > 1e-6:
                mod["power"] = round(st[f"modulation_{i}_power"], 3)
            mods.append(mod)
    return {
        "name": preset.get("preset_name", ""),
        "author": preset.get("author", ""),
        "description": preset.get("comments", ""),
        "macros": {str(k): preset.get(f"macro{k}") for k in range(1, 5) if preset.get(f"macro{k}")},
        "wavetables": [w.get("name") for w in st.get("wavetables", [])],
        "lfos": [lf.get("name") for lf in st.get("lfos", [])],
        "params": params,
        "mods": mods,
    }
