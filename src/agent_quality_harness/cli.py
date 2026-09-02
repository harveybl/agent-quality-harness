"""Public command-line interface for Agent Quality Harness."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence


COMMANDS = (
    ("install", "Install repository-local Claude Code and Codex hooks"),
    ("doctor", "Diagnose an installed repository treatment"),
    ("verify", "Run synthetic hook verification without model calls"),
    ("uninstall", "Restore the repository to its pre-install state"),
    ("local", "Use an existing local model endpoint"),
    ("experiment", "Run explicitly experimental quality comparisons"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aqh",
        description="Quality checks for native Claude Code, Codex, and local models.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in COMMANDS:
        subparsers.add_parser(name, help=help_text)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"aqh {args.command} is not available in this build", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
