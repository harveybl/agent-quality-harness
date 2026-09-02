"""Small validated data boundary for an AVO review directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ACTIONS = frozenset({"continue", "redirect", "stop"})


def _text(value: object, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters")
    return value.strip()


@dataclass(frozen=True)
class Directive:
    action: str
    strategy: str
    instruction: str
    rationale: str

    @classmethod
    def from_object(cls, value: object) -> "Directive":
        if not isinstance(value, dict) or set(value) != {
            "action",
            "strategy",
            "instruction",
            "rationale",
        }:
            raise ValueError("directive must contain action, strategy, instruction, rationale")
        if value["action"] not in ACTIONS:
            raise ValueError("directive action must be continue, redirect, or stop")
        return cls(
            action=value["action"],
            strategy=_text(value["strategy"], "strategy", 120),
            instruction=_text(value["instruction"], "instruction", 1200),
            rationale=_text(value["rationale"], "rationale", 600),
        )


@dataclass(frozen=True)
class ReviewPacket:
    task_summary: str
    worker_diff: str
    check_evidence: str
    repair_cycle: int
    repairs_remaining: int

    def __post_init__(self) -> None:
        _text(self.task_summary, "task_summary", 4000)
        _text(self.worker_diff, "worker_diff", 40_000)
        _text(self.check_evidence, "check_evidence", 20_000)
        if type(self.repair_cycle) is not int or self.repair_cycle < 0:
            raise ValueError("repair_cycle must be a non-negative integer")
        if type(self.repairs_remaining) is not int or self.repairs_remaining < 0:
            raise ValueError("repairs_remaining must be a non-negative integer")

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "task_summary": self.task_summary,
            "worker_diff": self.worker_diff,
            "check_evidence": self.check_evidence,
            "repair_cycle": self.repair_cycle,
            "repairs_remaining": self.repairs_remaining,
        }


@dataclass(frozen=True)
class SupervisorUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cycles: int = 0
    tool_calls: int = 0
    wall_seconds: float = 0.0

    def __post_init__(self) -> None:
        for value in (
            self.input_tokens,
            self.output_tokens,
            self.total_tokens,
            self.cycles,
            self.tool_calls,
        ):
            if type(value) is not int or value < 0:
                raise ValueError("usage counts must be non-negative integers")
        if self.total_tokens < self.input_tokens + self.output_tokens:
            raise ValueError("total tokens cannot be less than input plus output")
        if self.wall_seconds < 0:
            raise ValueError("wall_seconds must be non-negative")
