import json
import random
import re

import numpy as np
import vita

from vitalmake import controls as C
from vitalmake import ears as E
from vitalmake import patch as P
from vitalmake import render as R


def test_display_conversion_matches_vital_text():
    """Our raw->display formula agrees with Vital's own display text for every continuous control."""
    synth = vita.Synth()
    ctl = synth.get_controls()
    rng = random.Random(0)
    for name, c in C.catalog().items():
        if c.options or c.scale == "indexed":
            continue
        raw = rng.uniform(c.min, c.max)
        ctl[name].set(raw)
        shown = float(re.match(r"\s*(-?[\d.]+(?:e-?\d+)?)", synth.get_control_text(name)).group(1))
        assert abs(shown - c.to_display(raw)) <= 1e-3 * max(1, abs(shown)), name
        assert abs(c.from_display(c.to_display(raw)) - raw) <= 1e-4 * max(1, abs(raw)), name


def test_human_units():
    assert C.to_raw("filter_1_cutoff", "440Hz") == 69.0
    assert C.to_raw("filter_1_cutoff", "A4") == 69.0
    assert C.to_raw("filter_1_model", "ladder") == 2.0
    assert C.to_raw("delay_tempo", "1/8") == 9.0
    assert abs(C.get("env_1_attack").to_display(C.to_raw("env_1_attack", "250ms")) - 0.25) < 1e-6
    assert abs(C.to_raw("lfo_1_frequency", "2Hz") - 1.0) < 1e-9


def test_render_is_deterministic_and_pitched():
    spec = {"wavetables": {"osc_1": [{"shape": "sine"}]}, "params": {"osc_1_random_phase": "0%"}}
    js = P.to_vital_json(P.build(spec))
    a = R.render(js, {"note": "A3", "dur": 0.5, "tail": 0.2})
    b = R.render(js, {"note": "A3", "dur": 0.5, "tail": 0.2})
    assert np.array_equal(a, b)
    L = E.listen(a, note_off=0.5)
    assert abs(L.f0_hz - 220) < 2


def test_bad_patch_reports_all_problems():
    try:
        P.build({"params": {"filter_1_cutof": 1, "filter_1_model": "Moog"}})
    except P.PatchError as e:
        msg = str(e)
        assert "filter_1_cutoff" in msg and "Ladder" in msg
    else:
        raise AssertionError("expected PatchError")


def test_saved_preset_roundtrips():
    spec = json.load(open("patches/glass-choir.json"))
    text = P.to_vital_json(P.build(spec))
    assert json.loads(text)["synth_version"] == "1.5.5"
    assert vita.Synth().load_json(text)


def test_mod_ids_resolve_to_slots():
    spec = {"mods": [
        {"source": "lfo_1", "dest": "filter_1_cutoff", "amount": 0.0, "id": "wob"},
        {"source": "mod_wheel", "dest": "mod:wob", "amount": 0.3},
    ]}
    st = json.loads(P.to_vital_json(P.build(spec)))["settings"]
    assert st["modulations"][1] == {"source": "mod_wheel", "destination": "modulation_1_amount"}


def test_expression_check_sees_macro_and_vibrato():
    from vitalmake import expression as X

    spec = {
        "params": {"filter_1_on": "On", "filter_1_cutoff": "300Hz", "lfo_1_sync": "Seconds", "lfo_1_frequency": "5.5Hz"},
        "lfos": {"lfo_1": {"shape": "sine"}},
        "macros": {"1": "BRIGHT"},
        "mods": [
            {"source": "macro_control_1", "dest": "filter_1_cutoff", "amount": "+40st"},
            {"source": "lfo_1", "dest": "voice_tune", "amount": 0.0, "bipolar": True, "id": "vib"},
            {"source": "aftertouch", "dest": "mod:vib", "amount": 0.15},
        ],
        "tour": {"note": "A3", "dur": 1.5, "tail": 0.3},
    }
    text, _ = X.tour(spec)
    assert "M1 BRIGHT" in text and "brightness" in text.split("\n")[0]
    assert "pitch wobble" in [ln for ln in text.split("\n") if ln.startswith("Aftertouch")][0]


def test_per_note_set_reaches_mod_chains():
    spec = {"wavetables": {"osc_1": [{"shape": "sine"}]}, "params": {"osc_1_random_phase": "0%"},
            "mods": [{"source": "mod_wheel", "dest": "osc_1_transpose", "amount": "+12st"}]}
    js = P.to_vital_json(P.build(spec))
    a = R.render(js, {"note": "A3", "dur": 0.6, "tail": 0.1, "set": {"mod_wheel": 1.0}})
    assert abs(E.listen(a, note_off=0.6).f0_hz - 440) < 4
