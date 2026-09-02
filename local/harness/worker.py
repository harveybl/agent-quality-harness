"""Strands worker for an OpenAI-compatible local llama.cpp endpoint."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any

from .contracts import Plan
from .file_tools import FileTools


SYSTEM = """You are a bounded coding worker. Use only supplied tools and files. Do not edit tests,
contracts, harness code, or protected paths. Make the smallest change that satisfies the task.
Run public checks only after a write. Never restart the task or invent success."""

MAX_MODEL_CALLS_PER_PHASE = 32
MAX_SECONDS_PER_PHASE = 300


class PhaseLimitError(RuntimeError):
    """Raised when one local agent phase exceeds its native model-call budget."""

    def __init__(
        self,
        phase: str,
        maximum: int,
        calls: int,
        description: str | None = None,
    ) -> None:
        self.model_calls = calls
        limit = description or f"{maximum} model calls"
        super().__init__(f"{phase} phase exceeded {limit}")


class PhaseExecutionError(RuntimeError):
    """Carries countable phase evidence back to the controller ledger."""

    def __init__(self, phase: str, calls: int, failure: BaseException) -> None:
        self.model_calls = calls
        super().__init__(f"{phase} phase failed after {calls} model calls: {failure}")


@dataclass
class _ModelCallBudget:
    phase: str
    maximum: int = MAX_MODEL_CALLS_PER_PHASE
    maximum_seconds: int = MAX_SECONDS_PER_PHASE
    calls: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def __call__(self, event: object) -> None:
        self.calls += 1
        if time.monotonic() - self.started_at > self.maximum_seconds:
            raise PhaseLimitError(
                self.phase,
                self.maximum_seconds,
                self.calls,
                f"{self.maximum_seconds}-second time limit",
            )
        if self.calls > self.maximum:
            raise PhaseLimitError(self.phase, self.maximum, self.calls)


def _metrics(result: Any) -> dict[str, int]:
    metrics = getattr(result, "metrics", None)
    if metrics is None:
        return {"model_calls": 1, "tokens": 0}
    summary = metrics.get_summary() if hasattr(metrics, "get_summary") else {}
    summary = summary if isinstance(summary, dict) else {}
    usage = getattr(metrics, "accumulated_usage", None)
    if not isinstance(usage, dict):
        usage = summary.get("accumulated_usage") or summary.get("accumulatedUsage") or {}
    calls = getattr(metrics, "cycle_count", None)
    if calls is None:
        calls = summary.get("total_cycles") or summary.get("cycleCount") or 1
    tokens = usage.get("totalTokens") or usage.get("total_tokens") or 0
    return {"model_calls": int(calls or 1), "tokens": int(tokens)}


class StrandsWorker:
    def __init__(self, endpoint: str, model_id: str) -> None:
        from strands.models.openai import OpenAIModel

        self.model = OpenAIModel(
            client_args={
                "api_key": "local-not-a-secret",
                "base_url": endpoint,
                "timeout": 300.0,
            },
            model_id=model_id,
            params={
                "max_tokens": 8192,
                "temperature": 0.1,
                "stream_options": {"include_usage": True},
            },
        )

    def plan(
        self,
        task: str,
        inventory: list[str],
        tools: FileTools,
    ) -> tuple[dict, dict]:
        from pydantic import BaseModel, Field
        from strands import Agent

        class ChangeModel(BaseModel):
            path: str
            line: int = Field(ge=1)
            anchor: str
            change: str
            acceptance_ids: list[str]

        class PlanModel(BaseModel):
            changes: list[ChangeModel]

        agent = Agent(
            model=self.model,
            tools=self._plan_tools(tools),
            system_prompt=SYSTEM,
        )
        budget = self._limit(agent, "plan")
        try:
            result = agent(
                "Inspect the inventory with the read-only tools, then return a native plan object. "
                "Each change must name an inventory file, "
                "an exact current line number and anchor text, the intended change, and acceptance IDs.\n\n"
                f"TASK:\n{task}\n\nINVENTORY:\n" + "\n".join(inventory),
                structured_output_model=PlanModel,
            )
        except Exception as error:
            self._raise_phase_failure("plan", budget, error)
        structured = getattr(result, "structured_output", None)
        if structured is None:
            raise RuntimeError("Strands did not return native structured plan output")
        return structured.model_dump(), _metrics(result)

    @staticmethod
    def _limit(agent: Any, phase: str) -> _ModelCallBudget:
        from strands.hooks.events import BeforeModelCallEvent

        budget = _ModelCallBudget(phase)
        agent.add_hook(budget, BeforeModelCallEvent)
        return budget

    @staticmethod
    def _raise_phase_failure(
        phase: str,
        budget: _ModelCallBudget,
        error: BaseException,
    ) -> None:
        if isinstance(error, PhaseLimitError):
            raise error
        raise PhaseExecutionError(phase, budget.calls, error) from error

    @staticmethod
    def _plan_tools(tools: FileTools) -> list[Any]:
        from strands import tool

        @tool
        def list_files(path: str = ".") -> list[str]:
            """List at most 100 repository files under a path."""
            return tools.list_files(path)

        @tool
        def search_text(needle: str, path: str = ".") -> list[str]:
            """Search literal text in repository files within the navigation budget."""
            return tools.search_text(needle, path)

        @tool
        def read_file(path: str, start_line: int = 1, end_line: int = 240) -> str:
            """Read a bounded, line-numbered range from one repository file."""
            content = tools.read_file(path, start_line, end_line)
            return "\n".join(
                f"{number}: {line}"
                for number, line in enumerate(content.splitlines(), start_line)
            )

        return [list_files, search_text, read_file]

    @staticmethod
    def _agent_tools(tools: FileTools) -> list[Any]:
        from strands import tool

        navigation = StrandsWorker._plan_tools(tools)

        @tool
        def replace_text(path: str, old: str, new: str, line: int, anchor: str) -> str:
            """Replace one exact text occurrence after validating an exact line anchor."""
            return tools.replace_text(path, old, new, line=line, anchor=anchor)

        @tool
        def write_file(path: str, content: str) -> str:
            """Write a complete allowed file after syntax and path validation."""
            return tools.write_file(path, content)

        @tool
        def run_public_tests() -> dict[str, Any]:
            """Run controller-owned public checks after at least one accepted write."""
            return tools.run_public_tests()

        return [*navigation, replace_text, write_file, run_public_tests]

    def implement(
        self,
        task: str,
        plan: Plan,
        windows: dict[str, str],
        tools: FileTools,
    ) -> dict:
        from strands import Agent

        agent = Agent(
            model=self.model,
            tools=self._agent_tools(tools),
            system_prompt=SYSTEM,
        )
        budget = self._limit(agent, "implementation")
        plan_value = {
            "changes": [
                {
                    "path": item.path,
                    "line": item.line,
                    "anchor": item.anchor,
                    "change": item.change,
                    "acceptance_ids": list(item.acceptance_ids),
                }
                for item in plan.changes
            ]
        }
        try:
            result = agent(
                "Implement from the carried plan and anchor windows. Read only the source needed "
                "to preserve surrounding behavior; do not rediscover the task or reread controller "
                "checks unless a public check fails.\n"
                f"TASK:\n{task}\nPLAN:\n{json.dumps(plan_value)}\nWINDOWS:\n{json.dumps(windows)}"
            )
        except Exception as error:
            self._raise_phase_failure("implementation", budget, error)
        return _metrics(result)

    def repair(self, task: str, evidence: str, diff: str, tools: FileTools) -> dict:
        from strands import Agent

        agent = Agent(
            model=self.model,
            tools=self._agent_tools(tools),
            system_prompt=SYSTEM,
        )
        budget = self._limit(agent, "repair")
        try:
            result = agent(
                "This is the only gate-controlled continuation. Repair the exact observed failure "
                "from the evidence and current diff without broadening scope, then run the relevant "
                "public checks once. Use the evidence and diff before spending the fresh bounded "
                "navigation budget.\n"
                f"TASK:\n{task}\nEVIDENCE:\n{evidence}\nCURRENT DIFF:\n{diff}"
            )
        except Exception as error:
            self._raise_phase_failure("repair", budget, error)
        return _metrics(result)
