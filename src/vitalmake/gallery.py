"""Build gallery/index.html: every rendered patch with its audio, the
spectrogram the model looked at, and the listening report it read."""

from __future__ import annotations

import html
import json
from pathlib import Path

from . import studio

ORDER = ["glass-choir", "words-as-waves", "endless-staircase", "robot-babble", "midnight-reese", "wub-machine",
         "gravity-kick", "laser-tag", "tin-kalimba", "neon-arp"]
EXPERIMENTS = ["blind-match", "llm-blind-match"]


def _entry(d: Path) -> dict | None:
    if not (d / "sound.wav").exists() or not (d / "listening.json").exists():
        return None
    spec = json.loads((d / "patch.json").read_text())
    L = json.loads((d / "listening.json").read_text())
    report = (d / "report.txt").read_text().strip()
    vital = next(d.glob("*.vital"), None)
    return {"slug": d.name, "spec": spec, "L": L, "report": report, "vital": vital.name if vital else ""}


def _mods(spec: dict) -> list[str]:
    out = []
    for m in spec.get("mods", []):
        amt = m.get("amount", "")
        out.append(f"{m['source']} → {m['dest']} {amt}{' ±' if m.get('bipolar') else ''}")
    return out


def _card(e: dict) -> str:
    s, L = e["spec"], e["L"]
    esc = html.escape
    chips = "".join(f'<li>{esc(w)}</li>' for w in L.get("words", []))
    mods = "".join(f"<li>{esc(m)}</li>" for m in _mods(s)) or "<li>none</li>"
    wt = s.get("wavetables", {})
    wt_txt = ", ".join(f"{k}: {len(v['frames'] if isinstance(v, dict) else v)} frame(s)" for k, v in wt.items()) or "Vital init saw"
    spec_json = esc(json.dumps(s, indent=2))
    report = esc(e["report"])
    return f"""
<article class="sound" id="{e['slug']}">
  <header class="sound-head">
    <h2>{esc(s.get('name', e['slug']))}</h2>
    <p class="brief">{esc(s.get('description', ''))}</p>
  </header>
  <div class="sound-body">
    <div class="listen">
      <audio controls preload="none" src="{e['slug']}/sound.wav"></audio>
      <figure><img loading="lazy" src="{e['slug']}/sheet.png" alt="Spectrogram and waveform of {esc(s.get('name',''))}"></figure>
    </div>
    <div class="read">
      <h3>What the ears reported</h3>
      <ul class="chips">{chips}</ul>
      <dl class="facts">
        <div><dt>Pitch</dt><dd>{esc(L.get('f0_note') or '-')}</dd></div>
        <div><dt>Centroid</dt><dd>{L.get('centroid_hz')} Hz</dd></div>
        <div><dt>Attack</dt><dd>{L.get('attack_ms'):.0f} ms</dd></div>
        <div><dt>Width</dt><dd>{L.get('width')}</dd></div>
      </dl>
      <details><summary>Full listening report</summary><pre>{report}</pre></details>
      <h3>How it was built</h3>
      <p class="small">Wavetables: {esc(wt_txt)} · {len(s.get('params', {}))} settings · preset file <code>{esc(e['vital'])}</code></p>
      <ul class="mods">{mods}</ul>
      <details><summary>Patch spec (JSON)</summary>
        <button class="copy" type="button" data-target="spec-{e['slug']}">Copy JSON</button>
        <pre id="spec-{e['slug']}">{spec_json}</pre></details>
    </div>
  </div>
</article>"""


def build_gallery(extra_html: str = "") -> Path:
    root = studio.GALLERY
    entries = []
    names = ORDER + sorted(p.stem for p in studio.PATCHES.glob("*.json") if p.stem not in ORDER)
    for slug in names:
        e = _entry(root / slug)
        if e:
            entries.append(e)
    exp = [e for e in (_entry(root / s) for s in EXPERIMENTS) if e]
    notes = studio.ROOT / "experiments" / "summary.html"
    extra_html = extra_html or (notes.read_text() if notes.exists() else "")
    toc = "".join(f'<a href="#{e["slug"]}">{html.escape(e["spec"].get("name", e["slug"]))}</a>' for e in entries)
    body = "".join(_card(e) for e in entries)
    exp_body = "".join(_card(e) for e in exp)
    page = TEMPLATE.replace("{{TOC}}", toc).replace("{{SOUNDS}}", body).replace("{{COUNT}}", str(len(entries)))
    page = page.replace("{{EXPERIMENTS}}", extra_html + exp_body)
    out = root / "index.html"
    out.write_text(page)
    return out


