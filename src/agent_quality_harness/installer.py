"""Transactional repository-local installation for native agent hooks."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from .hooks import build_hooks, resource_bytes


TOOL_PATHS = {
    "claude": Path(".claude/settings.json"),
    "codex": Path(".codex/hooks.json"),
}
RESOURCE_PATHS = {
    Path(".agent-quality/completion_gate.py"): "completion_gate.py",
    Path(".agent-quality/quality_context.py"): "quality_context.py",
    Path(".agent-quality/quality_contract.txt"): "quality_contract.txt",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_root(target: Path) -> Path:
    candidate = target.expanduser().absolute()
    process = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=candidate,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0 or Path(process.stdout.strip()).resolve() != candidate.resolve():
        raise ValueError("target must be the root of a Git repository")
    return candidate


def _load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path} must contain valid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _selected_tools(tool: str | None) -> list[str]:
    if tool in (None, "both"):
        return ["claude", "codex"]
    if tool not in TOOL_PATHS:
        raise ValueError("tool must be claude, codex, or both")
    return [tool]


def _merge_hooks(value: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(value)
    hooks = merged.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("existing hooks value must be a JSON object")
    for event, desired_groups in desired["hooks"].items():
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"existing hooks.{event} value must be a JSON array")
        for desired_group in desired_groups:
            desired_commands = {
                handler.get("command")
                for handler in desired_group.get("hooks", [])
                if isinstance(handler, dict)
            }
            present = any(
                isinstance(group, dict)
                and any(
                    isinstance(handler, dict)
                    and handler.get("command") in desired_commands
                    for handler in group.get("hooks", [])
                )
                for group in groups
            )
            if not present:
                groups.append(deepcopy(desired_group))
    return merged


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _remove_empty_parents(path: Path, stop: Path) -> None:
    current = path
    while current != stop and current.is_dir():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def _restore(
    root: Path,
    originals: dict[Path, bytes | None],
    backup_root: Path,
) -> None:
    for relative, before in reversed(list(originals.items())):
        path = root / relative
        if before is None:
            path.unlink(missing_ok=True)
            _remove_empty_parents(path.parent, root)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(before)
    if backup_root.exists():
        shutil.rmtree(backup_root)
        _remove_empty_parents(backup_root.parent, root)


def _existing_install(root: Path) -> dict[str, Any] | None:
    manifest_path = root / ".agent-quality/install-manifest.json"
    if not manifest_path.exists():
        return None
    manifest = _load_object(manifest_path)
    records = manifest.get("files")
    if not isinstance(records, dict):
        raise RuntimeError("the installation manifest is invalid")
    for relative, record in records.items():
        if not isinstance(record, dict):
            raise RuntimeError("the installation manifest is invalid")
        path = root / relative
        current = sha256_bytes(path.read_bytes()) if path.is_file() else None
        if current != record.get("after_sha256"):
            raise RuntimeError(f"managed file changed after installation: {relative}")
    return manifest


def _gate_bytes(gate_source: Path | None) -> bytes:
    raw = gate_source.read_bytes() if gate_source is not None else resource_bytes("gate.default.json")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("gate source must contain valid JSON") from error
    if not isinstance(value, dict):
        raise ValueError("gate source must contain a JSON object")
    return _json_bytes(value)


def _install_new(
    root: Path,
    selected: list[str],
    gate: bytes,
) -> dict[str, Any]:
    desired_hooks = build_hooks(Path(sys.executable).resolve(), root)
    outputs: dict[Path, bytes] = {
        relative: resource_bytes(resource_name)
        for relative, resource_name in RESOURCE_PATHS.items()
    }
    outputs[Path(".agent-quality/gate.json")] = gate
    for selected_tool in selected:
        relative = TOOL_PATHS[selected_tool]
        outputs[relative] = _json_bytes(
            _merge_hooks(_load_object(root / relative), desired_hooks)
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_root = root / ".agent-quality-backups" / stamp
    manifest_relative = Path(".agent-quality/install-manifest.json")
    originals = {
        relative: (root / relative).read_bytes() if (root / relative).is_file() else None
        for relative in (*outputs, manifest_relative)
    }
    records: dict[str, Any] = {}
    try:
        for relative, content in outputs.items():
            before = originals[relative]
            backup: str | None = None
            if before is not None:
                backup_path = backup_root / relative
                _atomic_write(backup_path, before)
                backup = backup_path.relative_to(root).as_posix()
            records[relative.as_posix()] = {
                "before_exists": before is not None,
                "before_sha256": sha256_bytes(before) if before is not None else None,
                "after_sha256": sha256_bytes(content),
                "backup": backup,
            }
        for relative, content in outputs.items():
            _atomic_write(root / relative, content)
        manifest = {
            "schema_version": 1,
            "state": "complete",
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "tools": selected,
            "files": records,
        }
        _atomic_write(root / manifest_relative, _json_bytes(manifest))
        return manifest
    except BaseException:
        _restore(root, originals, backup_root)
        raise


def _replace_install(
    root: Path,
    selected: list[str],
    gate: bytes,
) -> dict[str, Any]:
    """Replace a valid install and restore it exactly if replacement fails."""
    directory_paths = [
        Path(".agent-quality"),
        Path(".agent-quality-backups"),
    ]
    file_paths = list(TOOL_PATHS.values())
    with tempfile.TemporaryDirectory(prefix="aqh-update-") as temporary:
        snapshot_root = Path(temporary)
        existing_directories: set[Path] = set()
        existing_files: set[Path] = set()
        for relative in directory_paths:
            source = root / relative
            if source.is_dir():
                shutil.copytree(source, snapshot_root / relative)
                existing_directories.add(relative)
        for relative in file_paths:
            source = root / relative
            if source.is_file():
                destination = snapshot_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                existing_files.add(relative)

        from .uninstaller import uninstall

        try:
            uninstall(root)
            return _install_new(root, selected, gate)
        except BaseException:
            for relative in directory_paths:
                destination = root / relative
                if destination.is_dir():
                    shutil.rmtree(destination)
                elif destination.exists():
                    destination.unlink()
                if relative in existing_directories:
                    shutil.copytree(snapshot_root / relative, destination)
            for relative in file_paths:
                destination = root / relative
                destination.unlink(missing_ok=True)
                if relative in existing_files:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(snapshot_root / relative, destination)
                else:
                    _remove_empty_parents(destination.parent, root)
            raise


def install(
    target: Path,
    *,
    tool: str | None = None,
    gate_source: Path | None = None,
    update: bool = False,
) -> dict[str, Any]:
    """Install both native-client treatments, or one selected treatment."""
    root = _git_root(target)
    selected = _selected_tools(tool)
    gate = _gate_bytes(gate_source)
    existing = _existing_install(root)
    if existing is not None:
        gate_record = existing["files"].get(".agent-quality/gate.json", {})
        same_request = (
            existing.get("tools") == selected
            and gate_record.get("after_sha256") == sha256_bytes(gate)
        )
        if same_request:
            return existing
        if not update:
            raise RuntimeError(
                "a different installation exists; rerun with `aqh install --update`"
            )
        return _replace_install(root, selected, gate)
    return _install_new(root, selected, gate)
