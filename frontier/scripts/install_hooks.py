#!/usr/bin/env python3
"""Install repository-local Claude Code and Codex completion hooks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any


HOOK_COMMAND = 'python3 "$(git rev-parse --show-toplevel)/.agent-quality/completion_gate.py"'
HOOK_GROUP = {
    "hooks": [
        {
            "type": "command",
            "command": HOOK_COMMAND,
            "timeout": 1800,
            "statusMessage": "Running deterministic completion checks",
        }
    ]
}
TOOL_PATHS = {"claude": Path(".claude/settings.json"), "codex": Path(".codex/hooks.json")}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_root(target: Path) -> Path:
    process = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=target,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0 or Path(process.stdout.strip()).resolve() != target.resolve():
        raise ValueError("target must be the root of a Git repository")
    return target.resolve()


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


def _merge_hook(value: dict[str, Any]) -> dict[str, Any]:
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("existing hooks value must be a JSON object")
    stop = hooks.setdefault("Stop", [])
    if not isinstance(stop, list):
        raise ValueError("existing hooks.Stop value must be a JSON array")
    for group in stop:
        if not isinstance(group, dict):
            continue
        for handler in group.get("hooks", []):
            if isinstance(handler, dict) and handler.get("command") == HOOK_COMMAND:
                return value
    stop.append(HOOK_GROUP)
    return value


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _record_write(
    root: Path,
    relative: Path,
    content: bytes,
    backup_root: Path,
) -> dict[str, Any]:
    path = root / relative
    existed = path.is_file()
    before = path.read_bytes() if existed else b""
    backup: str | None = None
    if existed:
        backup_path = backup_root / relative
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_bytes(before)
        backup = backup_path.relative_to(root).as_posix()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "before_exists": existed,
        "before_sha256": sha256_bytes(before) if existed else None,
        "after_sha256": sha256_bytes(content),
        "backup": backup,
    }


def install(
    target: Path,
    tools: list[str],
    *,
    gate_source: Path | None = None,
) -> dict[str, Any]:
    root = _git_root(target)
    selected = sorted(set(tools))
    if not selected or any(tool not in TOOL_PATHS for tool in selected):
        raise ValueError("tools must contain claude, codex, or both")
    manifest_path = root / ".agent-quality/install-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("tools") != selected:
            raise RuntimeError("a different installation exists; uninstall it first")
        for relative, record in manifest["files"].items():
            path = root / relative
            if not path.is_file() or sha256_bytes(path.read_bytes()) != record["after_sha256"]:
                raise RuntimeError("managed files changed after installation; uninstall with --force")
        return manifest

    # Validate every JSON target before creating backups or managed files.
    merged: dict[Path, bytes] = {}
    for tool in selected:
        relative = TOOL_PATHS[tool]
        merged[relative] = _json_bytes(_merge_hook(_load_object(root / relative)))

    project_root = Path(__file__).resolve().parents[2]
    gate_path = gate_source or project_root / "evaluator/gate.example.json"
    gate_value = json.loads(gate_path.read_text(encoding="utf-8"))
    if not isinstance(gate_value, dict):
        raise ValueError("gate source must contain a JSON object")
    managed = {
        **merged,
        Path(".agent-quality/completion_gate.py"): (
            project_root / "evaluator/completion_gate.py"
        ).read_bytes(),
        Path(".agent-quality/gate.json"): _json_bytes(gate_value),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = root / ".agent-quality-backups" / stamp
    records: dict[str, Any] = {}
    for relative, content in managed.items():
        records[relative.as_posix()] = _record_write(root, relative, content, backup_root)
    manifest = {
        "schema_version": 1,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "tools": selected,
        "files": records,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=Path.cwd())
    parser.add_argument("--tool", choices=("claude", "codex", "both"), default="both")
    parser.add_argument("--gate", type=Path)
    args = parser.parse_args()
    tools = ["claude", "codex"] if args.tool == "both" else [args.tool]
    manifest = install(args.target, tools, gate_source=args.gate)
    print(f"installed: {', '.join(manifest['tools'])}")
    print("next: open Claude Code or Codex in the target repository and review the hook once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

