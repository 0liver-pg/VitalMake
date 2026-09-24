"""High-level operations shared by the CLI and the MCP server."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import ears as E
from . import patch as P
from . import render as R

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / "patches"
GALLERY = ROOT / "gallery"
VITAL_USER_PRESETS = Path.home() / "Music" / "Vital" / "User" / "Presets" / "VitalMake"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "untitled"


def make(spec: dict, slug: str | None = None, out_root: Path = GALLERY) -> dict:
    """Build + render + listen. Writes <out>/<slug>/{sound.wav, <name>.vital, sheet.png, report.txt, patch.json}."""
    name = spec.get("name", "Untitled")
    slug = slug or slugify(name)
    synth = P.build(spec)
    out = out_root / slug
    out.mkdir(parents=True, exist_ok=True)
    preset_json = P.to_vital_json(synth)
    play = spec.get("play")
    audio = R.render(preset_json, play)
    notes, tail = R.parse_play(play)
    note_off = max(n.start + n.dur for n in notes)
    L = E.listen(audio, R.SR, note_off=note_off)

    # A sequence smears envelope/pitch/motion analysis across notes, so the
    # detailed report is taken from a probe: whatever starts at t=0 (a note or chord).
    first = [n for n in notes if n.start == 0]
    if len(first) < len(notes):
        probe_play = {"notes": [{"pitch": n.pitch, "start": 0, "dur": n.dur, "vel": n.vel} for n in first],
                      "tail": tail}
        probe = R.render(preset_json, probe_play)
        P_ = E.listen(probe, R.SR, note_off=max(n.dur for n in first))
        text = E.report(P_, f"{name} - first note alone") + "\n" + E.phrase_line(L)
        # the probe is the trustworthy description (pitch/motion trackers are
        # confused by chord changes), so it's what the sheet and gallery show
        L = P_
    else:
        text = E.report(L, name)
    if L.peak_db < -30:
        text += "\nWARNING: very quiet render - check levels, filter cutoff, osc levels."

    from . import expression as X

    for old in out.glob("tour-*.*"):
        old.unlink()
    expr_text, tour_files = X.tour(spec, out) if X.controls_used(spec) else ("", [])
    if expr_text:
        text += "\n\nExpression check (probe note, low -> high):\n" + expr_text
    (out / "tour.json").write_text(json.dumps(tour_files, indent=2) + "\n")

    wav = R.write_wav(audio, out / "sound.wav")
    R.write_mp3(audio, out / "sound.mp3")
    vital = out / f"{name}.vital"
    for old in out.glob("*.vital"):
        old.unlink()
    vital.write_text(preset_json)
    sheet = E.plot(audio, out / "sheet.png", R.SR, title=name, L=L, note_off=note_off)
    (out / "report.txt").write_text(text + "\n")
    (out / "patch.json").write_text(json.dumps(spec, indent=2) + "\n")
    (out / "listening.json").write_text(json.dumps(L.to_dict(), indent=2) + "\n")
    return {"slug": slug, "report": text, "wav": wav, "vital": vital, "sheet": sheet, "listening": L}


def install(vital_path: Path) -> Path:
    VITAL_USER_PRESETS.mkdir(parents=True, exist_ok=True)
    dest = VITAL_USER_PRESETS / vital_path.name
    shutil.copy2(vital_path, dest)
    return dest


def play(wav: Path, block: bool = True) -> None:
    cmd = ["afplay", str(wav)]
    if block:
        subprocess.run(cmd, check=False)
    else:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find_output(slug_or_path: str) -> Path:
    p = Path(slug_or_path)
    if p.exists():
        return p
    d = GALLERY / slugify(slug_or_path)
    if d.exists():
        return d
    raise FileNotFoundError(f"no gallery entry or file named {slug_or_path!r}")
