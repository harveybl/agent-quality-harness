#!/usr/bin/env python3
"""Deterministic Stop gate shared by Claude Code and Codex."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("protected_paths entries must be non-empty strings")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("protected_paths entries must stay inside the workspace")
    return value


def load_config(script: Path) -> dict[str, Any]:
    value = json.loads(script.with_name("gate.json").read_text(encoding="utf-8"))
    if value.get("schema_version") != 1:
        raise ValueError("gate.json schema_version must be 1")
    if type(value.get("max_blocks")) is not int or not 1 <= value["max_blocks"] <= 7:
        raise ValueError("gate.json max_blocks must be an integer from 1 to 7")
    commands = value.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError("gate.json commands must be a non-empty list")
    for command in commands:
        if set(command) != {"name", "argv", "timeout_seconds"}:
            raise ValueError("each gate command must contain name, argv, timeout_seconds")
        if not isinstance(command["name"], str) or not command["name"]:
            raise ValueError("gate command name must be non-empty")
        if (
            not isinstance(command["argv"], list)
            or not command["argv"]
            or not all(isinstance(item, str) and item for item in command["argv"])
        ):
            raise ValueError("gate command argv must be a non-empty string list")
        seconds = command["timeout_seconds"]
        if type(seconds) is not int or not 1 <= seconds <= 1800:
            raise ValueError("gate command timeout_seconds must be from 1 to 1800")
    protected = value.get("protected_paths", [])
    if not isinstance(protected, list):
        raise ValueError("gate.json protected_paths must be a list")
    value["protected_paths"] = [_relative_path(item) for item in protected]
    return value


def state_path(work: Path, payload: dict[str, Any]) -> Path:
    session = str(payload.get("session_id") or "unknown-session")
    turn = str(payload.get("turn_id") or payload.get("prompt_id") or "session-fallback")
    identity = hashlib.sha256(f"{work}\0{session}\0{turn}".encode()).hexdigest()
    return Path(tempfile.gettempdir()) / "agent-quality-gate" / f"{identity}.json"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_commands(work: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for command in config["commands"]:
        try:
            process = subprocess.run(
                command["argv"],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
                timeout=command["timeout_seconds"],
            )
            rows.append(
                {
                    "name": command["name"],
                    "argv": command["argv"],
                    "passed": process.returncode == 0,
                    "exit_code": process.returncode,
                    "timed_out": False,
                    "stdout_tail": process.stdout[-2000:],
                    "stderr_tail": process.stderr[-3000:],
                }
            )
        except subprocess.TimeoutExpired as error:
            rows.append(
                {
                    "name": command["name"],
                    "argv": command["argv"],
                    "passed": False,
                    "exit_code": None,
                    "timed_out": True,
                    "stdout_tail": str(error.stdout or "")[-2000:],
                    "stderr_tail": str(error.stderr or "")[-3000:],
                }
            )
    return rows


def protected_path_check(work: Path, paths: list[str]) -> dict[str, Any] | None:
    if not paths:
        return None
    process = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", *paths],
        cwd=work,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    changed = process.stdout.strip()
    passed = process.returncode == 0 and not changed
    evidence = changed or process.stderr.strip()
    return {
        "name": "protected paths unchanged" if passed else "protected paths changed",
        "argv": ["git", "status", "--porcelain=v1", "--", *paths],
        "passed": passed,
        "exit_code": process.returncode,
        "timed_out": False,
        "stdout_tail": changed,
        "stderr_tail": evidence,
    }


def process(payload: dict[str, Any], script: Path) -> dict[str, Any]:
    if payload.get("hook_event_name") != "Stop":
        raise ValueError("completion gate only accepts Stop events")
    work = Path(str(payload.get("cwd", ""))).resolve()
    if not work.is_dir():
        raise ValueError("Stop payload cwd must be an existing directory")
    if script.resolve().parent != work / ".agent-quality":
        raise ValueError("completion gate must be installed at <workspace>/.agent-quality")
    config = load_config(script)
    path = state_path(work, payload)
    if path.is_file():
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        state = {
            "schema_version": 1,
            "cwd": str(work),
            "session_id": str(payload.get("session_id") or "unknown-session"),
            "turn_id": str(
                payload.get("turn_id") or payload.get("prompt_id") or "session-fallback"
            ),
            "model": str(payload.get("model") or "unknown-model"),
            "permission_mode": str(
                payload.get("permission_mode") or "unknown-permission-mode"
            ),
            "invocations": 0,
            "blocks": 0,
            "evaluations": [],
        }
    state["invocations"] += 1
    rows = run_commands(work, config)
    protected = protected_path_check(work, config["protected_paths"])
    if protected is not None:
        rows.append(protected)
    passed = all(row["passed"] for row in rows)
    state["evaluations"].append(
        {
            "passed": passed,
            "checks": [
                {key: row[key] for key in ("name", "passed", "exit_code", "timed_out")}
                for row in rows
            ],
        }
    )
    if passed:
        state["outcome"] = "passed"
        write_json(path, state)
        return {"systemMessage": f"completion gate passed: {len(rows)}/{len(rows)} checks"}
    failed = [row for row in rows if not row["passed"]]
    if state["blocks"] < config["max_blocks"]:
        state["blocks"] += 1
        state["outcome"] = "blocked-for-repair"
        write_json(path, state)
        diagnostics = []
        for row in failed:
            evidence = (row["stderr_tail"] or row["stdout_tail"] or "no diagnostic output").strip()
            diagnostics.append(
                f"{row['name']} (exit={row['exit_code']}, timed_out={row['timed_out']}):\n{evidence}"
            )
        return {
            "decision": "block",
            "reason": (
                "Deterministic completion checks failed. Repair only the observed failures, "
                "preserve passing behavior, rerun the relevant checks, and finish again.\n\n"
                + "\n\n".join(diagnostics)
            ),
        }
    state["outcome"] = "failed-after-bounded-repair"
    write_json(path, state)
    return {"systemMessage": "completion gate exhausted its bounded repair budget"}


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(process(payload, Path(__file__)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
