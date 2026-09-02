#!/usr/bin/env python3
"""Validate operational runbook shape and public-path hygiene."""

from __future__ import annotations

from pathlib import Path
import re
import sys


FIELDS = ("Purpose", "Run", "Expect", "If it fails", "Verify", "Undo")
RUNBOOKS = ("docs/local-deploy.md", "docs/frontier-deploy.md")
BLOCKED = (
    "/Users/",
    "/home/",
    "brandonharvey",
    "Development-Projects",
    "192.168.",
    "TODO",
    "TBD",
    "CHANGEME",
)


def lint_runbook(path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing runbook: {path.relative_to(path.parents[1])}"]
    text = path.read_text(encoding="utf-8")
    starts = list(re.finditer(r"^## Step \d+: .+$", text, re.MULTILINE))
    if not starts:
        return [f"{path}: no numbered steps"]
    errors: list[str] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        section = text[match.start() : end]
        positions = [section.find(f"### {field}") for field in FIELDS]
        if any(position < 0 for position in positions):
            missing = [field for field, position in zip(FIELDS, positions) if position < 0]
            errors.append(f"{path}:{match.group(0)} missing {', '.join(missing)}")
        elif positions != sorted(positions):
            errors.append(f"{path}:{match.group(0)} fields are out of order")
    return errors


def lint_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in RUNBOOKS:
        errors.extend(lint_runbook(root / relative))
    for base in (root / "docs", root / "evidence", root / "examples"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for token in BLOCKED:
                if token in text:
                    errors.append(f"{path.relative_to(root)} contains blocked token {token!r}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = lint_repository(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("PASS deployment runbooks and public boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

