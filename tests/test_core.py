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
