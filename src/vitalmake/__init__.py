"""VitalMake: sound design for Vital, driven by text, rendered headlessly, heard through analysis."""


def main() -> None:
    from .cli import main as _main

    raise SystemExit(_main())
