"""vitalmake command line.

    vitalmake make patches/glass-choir.json [--play] [--install]
    vitalmake make-all                       # every patch in patches/
    vitalmake listen some.wav [--note-off 2]
    vitalmake describe ~/Music/Vital/Factory/Presets/Plucked\\ String.vital
    vitalmake params cutoff filter_1
    vitalmake install glass-choir
    vitalmake play glass-choir
    vitalmake match target.wav --base patches/x.json --param filter_1_cutoff=100Hz..8kHz --param env_1_attack
    vitalmake gallery
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import controls as C
from . import studio


def _make(path: Path, args) -> dict:
    spec = json.loads(path.read_text())
    res = studio.make(spec, slug=path.stem)
    print(res["report"])
    print(f"-> {res['wav'].relative_to(studio.ROOT)}  |  {res['vital'].relative_to(studio.ROOT)}  |  "
          f"{res['sheet'].relative_to(studio.ROOT)}\n")
    if getattr(args, "install", False):
        print("installed:", studio.install(res["vital"]))
    if getattr(args, "play", False):
        studio.play(res["wav"])
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vitalmake", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("make", help="build, render and listen to patch specs")
    m.add_argument("patches", nargs="+", type=Path)
    m.add_argument("--play", action="store_true", help="play through the speakers (afplay)")
    m.add_argument("--install", action="store_true", help="copy the .vital into Vital's user presets")

    ma = sub.add_parser("make-all", help="render every patch in patches/")
    ma.add_argument("--install", action="store_true")

    li = sub.add_parser("listen", help="analyse a wav file")
    li.add_argument("wav", type=Path)
    li.add_argument("--note-off", type=float, default=None)
    li.add_argument("--sheet", type=Path, default=None, help="also write a spectrogram png here")

    de = sub.add_parser("describe", help="summarise a .vital preset in human units")
    de.add_argument("preset", type=Path)

    pa = sub.add_parser("params", help="search Vital's controls")
    pa.add_argument("query", nargs="*")
    pa.add_argument("--limit", type=int, default=40)

    ins = sub.add_parser("install", help="copy a gallery preset into Vital's user folder")
    ins.add_argument("slug")

    pl = sub.add_parser("play", help="play a gallery sound")
    pl.add_argument("slug")

    mt = sub.add_parser("match", help="fit patch parameters to a target sound")
    mt.add_argument("target", type=Path)
    mt.add_argument("--base", type=Path, required=True, help="patch spec to start from (its play block is used)")
    mt.add_argument("--param", action="append", required=True,
                    help="control to fit, optionally with a range: filter_1_cutoff=100Hz..8kHz")
    mt.add_argument("--budget", type=int, default=400, help="number of renders")
    mt.add_argument("--name", default=None)

    sub.add_parser("gallery", help="rebuild gallery/index.html")

    args = ap.parse_args(argv)

    if args.cmd == "make":
        for p in args.patches:
            _make(p, args)
    elif args.cmd == "make-all":
        for p in sorted(studio.PATCHES.rglob("*.json")):
            _make(p, args)
        from .gallery import build_gallery

        print("gallery:", build_gallery())
    elif args.cmd == "listen":
        from . import ears as E
        from . import render as R

        audio, sr = R.read_wav(args.wav)
        L = E.listen(audio, sr, note_off=args.note_off)
        print(E.report(L, args.wav.name))
        if args.sheet:
            print("sheet:", E.plot(audio, args.sheet, sr, title=args.wav.name, L=L, note_off=args.note_off))
    elif args.cmd == "describe":
        from . import patch as P

        print(json.dumps(P.describe_preset(args.preset), indent=2))
    elif args.cmd == "params":
        q = " ".join(args.query)
        rows = C.search(q, args.limit) if q else list(C.catalog().values())[: args.limit]
        for c in rows:
            print(f"{c.name:34s} {c.describe_range():60s} default {C.human(c.name, c.default)}")
    elif args.cmd == "install":
        d = studio.find_output(args.slug)
        vit = next(d.glob("*.vital"))
        print("installed:", studio.install(vit))
    elif args.cmd == "play":
        studio.play(studio.find_output(args.slug) / "sound.wav")
    elif args.cmd == "match":
        from .match import match_cli

        match_cli(args)
    elif args.cmd == "gallery":
        from .gallery import build_gallery

        print("gallery:", build_gallery())
    return 0


if __name__ == "__main__":
    sys.exit(main())
