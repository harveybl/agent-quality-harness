"""Bounded tool-less Strands supervisor for the opt-in AVO experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .directive import Directive, ReviewPacket, SupervisorUsage


SYSTEM_PROMPT = """You review one coding worker's public diff and deterministic check evidence.
You have no tools and no authority to edit, execute, restart, or claim success. Return one
bounded directive. Preserve passing behavior, address only observed evidence, and choose stop
when no repair budget remains. Never request credentials, hidden tests, private data, or paths."""


def _strands_agent(**kwargs: Any) -> tuple[Any, type[Any]]:
    try:
        from pydantic import BaseModel, Field
        from strands import Agent
        from strands.session.file_session_manager import FileSessionManager
    except ImportError as error:
        raise ImportError(
            "AVO supervisor requires: pip install 'agent-quality-harness[experiment]'"
        ) from error

    class DirectiveModel(BaseModel):
        action: str = Field(pattern="^(continue|redirect|stop)$")
        strategy: str = Field(min_length=1, max_length=120)
        instruction: str = Field(min_length=1, max_length=1200)
        rationale: str = Field(min_length=1, max_length=600)

    manager = FileSessionManager(
        session_id=kwargs["session_id"], storage_dir=str(kwargs["session_root"])
    )
    agent = Agent(
        agent_id="aqh-avo-supervisor",
        name="AQH AVO Supervisor",
        model=kwargs["model"],
        tools=kwargs["tools"],
        system_prompt=kwargs["system_prompt"],
        session_manager=manager,
        callback_handler=None,
    )
    return agent, DirectiveModel


class AvoSupervisor:
    def __init__(
        self,
        *,
        workspace: Path,
        session_root: Path,
        session_id: str,
        model: Any,
        agent_factory: Callable[..., Any] | None = None,
    ) -> None:
        candidate = workspace.resolve()
        if not session_id or any(character in session_id for character in "/\\"):
            raise ValueError("invalid supervisor session_id")
        if session_root.is_symlink():
            raise ValueError("session root cannot be a symlink")
        session = session_root.resolve()
        if session == candidate or session.is_relative_to(candidate):
            raise ValueError("supervisor session state must remain outside the candidate")
        session.mkdir(parents=True, exist_ok=True, mode=0o700)
        session.chmod(0o700)
        arguments = {
            "model": model,
            "tools": [],
            "system_prompt": SYSTEM_PROMPT,
            "session_root": session,
            "session_id": session_id,
        }
        if agent_factory is None:
            self._agent, self._output_model = _strands_agent(**arguments)
        else:
            self._agent = agent_factory(**arguments)
            self._output_model = None
        get_config = getattr(model, "get_config", None)
        configuration = get_config() if callable(get_config) else {}
        self.model_identity = {
            "provider": configuration.get("provider", type(model).__name__),
            "model": configuration.get("model_id", "scripted-or-unspecified"),
        }
        self.last_usage = SupervisorUsage()

    def decide(self, packet: ReviewPacket) -> Directive:
        payload = json.dumps(packet.as_public_dict(), sort_keys=True, separators=(",", ":"))
        prompt = (
            "Return one directive for this public review packet. Do not expand its authority.\n"
            f"<review_packet>{payload}</review_packet>"
        )
        options: dict[str, Any] = {"limits": {"turns": 2}}
        if self._output_model is not None:
            options["structured_output_model"] = self._output_model
        result = self._agent(prompt, **options)
        self.last_usage = self._usage(result)
        output = getattr(result, "structured_output", None)
        if hasattr(output, "model_dump"):
            output = output.model_dump()
        return Directive.from_object(output)

    @staticmethod
    def _usage(result: Any) -> SupervisorUsage:
        metrics = getattr(result, "metrics", None)
        usage = getattr(metrics, "accumulated_usage", {}) if metrics is not None else {}
        if not isinstance(usage, dict):
            usage = {}
        input_tokens = int(usage.get("inputTokens", 0) or 0)
        output_tokens = int(usage.get("outputTokens", 0) or 0)
        total_tokens = int(usage.get("totalTokens", input_tokens + output_tokens) or 0)
        durations = tuple(getattr(metrics, "cycle_durations", ()) or ())
        tool_metrics = getattr(metrics, "tool_metrics", {}) if metrics is not None else {}
        tool_calls = 0
        if isinstance(tool_metrics, dict):
            for value in tool_metrics.values():
                tool = getattr(value, "tool", {})
                if isinstance(value, dict):
                    tool = value.get("tool", {})
                if isinstance(tool, dict) and tool.get("toolUseId") == (
                    "aqh-supervisor-directive"
                ):
                    # Strands represents validated structured output internally as a
                    # synthetic tool event. It is not an external supervisor tool.
                    continue
                calls = getattr(value, "call_count", 0)
                if isinstance(value, dict):
                    calls = value.get("call_count", 0)
                tool_calls += int(calls or 0)
        return SupervisorUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=max(total_tokens, input_tokens + output_tokens),
            cycles=len(durations),
            tool_calls=tool_calls,
            wall_seconds=sum(float(value) for value in durations),
        )
