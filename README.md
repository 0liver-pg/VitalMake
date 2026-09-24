# VitalMake

Sound design for the [Vital](https://vital.audio) synthesizer, driven by text and
judged by machine listening. It's a small lab for seeing how a language model
works with sound when it can't hear anything.

The loop:

1. **Write** a patch as compact JSON in human units (`"filter_1_cutoff": "800Hz"`,
   `"env_1_attack": "1.2s"`, `"filter_1_model": "Ladder"`).
2. **Render** it headlessly through the real Vital engine
   ([vita](https://pypi.org/project/vita/) Python bindings), as a note, a chord or a sequence.
3. **Listen** using `ears.py`, which turns the audio into a text report (envelope,
   pitch, partials, brightness over time, modulation rates, glides, stereo image) and a
   spectrogram sheet a multimodal model can look at.
4. **Iterate**, then save a real `.vital` preset that opens in the plugin.

`gallery/` holds ten sounds made this way. Open `gallery/index.html` to hear
them next to what the model "heard".

## Quick start

```bash
uv sync
uv run vitalmake make patches/glass-choir.json --play      # render, analyse, play
uv run vitalmake make-all                                  # every patch + gallery/index.html
uv run vitalmake install glass-choir                       # copy into Vital: User > VitalMake
uv run vitalmake params filter cutoff                      # search the 772 controls
uv run vitalmake describe ~/Music/Vital/Factory/Presets/Plucked\ String.vital
uv run vitalmake listen some.wav --note-off 1.0 --sheet some.png
```

Presets install to `~/Music/Vital/User/Presets/VitalMake/`.

## Patch format

```json
{
  "name": "Glass Choir",
  "description": "what it should sound like",
  "wavetables": {"osc_1": [{"shape": "saw"}, {"harmonics": [1, 0.5, 0.3]}, {"text": "hello"}]},
  "lfos": {"lfo_1": {"shape": "sine"}},
  "params": {"osc_1_unison_voices": 7, "filter_1_on": "On", "filter_1_cutoff": "350Hz", "env_1_attack": "1.4s"},
  "mods": [{"source": "env_2", "dest": "filter_1_cutoff", "amount": "+40st"}],
  "macros": {"1": "BLOOM"},
  "play": {"chord": ["C3", "G3", "D4"], "dur": 5, "tail": 4}
}
```

- **params**: a number means the value the Vital GUI displays. Strings take units
  (`Hz`, `kHz`, `s`, `ms`, `%`, `dB`, `st`), note names for cutoffs (`"A4"`), or option
  names (`"Ladder"`, `"Tempo Dotted"`, `"1/8"`). `{"raw": x}` and `{"norm": x}` are escape
  hatches. Conversions are checked against Vital's own display text for every control.
- **wavetables**: keyframes from `shape`, `harmonics`, `partials` (1/n^falloff series),
  `expr` (a numpy expression over phase `x`), `noise`, or `text` (letters become
  harmonic loudness).
- **mods**: `amount` is a fraction of the destination's range, or `"+24st"`. Options:
  `bipolar`, `stereo`, `power`.
- **play**: `note`, `chord`, `sequence` (`"C2 _ Eb2 G1!"`, `_` rest, `!` accent) or explicit `notes`.

Mistakes come back as a list with suggestions (`unknown control 'filter_1_cutof'. Did you mean: filter_1_cutoff`),
so a model can fix them in one pass.

## MCP server

`.mcp.json` registers `vitalmake-mcp`, so Claude Code sessions in this folder get
these tools: `vital_spec_help`, `vital_search_params`, `vital_make` (returns the report plus the
spectrogram image), `vital_listen`, `vital_compare`, `vital_list_presets`,
`vital_describe_preset`, `vital_play` (plays on your speakers), `vital_install`, `vital_match`.
To use it from anywhere:

```bash
claude mcp add vitalmake -- uv run --directory /path/to/VitalMake vitalmake-mcp
```

## Sound matching

`vitalmake match target.wav --base patch.json --param filter_1_cutoff=100Hz..8kHz --param env_1_decay`
fits the chosen knobs to a target with CMA-ES (plus random restarts), minimising a
multi-resolution spectrogram distance. `experiments/blind_match.py` hides a pluck patch,
then recovers it from the audio alone. `experiments/llm-blind-match.md` is the same test
done by a language model reading reports and spectrograms.

## Layout

```
src/vitalmake/
  controls.py    human units <-> Vital's raw values, control search
  wavetable.py   wavetable and LFO generation
  patch.py       patch spec -> Vital state; .vital -> readable summary
  render.py      notes, chords and sequences -> audio (parallel, deterministic)
  ears.py        machine listening: report, descriptors, spectrogram sheet, distance
  match.py       CMA-ES sound matching
  studio.py      make/install/play, shared by CLI and MCP
  cli.py, mcp_server.py, gallery.py
patches/         patch specs (the source of every gallery sound)
gallery/         rendered .wav, .vital, sheet.png, report per patch + index.html
experiments/     blind-match experiments and write-ups
```

## Notes and limits

- vita renders one note per call. Chords and sequences are rendered note by note and
  summed, so voices don't share a compressor, and legato or portamento between notes isn't possible.
- Re-rendering on the same `Synth` carries oscillator phase over. `render.py` uses a fresh
  `Synth` per note, which keeps output deterministic.
- vita reports `synth_version` 99999.9.9. Saved presets are stamped 1.5.5 so the plugin
  doesn't treat them as coming from a future version.
- The descriptor words in the report are thresholds on the measurements, not perception.
  The numbers are printed next to them for that reason.
- Don't commit or redistribute renders of the factory or pack presets. Their license forbids it.

Vital and vita are GPLv3. This project only drives them.
