"""Native plan contract and anchor validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


def _relative(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("path must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("path must stay inside the workspace")
    return value


@dataclass(frozen=True)
class PlanChange:
    path: str
    line: int
    anchor: str
    change: str
    acceptance_ids: tuple[str, ...]

    @classmethod
    def from_object(cls, value: object) -> "PlanChange":
        if not isinstance(value, dict):
            raise ValueError("each plan change must be a JSON object")
        expected = {"path", "line", "anchor", "change", "acceptance_ids"}
        if set(value) != expected:
            raise ValueError("each plan change must contain exactly path, line, anchor, change, acceptance_ids")
        if type(value["line"]) is not int or value["line"] < 1:
            raise ValueError("plan line must be a positive integer")
        for key in ("anchor", "change"):
            if not isinstance(value[key], str) or not value[key].strip():
                raise ValueError(f"plan {key} must be non-empty")
        acceptance = value["acceptance_ids"]
        if (
            not isinstance(acceptance, list)
            or not acceptance
            or not all(isinstance(item, str) and item for item in acceptance)
        ):
            raise ValueError("acceptance_ids must be a non-empty string list")
        return cls(
            path=_relative(value["path"]),
            line=value["line"],
            anchor=value["anchor"],
            change=value["change"],
            acceptance_ids=tuple(acceptance),
        )


@dataclass(frozen=True)
class Plan:
    changes: tuple[PlanChange, ...]

    @classmethod
    def from_object(cls, value: object) -> "Plan":
        if not isinstance(value, dict):
            raise ValueError("plan must be a native JSON object, not Markdown")
        if set(value) != {"changes"} or not isinstance(value["changes"], list) or not value["changes"]:
            raise ValueError("plan must contain exactly one non-empty changes array")
        return cls(tuple(PlanChange.from_object(item) for item in value["changes"]))


def validate_anchor(path: Path, line: int, anchor: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if line > len(lines) or anchor not in lines[line - 1]:
        raise ValueError(f"anchor {anchor!r} does not match {path} line {line}")


def anchor_window(path: Path, line: int, radius: int = 30) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = max(0, line - radius - 1)
    end = min(len(lines), line + radius)
    return "\n".join(f"{index + 1}: {lines[index]}" for index in range(start, end))

