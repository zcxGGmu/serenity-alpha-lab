from __future__ import annotations

import argparse
from collections.abc import Sequence

from serenity_alpha_lab import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="serenity-alpha-lab",
        description="Serenity Alpha Lab command surface.",
    )
    parser.add_argument("--version", action="store_true", help="Print the Serenity package version.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    parser.print_help()
    return 0
