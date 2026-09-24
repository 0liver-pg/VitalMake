"""MCP server: lets any Claude session design sounds in Vital.

Tools render headlessly, then return the listening report plus a spectrogram
image, so the model "hears" by reading numbers and looking at a picture.
`vital_play` sends the sound to the user's speakers so a human can judge too.

Register with Claude Code (project .mcp.json does this for this repo):
    claude mcp add vitalmake -- uv run --directory /path/to/VitalMake vitalmake-mcp
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.mcpserver import Image, MCPServer

from . import controls as C
from . import ears as E
from . import patch as P
from . import render as R
from . import studio
from . import wavetable as W

mcp = MCPServer(
    "vitalmake",
    instructions=(
        "Design sounds for the Vital synthesizer. Call vital_spec_help once to learn the patch format, "
        "vital_search_params to find controls, then vital_make to build+render+analyse a patch. "
        "Read the report and look at the spectrogram, then iterate. vital_play lets the user hear it; "
        "vital_install copies the preset into Vital."
    ),
)


def _sheet(path: Path) -> Image:
    return Image(path=str(path))


@mcp.tool()
def vital_spec_help() -> str:
    """The patch-spec format, wavetable/LFO/play syntax, and all modulation sources and destinations."""
    dests = sorted({d for d in P.MOD_DESTINATIONS if not d.startswith("modulation_")})
    return "\n\n".join([
        P.__doc__ or "", C.to_raw.__doc__ or "", W.__doc__ or "", W.lfo.__doc__ or "", R.__doc__ or "",
        "Mod amount: fraction of the destination's full range (-1..1), or '+24st' for pitch-like "
        "destinations. Optional: bipolar, stereo, power (curve -10..10). A modulation's own amount can be a "
        "destination: 'modulation_3_amount'. env_1 is hard-wired to amplitude.",
        "Modulation sources: " + ", ".join(P.MOD_SOURCES),
        "Modulation destinations (N = 1..3 for osc/filter, 1..6 env, 1..8 lfo, 1..4 random): " + ", ".join(dests),
        "Sound-design notes: MIDI C3 = 48 (130.8 Hz); keep bass fundamentals at or above E1 (41 Hz). "
        "Chords are summed renders, so lower 'volume' for dense chords. Renders are deterministic.",
    ])


@mcp.tool()
def vital_search_params(query: str, limit: int = 25) -> str:
    """Search Vital's 772 controls by words (e.g. 'filter 1 cutoff', 'reverb', 'unison'). Shows range + default."""
    rows = C.search(query, limit)
    if not rows:
        return "no match"
    return "\n".join(f"{c.name}: {c.describe_range()} (default {C.human(c.name, c.default)})" for c in rows)


@mcp.tool()
def vital_make(patch: dict, slug: str | None = None, play_aloud: bool = False) -> list:
    """Build a patch spec, render it, listen, and save it (patches/<slug>.json + gallery/<slug>/).

    Returns the listening report and a spectrogram sheet. Set play_aloud to hear it on the user's speakers.
    """
    slug = slug or studio.slugify(patch.get("name", "untitled"))
    try:
        res = studio.make(patch, slug=slug)
    except (P.PatchError, ValueError, KeyError) as e:
        return [f"Patch error - nothing rendered:\n{e}"]
    studio.PATCHES.mkdir(exist_ok=True)
    (studio.PATCHES / f"{slug}.json").write_text(json.dumps(patch, indent=2) + "\n")
    if play_aloud:
        studio.play(res["wav"], block=False)
    return [res["report"] + f"\n\nSaved: {res['vital']}", _sheet(res["sheet"])]


@mcp.tool()
def vital_listen(wav_path: str, note_off_seconds: float | None = None) -> list:
    """Analyse any WAV file (a reference sound, a render, a sample) with the same ears."""
    audio, sr = R.read_wav(wav_path)
    L = E.listen(audio, sr, note_off=note_off_seconds)
    out = Path(wav_path).with_suffix(".sheet.png")
    E.plot(audio, out, sr, title=Path(wav_path).name, L=L, note_off=note_off_seconds)
    return [E.report(L, Path(wav_path).name), _sheet(out)]


@mcp.tool()
def vital_compare(a: str, b: str) -> str:
    """Spectral distance between two gallery sounds or WAV paths (0 = identical; ~1+ = very different)."""
    def load(x):
        p = Path(x)
        return R.read_wav(p if p.suffix == ".wav" else studio.find_output(x) / "sound.wav")[0]
    return f"distance {E.distance(load(a), load(b)):.4f}"


@mcp.tool()
def vital_list_presets(query: str = "", limit: int = 40) -> str:
    """List .vital presets installed on this machine (factory + packs + user), filtered by name."""
    root = Path.home() / "Music" / "Vital"
    hits = [p for p in root.rglob("*.vital") if query.lower() in p.name.lower()]
    return "\n".join(str(p) for p in sorted(hits)[:limit]) or "none found"


@mcp.tool()
def vital_describe_preset(path: str) -> str:
    """Read a .vital preset back as non-default settings in human units, plus its modulation matrix."""
    return json.dumps(P.describe_preset(path), indent=2)


@mcp.tool()
def vital_play(slug: str) -> str:
    """Play a gallery sound through the user's speakers."""
    wav = studio.find_output(slug) / "sound.wav"
    studio.play(wav, block=False)
    return f"playing {wav}"


@mcp.tool()
def vital_install(slug: str) -> str:
    """Copy a gallery preset into Vital's user preset folder (browse it under User > VitalMake)."""
    d = studio.find_output(slug)
    return f"installed {studio.install(next(d.glob('*.vital')))}"


@mcp.tool()
def vital_match(target_wav: str, base_patch: dict, free_params: list[str], budget: int = 300) -> list:
    """Fit chosen knobs of a base patch to a target WAV with CMA-ES (spectral distance).

    free_params: control names, optionally with ranges, e.g. ["filter_1_cutoff=100Hz..8kHz", "env_1_decay"].
    The base patch's play block decides the note that is rendered (use the target's pitch).
    """
    from .match import Free, match

    target, sr = R.read_wav(target_wav)
    spec, _, hist = match(target, base_patch, [Free.parse(p) for p in free_params], budget=budget, log=lambda *_: None)
    spec["name"] = base_patch.get("name", "Match") + " (fitted)"
    res = studio.make(spec)
    return [f"distance {hist[0]:.4f} -> {hist[-1]:.4f}\nfitted: {json.dumps(spec['fitted'])}\n\n{res['report']}",
            _sheet(res["sheet"])]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
