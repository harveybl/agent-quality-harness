"""Strands worker for an OpenAI-compatible local llama.cpp endpoint."""

from __future__ import annotations

import json
from typing import Any

from .contracts import Plan
from .file_tools import FileTools


SYSTEM = """You are a bounded coding worker. Use only supplied tools and files. Do not edit tests,
contracts, harness code, or protected paths. Make the smallest change that satisfies the task.
Run public checks only after a write. Never restart the task or invent success."""


def _metrics(result: Any) -> dict[str, int]:
    metrics = getattr(result, "metrics", None)
    if metrics is None:
        return {"model_calls": 1, "tokens": 0}
    summary = metrics.get_summary() if hasattr(metrics, "get_summary") else {}
    usage = summary.get("accumulatedUsage", {}) if isinstance(summary, dict) else {}
    calls = summary.get("cycleCount", 1) if isinstance(summary, dict) else 1
    return {"model_calls": int(calls or 1), "tokens": int(usage.get("totalTokens", 0) or 0)}


class StrandsWorker:
    def __init__(self, endpoint: str, model_id: str) -> None:
        from strands.models.openai import OpenAIModel

        self.model = OpenAIModel(
            client_args={"api_key": "local-not-a-secret", "base_url": endpoint},
            model_id=model_id,
            params={"max_tokens": 8192, "temperature": 0.1, "stream_options": None},
        )

    def plan(self, task: str, inventory: list[str]) -> tuple[dict, dict]:
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

        agent = Agent(model=self.model, system_prompt=SYSTEM)
        result = agent(
            "Return a native plan object for this task. Each change must name an inventory file, "
            "an exact current line number and anchor text, the intended change, and acceptance IDs.\n\n"
            f"TASK:\n{task}\n\nINVENTORY:\n" + "\n".join(inventory),
            structured_output_model=PlanModel,
        )
        structured = getattr(result, "structured_output", None)
        if structured is None:
            raise RuntimeError("Strands did not return native structured plan output")
        return structured.model_dump(), _metrics(result)

    @staticmethod
    def _agent_tools(tools: FileTools) -> list[Any]:
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
            """Read a bounded line range from one repository file."""
            return tools.read_file(path, start_line, end_line)

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

        return [list_files, search_text, read_file, replace_text, write_file, run_public_tests]

    def implement(
        self,
        task: str,
        plan: Plan,
        windows: dict[str, str],
        tools: FileTools,
    ) -> dict:
        from strands import Agent

        agent = Agent(model=self.model, tools=self._agent_tools(tools), system_prompt=SYSTEM)
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
        result = agent(
            f"Implement the task using the carried plan and anchor windows.\nTASK:\n{task}\n"
            f"PLAN:\n{json.dumps(plan_value)}\nWINDOWS:\n{json.dumps(windows)}"
        )
        return _metrics(result)

    def repair(self, task: str, evidence: str, diff: str, tools: FileTools) -> dict:
        from strands import Agent

        agent = Agent(model=self.model, tools=self._agent_tools(tools), system_prompt=SYSTEM)
        result = agent(
            "This is the only gate-controlled continuation. Repair the exact observed failure "
            "without broadening scope, then run the relevant public checks once.\n"
            f"TASK:\n{task}\nEVIDENCE:\n{evidence}\nCURRENT DIFF:\n{diff}"
        )
        return _metrics(result)

