"""Direct normal-environment Claude Code and Codex experiment providers."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
from uuid import UUID, uuid4


PAID_ROUTE_ENVIRONMENT = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
    }
)


@dataclass(frozen=True)
class NativeInvocation:
    argv: tuple[str, ...]
    cwd: Path
    stdin: str
    session_id: str


@dataclass(frozen=True)
class InvocationReceipt:
    client: str
    executable: str
    model: str
    session_id: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    turns: int
    tool_calls: int
    elapsed_seconds: float
    exit_code: int
    final_output: str

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class NativeInvocationError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int | None, elapsed_seconds: float) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.elapsed_seconds = elapsed_seconds


def _events(output: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            values.append(value)
    return values


def _metric(row: dict[str, Any], key: str, *, default: int | None = None) -> int:
    if key not in row:
        if default is None:
            raise ValueError(f"native usage is missing {key}")
        return default
    value = row[key]
    if type(value) is not int or value < 0:
        raise ValueError(f"native usage {key} is invalid")
    return value


def _validate_environment(environment: dict[str, str]) -> None:
    present = sorted(key for key in PAID_ROUTE_ENVIRONMENT if environment.get(key))
    if present:
        raise RuntimeError(
            "AVO personal-plan experiment refuses paid/external route variables: "
            + ", ".join(present)
        )


class _Provider:
    client: str

    def run(
        self,
        invocation: NativeInvocation,
        *,
        timeout_seconds: int = 3600,
    ) -> InvocationReceipt:
        _validate_environment(dict(os.environ))
        executable = shutil.which(invocation.argv[0])
        if executable is None:
            raise FileNotFoundError(f"{invocation.argv[0]} is not installed")
        started = time.monotonic()
        try:
            process = subprocess.run(
                invocation.argv,
                cwd=invocation.cwd,
                input=invocation.stdin,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise NativeInvocationError(
                f"{self.client} timed out",
                exit_code=None,
                elapsed_seconds=time.monotonic() - started,
            ) from error
        elapsed = time.monotonic() - started
        if process.returncode != 0:
            diagnostic = (process.stderr or process.stdout or "no output").strip()[-4000:]
            raise NativeInvocationError(
                f"{self.client} failed: {diagnostic}",
                exit_code=process.returncode,
                elapsed_seconds=elapsed,
            )
        return self.parse(
            process.stdout,
            elapsed_seconds=elapsed,
            exit_code=process.returncode,
            requested_session_id=invocation.session_id,
            executable=executable,
        )


class ClaudeProvider(_Provider):
    client = "claude"

    def __init__(self, model: str, effort: str = "high") -> None:
        if not model or effort not in {"low", "medium", "high", "xhigh", "max"}:
            raise ValueError("invalid Claude model or effort")
        self.model = model
        self.effort = effort

    def _common(self) -> tuple[str, ...]:
        return (
            "--print",
            "--verbose",
            "--output-format",
            "stream-json",
            "--input-format",
            "text",
            "--model",
            self.model,
            "--effort",
            self.effort,
        )

    def start(self, workspace: Path, prompt: str) -> NativeInvocation:
        session = str(uuid4())
        return NativeInvocation(
            argv=("claude", *self._common(), "--session-id", session),
            cwd=workspace,
            stdin=prompt,
            session_id=session,
        )

    def resume(self, workspace: Path, prompt: str, session_id: str) -> NativeInvocation:
        session = str(UUID(session_id))
        return NativeInvocation(
            argv=("claude", *self._common(), "--resume", session),
            cwd=workspace,
            stdin=prompt,
            session_id=session,
        )

    def parse(
        self,
        output: str,
        *,
        elapsed_seconds: float,
        exit_code: int,
        requested_session_id: str,
        executable: str = "claude",
    ) -> InvocationReceipt:
        events = _events(output)
        result_rows = [value for value in events if value.get("type") == "result"]
        if len(result_rows) != 1:
            raise ValueError("Claude output must contain exactly one result event")
        result = result_rows[0]
        observed_sessions = {
            value["session_id"]
            for value in events
            if isinstance(value.get("session_id"), str)
        }
        if observed_sessions != {requested_session_id}:
            raise ValueError("Claude session identity changed or was missing")
        usage = result.get("usage")
        if not isinstance(usage, dict):
            raise ValueError("Claude result is missing usage")
        models = {
            value["model"] for value in events if isinstance(value.get("model"), str)
        }
        model = next(iter(models)) if len(models) == 1 else self.model
        final = result.get("result")
        if not isinstance(final, str):
            raise ValueError("Claude result is missing final output")
        tool_ids: set[str] = set()
        for value in events:
            self._collect_claude_tools(value, tool_ids)
        return InvocationReceipt(
            client=self.client,
            executable=executable,
            model=model,
            session_id=requested_session_id,
            input_tokens=_metric(usage, "input_tokens"),
            output_tokens=_metric(usage, "output_tokens"),
            cached_input_tokens=(
                _metric(usage, "cache_read_input_tokens", default=0)
                + _metric(usage, "cache_creation_input_tokens", default=0)
            ),
            turns=_metric(result, "num_turns", default=1),
            tool_calls=len(tool_ids),
            elapsed_seconds=elapsed_seconds,
            exit_code=exit_code,
            final_output=final,
        )

    @classmethod
    def _collect_claude_tools(cls, value: object, found: set[str]) -> None:
        if isinstance(value, dict):
            if value.get("type") == "tool_use" and isinstance(value.get("id"), str):
                found.add(value["id"])
            for child in value.values():
                cls._collect_claude_tools(child, found)
        elif isinstance(value, list):
            for child in value:
                cls._collect_claude_tools(child, found)


class CodexProvider(_Provider):
    client = "codex"

    def __init__(self, model: str, effort: str = "high") -> None:
        if not model or effort not in {"low", "medium", "high", "xhigh", "max"}:
            raise ValueError("invalid Codex model or effort")
        self.model = model
        self.effort = effort

    def _common(self) -> tuple[str, ...]:
        return (
            "--json",
            "--model",
            self.model,
            "--config",
            f'model_reasoning_effort="{self.effort}"',
            "--config",
            'forced_login_method="chatgpt"',
        )

    def start(self, workspace: Path, prompt: str) -> NativeInvocation:
        return NativeInvocation(
            argv=("codex", "exec", *self._common(), "--cd", str(workspace), "-"),
            cwd=workspace,
            stdin=prompt,
            session_id="pending",
        )

    def resume(self, workspace: Path, prompt: str, session_id: str) -> NativeInvocation:
        if not session_id or session_id == "pending":
            raise ValueError("Codex resume requires a captured session ID")
        return NativeInvocation(
            argv=("codex", "exec", *self._common(), "resume", session_id, "-"),
            cwd=workspace,
            stdin=prompt,
            session_id=session_id,
        )

    def parse(
        self,
        output: str,
        *,
        elapsed_seconds: float,
        exit_code: int,
        requested_session_id: str = "pending",
        executable: str = "codex",
    ) -> InvocationReceipt:
        events = _events(output)
        sessions = {
            value["thread_id"]
            for value in events
            if isinstance(value.get("thread_id"), str)
        }
        if len(sessions) != 1:
            raise ValueError("Codex output must contain exactly one thread ID")
        session = next(iter(sessions))
        if requested_session_id != "pending" and session != requested_session_id:
            raise ValueError("Codex session identity changed")
        usage_rows = [
            value["usage"]
            for value in events
            if isinstance(value.get("usage"), dict)
        ]
        if not usage_rows:
            raise ValueError("Codex output is missing usage")
        usage = usage_rows[-1]
        final_rows = [
            item.get("text")
            for value in events
            if isinstance((item := value.get("item")), dict)
            and item.get("type") == "agent_message"
            and isinstance(item.get("text"), str)
        ]
        if not final_rows:
            raise ValueError("Codex output is missing final agent output")
        models = {
            value["model"] for value in events if isinstance(value.get("model"), str)
        }
        model = next(iter(models)) if len(models) == 1 else self.model
        tool_ids = {
            item["id"]
            for value in events
            if isinstance((item := value.get("item")), dict)
            and item.get("type") in {"command_execution", "file_change", "mcp_tool_call"}
            and isinstance(item.get("id"), str)
        }
        return InvocationReceipt(
            client=self.client,
            executable=executable,
            model=model,
            session_id=session,
            input_tokens=_metric(usage, "input_tokens"),
            output_tokens=_metric(usage, "output_tokens"),
            cached_input_tokens=_metric(usage, "cached_input_tokens", default=0),
            turns=sum(value.get("type") == "turn.completed" for value in events) or 1,
            tool_calls=len(tool_ids),
            elapsed_seconds=elapsed_seconds,
            exit_code=exit_code,
            final_output=final_rows[-1],
        )
