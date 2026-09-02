"""Compact run-ledger helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment(root: Path) -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "contract_sha256": file_sha256(root / "contract.json"),
        "task_sha256": file_sha256(root / "task.md"),
    }


def write_ledger(root: Path, value: dict[str, Any]) -> Path:
    path = root / "runs/ledger.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path

