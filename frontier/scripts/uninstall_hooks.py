#!/usr/bin/env python3
"""Compatibility entry point for the public ``aqh uninstall`` command."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_quality_harness.uninstaller import uninstall


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=Path.cwd())
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    uninstall(args.target, force=args.force)
    print("restored the pre-install repository state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
