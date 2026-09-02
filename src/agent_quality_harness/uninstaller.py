"""Exact rollback for repository-local Agent Quality Harness installs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .installer import _atomic_write, _git_root, _remove_empty_parents, sha256_bytes


def _manifest(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / ".agent-quality/install-manifest.json"
    if not path.is_file():
        raise FileNotFoundError("no .agent-quality/install-manifest.json found")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("installation manifest must contain valid JSON") from error
    if not isinstance(value, dict) or not isinstance(value.get("files"), dict):
        raise ValueError("installation manifest is invalid")
    return path, value


def uninstall(target: Path, *, force: bool = False) -> None:
    """Restore the exact bytes present before installation."""
    root = _git_root(target)
    manifest_path, manifest = _manifest(root)
    records: dict[str, dict[str, Any]] = manifest["files"]

    restored: dict[Path, bytes | None] = {}
    backup_paths: list[Path] = []
    for relative_string, record in records.items():
        if not isinstance(record, dict):
            raise ValueError("installation manifest is invalid")
        relative = Path(relative_string)
        path = root / relative
        current = path.read_bytes() if path.is_file() else None
        if not force and (
            current is None or sha256_bytes(current) != record.get("after_sha256")
        ):
            raise RuntimeError(f"managed file changed after installation: {relative_string}")
        if record.get("before_exists"):
            backup_value = record.get("backup")
            if not isinstance(backup_value, str):
                raise ValueError("installation manifest is invalid")
            backup = root / backup_value
            if not backup.is_file():
                raise FileNotFoundError(f"missing rollback backup: {backup_value}")
            restored[relative] = backup.read_bytes()
            backup_paths.append(backup)
        else:
            restored[relative] = None

    # All rollback inputs are validated and loaded before the first mutation.
    current_files = {
        relative: (root / relative).read_bytes() if (root / relative).is_file() else None
        for relative in restored
    }
    manifest_bytes = manifest_path.read_bytes()
    try:
        for relative, before in restored.items():
            path = root / relative
            if before is None:
                path.unlink(missing_ok=True)
                _remove_empty_parents(path.parent, root)
            else:
                _atomic_write(path, before)
        manifest_path.unlink()
    except BaseException:
        for relative, previous in current_files.items():
            path = root / relative
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                _atomic_write(path, previous)
        _atomic_write(manifest_path, manifest_bytes)
        raise

    _remove_empty_parents(root / ".agent-quality", root)
    for backup in backup_paths:
        backup.unlink()
        _remove_empty_parents(backup.parent, root)
