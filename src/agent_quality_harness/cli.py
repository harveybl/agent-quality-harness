"""Public command-line interface for Agent Quality Harness."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from . import doctor, installer, uninstaller


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
        command = subparsers.add_parser(name, help=help_text)
        if name == "install":
            command.add_argument("--target", type=Path, default=Path.cwd())
            command.add_argument(
                "--tool", choices=("claude", "codex", "both"), default="both"
            )
            command.add_argument("--gate", type=Path)
            command.add_argument(
                "--update",
                action="store_true",
                help="Transactionally replace an existing different installation",
            )
        elif name == "uninstall":
            command.add_argument("--target", type=Path, default=Path.cwd())
            command.add_argument(
                "--force",
                action="store_true",
                help="Discard later edits to managed files and restore pre-install bytes",
            )
        elif name == "doctor":
            command.add_argument("--target", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "install":
        manifest = installer.install(
            args.target,
            tool=args.tool,
            gate_source=args.gate,
            update=args.update,
        )
        names = {
            ("claude",): "Claude Code",
            ("codex",): "Codex",
            ("claude", "codex"): "Claude Code and Codex",
        }[tuple(manifest["tools"])]
        print(f"Installed Agent Quality Harness for {names}.")
        print("Next: run `aqh doctor`, then open the repository in your native client.")
        return 0
    if args.command == "uninstall":
        uninstaller.uninstall(args.target, force=args.force)
        print("Restored the repository to its exact pre-install state.")
        return 0
    if args.command == "doctor":
        report = doctor.diagnose(args.target)
        print(f"status: {report['status']}")
        print(f"clients: {', '.join(report['tools'])}")
        print(f"gate: {report['gate_kind']}")
        if report["latest_evidence"] is None:
            print("latest evidence: none yet")
        else:
            evidence = report["latest_evidence"]
            print(
                "latest evidence: "
                f"{evidence['outcome']}, {evidence['check_count']} checks, "
                f"{evidence['blocks']} blocks"
            )
        for issue in report["issues"]:
            print(f"issue: {issue}")
        print(f"next: {report['recommendation']}")
        return 0 if report["status"] == "ok" else 1
    print(f"aqh {args.command} is not available in this build", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
