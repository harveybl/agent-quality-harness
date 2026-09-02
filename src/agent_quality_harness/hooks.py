"""Portable native hook definitions and packaged resource access."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import os
import shlex
import subprocess
from typing import Any


def resource_bytes(name: str) -> bytes:
    allowed = {"completion_gate.py", "quality_context.py", "quality_contract.txt"}
    if name not in allowed:
        raise ValueError(f"unknown harness resource: {name}")
    return resources.files("agent_quality_harness.resources").joinpath(name).read_bytes()


def _command(arguments: list[str], platform: str) -> str:
    if platform == "windows":
        return subprocess.list2cmdline(arguments)
    if platform == "posix":
        return shlex.join(arguments)
    raise ValueError("platform must be 'posix' or 'windows'")


def _handler(
    interpreter: Path,
    script: Path,
    *,
    platform: str,
    timeout: int,
    status: str,
) -> dict[str, Any]:
    return {
        "type": "command",
        "command": _command([str(interpreter), str(script)], platform),
        "timeout": timeout,
        "statusMessage": status,
    }


def build_hooks(
    interpreter: Path,
    target: Path,
    *,
    platform: str | None = None,
) -> dict[str, Any]:
    """Return the shared Claude Code/Codex repository hook object."""
    selected_platform = platform or ("windows" if os.name == "nt" else "posix")
    quality = target / ".agent-quality"
    return {
        "description": "Repository-local Agent Quality Harness treatment.",
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        _handler(
                            interpreter,
                            quality / "quality_context.py",
                            platform=selected_platform,
                            timeout=10,
                            status="Loading repository quality contract",
                        )
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        _handler(
                            interpreter,
                            quality / "completion_gate.py",
                            platform=selected_platform,
                            timeout=1800,
                            status="Running deterministic completion checks",
                        )
                    ]
                }
            ],
        },
    }
