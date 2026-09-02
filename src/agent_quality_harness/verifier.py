"""Synthetic, model-free verification for an installed treatment."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from .doctor import diagnose
from .installer import TOOL_PATHS, _git_root, install


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def _invoke(script: Path, payload: dict[str, Any]) -> dict[str, Any]:
    process = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or f"{script.name} exited nonzero")
    value = json.loads(process.stdout)
    if not isinstance(value, dict):
        raise RuntimeError(f"{script.name} returned a non-object payload")
    return value


def _hook_shape(root: Path, tools: list[str]) -> bool:
    for tool in tools:
        config = json.loads((root / TOOL_PATHS[tool]).read_text(encoding="utf-8"))
        hooks = config.get("hooks", {})
        if not all(isinstance(hooks.get(event), list) and hooks[event] for event in ("SessionStart", "Stop")):
            return False
    return True


def verify(target: Path) -> dict[str, Any]:
    """Prove hook shape and bounded behavior without invoking a model."""
    root = _git_root(target)
    report = diagnose(root)
    before = _snapshot(root)
    checks = {
        "hook_shape": "pass" if _hook_shape(root, report["tools"]) else "fail",
        "session_start": "fail",
        "passing_stop": "fail",
        "bounded_failure": "fail",
        "target_immutable": "fail",
    }

    context = _invoke(
        root / ".agent-quality/quality_context.py",
        {"hook_event_name": "SessionStart", "cwd": str(root)},
    )
    if context.get("hookSpecificOutput", {}).get("additionalContext"):
        checks["session_start"] = "pass"

    with tempfile.TemporaryDirectory(prefix="aqh-verify-") as temporary:
        fixture = Path(temporary)
        subprocess.run(["git", "init", "-q"], cwd=fixture, check=True)
        gate_source = fixture / "verify-gate.json"
        gate_source.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "max_blocks": 1,
                    "protected_paths": [],
                    "commands": [
                        {
                            "name": "synthetic-marker",
                            "argv": [
                                sys.executable,
                                "-c",
                                (
                                    "from pathlib import Path; import sys; "
                                    "sys.exit(0 if Path('.verify-pass').is_file() else 1)"
                                ),
                            ],
                            "timeout_seconds": 10,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        install(fixture, tool="claude", gate_source=gate_source)
        stop_script = fixture / ".agent-quality/completion_gate.py"
        base = {
            "hook_event_name": "Stop",
            "cwd": str(fixture),
            "session_id": "synthetic-session",
            "turn_id": "failing-turn",
            "stop_hook_active": False,
        }
        blocked = _invoke(stop_script, base)
        exhausted = _invoke(stop_script, base)
        if blocked.get("decision") == "block" and "decision" not in exhausted:
            if "exhausted" in exhausted.get("systemMessage", ""):
                checks["bounded_failure"] = "pass"
        (fixture / ".verify-pass").write_text("pass\n", encoding="utf-8")
        passed = _invoke(stop_script, {**base, "turn_id": "passing-turn"})
        if "passed" in passed.get("systemMessage", ""):
            checks["passing_stop"] = "pass"

    if _snapshot(root) == before:
        checks["target_immutable"] = "pass"
    return {
        "status": "pass" if all(value == "pass" for value in checks.values()) else "fail",
        "checks": checks,
    }