TEMPLATE = """<title>Sounds Without Ears</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {
  --ground: #eceff3; --panel: #f7f8fa; --ink: #19202b; --muted: #5a6475; --line: #cfd5de;
  --accent: #0e7f86; --accent-ink: #ffffff; --chip: #dde7ea; --screen: #101418;
  --display: "Bricolage Grotesque", "Avenir Next", system-ui, sans-serif;
  --body: "IBM Plex Sans", system-ui, -apple-system, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground: #11151b; --panel: #171c24; --ink: #e2e7ee; --muted: #97a1b1; --line: #2a323e;
    --accent: #43c3c8; --accent-ink: #0b1115; --chip: #1f2b31;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --ground: #11151b; --panel: #171c24; --ink: #e2e7ee; --muted: #97a1b1; --line: #2a323e;
  --accent: #43c3c8; --accent-ink: #0b1115; --chip: #1f2b31;
}
* { box-sizing: border-box; }
body { background: var(--ground); color: var(--ink); font: 15px/1.55 var(--body); padding-inline: 16px; padding-block: 0 64px; }
.wrap { max-width: 1180px; margin: 0 auto; }
.masthead { padding-block: 48px 28px; display: grid; gap: 14px; max-width: 760px; }
.eyebrow { font: 500 12px/1 var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--accent); }
h1 { font: 700 clamp(34px, 6vw, 60px)/1.02 var(--display); margin: 0; text-wrap: balance; letter-spacing: -.01em; }
.lede { font-size: 17px; color: var(--muted); margin: 0; max-width: 65ch; }
.toc { display: flex; flex-wrap: wrap; gap: 6px 14px; padding-block: 14px; border-block: 1px solid var(--line); font: 500 13px/1.4 var(--mono); }
.toc a { color: var(--ink); text-decoration: none; border-bottom: 1px solid transparent; }
.toc a:hover, .toc a:focus-visible { border-color: var(--accent); outline: none; }
.sound { padding-block: 40px; border-bottom: 1px solid var(--line); display: grid; gap: 18px; }
.sound-head { display: grid; gap: 6px; max-width: 760px; }
h2 { font: 700 30px/1.1 var(--display); margin: 0; }
.brief { margin: 0; color: var(--muted); max-width: 65ch; }
.sound-body { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr); gap: 28px; align-items: start; }
@media (max-width: 860px) { .sound-body { grid-template-columns: 1fr; } }
.listen { display: grid; gap: 12px; }
audio { width: 100%; }
figure { margin: 0; background: var(--screen); border-radius: 6px; overflow: hidden; }
figure img { display: block; width: 100%; height: auto; }
.read { display: grid; gap: 12px; }
h3 { font: 600 12px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin: 8px 0 0; }
.chips { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.chips li { background: var(--chip); padding: 3px 9px; border-radius: 999px; font-size: 13px; }
.facts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin: 0; }
.facts div { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; }
.facts dt { font: 500 11px/1 var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
.facts dd { margin: 4px 0 0; font: 500 15px/1.2 var(--mono); font-variant-numeric: tabular-nums; }
@media (max-width: 480px) { .facts { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.mods { margin: 0; padding-left: 18px; font: 13px/1.6 var(--mono); }
.small { margin: 0; font-size: 13px; color: var(--muted); }
code { font: 12.5px var(--mono); }
details { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 8px 12px; }
summary { cursor: pointer; font-weight: 500; }
summary:focus-visible, .copy:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
pre { font: 12px/1.5 var(--mono); white-space: pre-wrap; word-break: break-word; margin: 10px 0 2px; max-height: 420px; overflow: auto; }
.copy { font: 500 12px var(--mono); background: var(--accent); color: var(--accent-ink); border: 0; border-radius: 4px; padding: 5px 10px; margin-top: 10px; cursor: pointer; }
.section-title { font: 700 clamp(26px, 4vw, 38px)/1.1 var(--display); margin: 56px 0 8px; }
.experiment { max-width: 820px; display: grid; gap: 12px; }
.experiment p { margin: 0; max-width: 70ch; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; font: 13px/1.4 var(--mono); font-variant-numeric: tabular-nums; min-width: 520px; }
th, td { text-align: left; padding: 7px 14px 7px 0; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 500; }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
</style>
<div class="wrap">
  <header class="masthead">
    <span class="eyebrow">VitalMake · Vital synthesizer, driven by text</span>
    <h1>Sounds designed by a model that cannot hear</h1>
    <p class="lede">Each patch below was written as JSON by Claude, rendered headlessly through the real Vital engine, and judged only through a machine-listening report and a spectrogram image. Press play to hear what it could only read about. {{COUNT}} sounds, plus two blind-reconstruction experiments at the end.</p>
  </header>
  <nav class="toc" aria-label="Sounds">{{TOC}}<a href="#experiments">Blind match</a></nav>
  {{SOUNDS}}
  <section id="experiments">
    <h2 class="section-title">Blind match</h2>
    {{EXPERIMENTS}}
  </section>
</div>
<script>
document.querySelectorAll('.copy').forEach(function (b) {
  b.addEventListener('click', function () {
    var el = document.getElementById(b.dataset.target);
    var done = function () { b.textContent = 'Copied'; setTimeout(function () { b.textContent = 'Copy JSON'; }, 1500); };
    navigator.clipboard.writeText(el.textContent).then(done, function () {
      var r = document.createRange(); r.selectNodeContents(el);
      var s = getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = 'Selected - press Cmd+C';
    });
  });
});
document.addEventListener('play', function (e) {
  document.querySelectorAll('audio').forEach(function (a) { if (a !== e.target) a.pause(); });
}, true);
</script>
"""
