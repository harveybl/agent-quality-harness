#!/usr/bin/env python3
"""Restore files changed by install_hooks.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .install_hooks import _git_root, sha256_bytes
except ImportError:  # Direct script execution.
    from install_hooks import _git_root, sha256_bytes


def _remove_empty_parents(path: Path, stop: Path) -> None:
    current = path
    while current != stop and current.is_dir():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def uninstall(target: Path, *, force: bool = False) -> None:
    root = _git_root(target)
    manifest_path = root / ".agent-quality/install-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("no .agent-quality/install-manifest.json found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("files", {})
    if not force:
        for relative, record in records.items():
            path = root / relative
            current = sha256_bytes(path.read_bytes()) if path.is_file() else None
            if current != record["after_sha256"]:
                raise RuntimeError(f"managed file changed after installation: {relative}")
    backup_paths: list[Path] = []
    for relative, record in records.items():
        path = root / relative
        if record["before_exists"]:
            backup = root / record["backup"]
            if not backup.is_file():
                raise FileNotFoundError(f"missing rollback backup: {record['backup']}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(backup.read_bytes())
            backup_paths.append(backup)
        elif path.exists():
            path.unlink()
    manifest_path.unlink()
    _remove_empty_parents(root / ".agent-quality", root)
    for backup in backup_paths:
        backup.unlink()
        _remove_empty_parents(backup.parent, root)


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

