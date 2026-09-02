#!/usr/bin/env python3
"""Compatibility entry point for the public ``aqh install`` command."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agent_quality_harness.installer import _git_root, install as _install, sha256_bytes


def install(
    target: Path,
    tools: list[str],
    *,
    gate_source: Path | None = None,
    update: bool = False,
) -> dict[str, Any]:
    selected = sorted(set(tools))
    if selected == ["claude", "codex"]:
        tool = "both"
    elif selected in (["claude"], ["codex"]):
        tool = selected[0]
    else:
        raise ValueError("tools must contain claude, codex, or both")
    return _install(target, tool=tool, gate_source=gate_source, update=update)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=Path.cwd())
    parser.add_argument("--tool", choices=("claude", "codex", "both"), default="both")
    parser.add_argument("--gate", type=Path)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    tools = ["claude", "codex"] if args.tool == "both" else [args.tool]
    manifest = install(args.target, tools, gate_source=args.gate, update=args.update)
    print(f"installed: {', '.join(manifest['tools'])}")
    print("next: run `aqh doctor`, then open the repository in your native client")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
