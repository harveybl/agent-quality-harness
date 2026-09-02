"""Read-only diagnostics for an installed Agent Quality Harness treatment."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any

from .hooks import resource_bytes
from .installer import _existing_install, _git_root


def _latest_evidence(root: Path) -> dict[str, Any] | None:
    state_root = Path(tempfile.gettempdir()) / "agent-quality-gate"
    candidates: list[tuple[int, dict[str, Any]]] = []
    if not state_root.is_dir():
        return None
    for path in state_root.glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or value.get("cwd") != str(root.resolve()):
            continue
        candidates.append((path.stat().st_mtime_ns, value))
    if not candidates:
        return None
    state = max(candidates, key=lambda item: item[0])[1]
    evaluations = state.get("evaluations", [])
    latest = evaluations[-1] if isinstance(evaluations, list) and evaluations else {}
    checks = latest.get("checks", []) if isinstance(latest, dict) else []
    return {
        "outcome": state.get("outcome", "unknown"),
        "invocations": state.get("invocations", 0),
        "blocks": state.get("blocks", 0),
        "check_count": len(checks) if isinstance(checks, list) else 0,
        "session_id": state.get("session_id", "unknown-session"),
        "turn_id": state.get("turn_id", "session-fallback"),
    }


def diagnose(target: Path) -> dict[str, Any]:
    """Validate files without logging in, calling a model, or mutating the repo."""
    root = _git_root(target)
    manifest = _existing_install(root)
    if manifest is None:
        raise FileNotFoundError("Agent Quality Harness is not installed")
    gate = json.loads((root / ".agent-quality/gate.json").read_text(encoding="utf-8"))
    default_gate = json.loads(resource_bytes("gate.default.json").decode("utf-8"))
    minimum = gate == default_gate
    issues: list[str] = []
    if manifest.get("target") != str(root):
        issues.append("installed hook path does not match the current repository path")
    interpreter = manifest.get("interpreter")
    if not isinstance(interpreter, str) or not Path(interpreter).is_file():
        issues.append("installed Python interpreter path is unavailable")
    return {
        "status": "repair-needed" if issues else "ok",
        "tools": manifest["tools"],
        "issues": issues,
        "gate_kind": "minimum" if minimum else "custom",
        "recommendation": (
            "Refresh absolute paths with `aqh install --update`."
            if issues
            else (
                "Add project-specific test, lint, or build commands with `aqh install "
                "--gate <file> --update`."
                if minimum
                else "Project-specific deterministic checks are configured."
            )
        ),
        "latest_evidence": _latest_evidence(root),
    }
