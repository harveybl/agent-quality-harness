"""Explicit bounded review-and-repair lifecycle for native CLI experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import difflib
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any

from .directive import ReviewPacket, SupervisorUsage
from .providers import InvocationReceipt


def load_gate(path: Path) -> tuple[tuple[tuple[str, ...], ...], tuple[str, ...]]:
    """Load only the deterministic commands and protected paths used by AVO."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read AVO gate {path}: {error}") from error
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("AVO gate schema_version must be 1")
    raw_commands = value.get("commands")
    raw_protected = value.get("protected_paths", [])
    if not isinstance(raw_commands, list) or not raw_commands:
        raise ValueError("AVO gate requires at least one command")
    commands: list[tuple[str, ...]] = []
    for row in raw_commands:
        argv = row.get("argv") if isinstance(row, dict) else None
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(part, str) or not part for part in argv)
        ):
            raise ValueError("each AVO gate command requires a nonempty argv string array")
        commands.append(tuple(argv))
    if not isinstance(raw_protected, list) or any(
        not isinstance(item, str) for item in raw_protected
    ):
        raise ValueError("AVO gate protected_paths must be a string array")
    protected = tuple(_relative_path(item) for item in raw_protected)
    return tuple(commands), protected


def _relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError("protected paths must stay inside the workspace")
    return value


@dataclass(frozen=True)
class AvoRun:
    workspace: Path
    task: str
    worker: Any
    supervisor: Any
    evaluator_argv: tuple[tuple[str, ...], ...]
    protected_paths: tuple[str, ...] = ()
    max_review_calls: int = 2
    max_repair_turns: int = 2

    def __post_init__(self) -> None:
        if not self.workspace.is_dir() or not self.task.strip():
            raise ValueError("AVO requires an existing workspace and nonempty task")
        if not self.evaluator_argv or any(not command for command in self.evaluator_argv):
            raise ValueError("AVO requires at least one evaluator argument array")
        if type(self.max_review_calls) is not int or not 0 <= self.max_review_calls <= 7:
            raise ValueError("max_review_calls must be from 0 to 7")
        if type(self.max_repair_turns) is not int or not 0 <= self.max_repair_turns <= 7:
            raise ValueError("max_repair_turns must be from 0 to 7")
        for path in self.protected_paths:
            _relative_path(path)

    def _evaluate(self, root: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for command in self.evaluator_argv:
            try:
                process = subprocess.run(
                    command,
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=1800,
                )
                rows.append(
                    {
                        "argv": list(command),
                        "passed": process.returncode == 0,
                        "exit_code": process.returncode,
                        "stdout_tail": process.stdout[-4000:],
                        "stderr_tail": process.stderr[-6000:],
                    }
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                rows.append(
                    {
                        "argv": list(command),
                        "passed": False,
                        "exit_code": None,
                        "stdout_tail": "",
                        "stderr_tail": str(error)[-6000:],
                    }
                )
        return rows

    def _protected_changes(self, root: Path) -> list[str]:
        if not self.protected_paths:
            return []
        process = subprocess.run(
            [
                "git",
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                *self.protected_paths,
            ],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if process.returncode != 0:
            return ["git-status-failed"]
        return [line for line in process.stdout.splitlines() if line.strip()]

    @staticmethod
    def _diff(root: Path) -> str:
        process = subprocess.run(
            ["git", "diff", "--no-ext-diff", "HEAD", "--", "."],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        parts = [process.stdout]
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if untracked.returncode == 0:
            for name in (item for item in untracked.stdout.split("\0") if item):
                path = root / name
                try:
                    content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    parts.append(f"\nUntracked non-text file: {name}\n")
                    continue
                parts.append(
                    "\n".join(
                        difflib.unified_diff(
                            (),
                            content.splitlines(),
                            fromfile="/dev/null",
                            tofile=f"b/{name}",
                            lineterm="",
                        )
                    )
                )
        value = "\n".join(parts)[-40_000:].strip()
        return value or "(no textual Git diff was available)"

    @staticmethod
    def _evidence(rows: list[dict[str, Any]]) -> str:
        failures = []
        for row in rows:
            if row["passed"]:
                continue
            output = (row["stderr_tail"] or row["stdout_tail"] or "no output").strip()
            failures.append(f"argv={row['argv']!r} exit={row['exit_code']}\n{output}")
        return "\n\n".join(failures) or "deterministic checks did not pass"

    @staticmethod
    def _worker_usage(receipts: list[InvocationReceipt]) -> dict[str, Any]:
        return {
            "model_calls": len(receipts),
            "input_tokens": sum(value.input_tokens for value in receipts),
            "output_tokens": sum(value.output_tokens for value in receipts),
            "total_tokens": sum(value.total_tokens for value in receipts),
            "cached_input_tokens": sum(value.cached_input_tokens for value in receipts),
            "tool_calls": sum(value.tool_calls for value in receipts),
            "elapsed_seconds": round(sum(value.elapsed_seconds for value in receipts), 3),
        }

    @staticmethod
    def _supervisor_usage(values: list[SupervisorUsage]) -> dict[str, Any]:
        return {
            "model_calls": len(values),
            "input_tokens": sum(value.input_tokens for value in values),
            "output_tokens": sum(value.output_tokens for value in values),
            "total_tokens": sum(value.total_tokens for value in values),
            "tool_calls": sum(value.tool_calls for value in values),
            "cycles": sum(value.cycles for value in values),
            "elapsed_seconds": round(sum(value.wall_seconds for value in values), 3),
        }

    def _write_ledger(self, root: Path, ledger: dict[str, Any]) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        path = root / ".agent-quality/runs" / f"avo-{stamp}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def run(self) -> dict[str, Any]:
        root = self.workspace.resolve()
        receipts: list[InvocationReceipt] = []
        supervisor_usage: list[SupervisorUsage] = []
        directives: list[dict[str, Any]] = []
        evaluations: list[dict[str, Any]] = []
        review_calls = 0
        repair_turns = 0
        error: str | None = None
        session_id = "pending"

        try:
            invocation = self.worker.start(root, self.task)
            receipt = self.worker.run(invocation)
            receipts.append(receipt)
            session_id = receipt.session_id
        except Exception as failure:
            terminal = "worker-failed"
            error = str(failure)
        else:
            while True:
                protected = self._protected_changes(root)
                if protected:
                    terminal = "protected-path-changed"
                    error = "\n".join(protected)
                    break
                rows = self._evaluate(root)
                evaluations.append(
                    {
                        "cycle": repair_turns,
                        "passed": all(row["passed"] for row in rows),
                        "checks": rows,
                    }
                )
                if evaluations[-1]["passed"]:
                    terminal = "passed" if repair_turns == 0 else "passed-after-repair"
                    break
                if (
                    repair_turns >= self.max_repair_turns
                    or review_calls >= self.max_review_calls
                ):
                    terminal = "failed-after-bounded-repair"
                    break
                packet = ReviewPacket(
                    task_summary=self.task,
                    worker_diff=self._diff(root),
                    check_evidence=self._evidence(rows),
                    repair_cycle=repair_turns,
                    repairs_remaining=self.max_repair_turns - repair_turns,
                )
                review_calls += 1
                try:
                    directive = self.supervisor.decide(packet)
                    usage = getattr(self.supervisor, "last_usage", SupervisorUsage())
                    if isinstance(usage, SupervisorUsage):
                        supervisor_usage.append(usage)
                except Exception as failure:
                    terminal = "supervisor-failed"
                    error = str(failure)
                    break
                directives.append(asdict(directive))
                if directive.action == "stop":
                    terminal = "supervisor-stopped"
                    break
                prompt = (
                    "Continue the same worker session. Do not restart or broaden scope.\n"
                    f"Strategy: {directive.strategy}\n"
                    f"Instruction: {directive.instruction}\n"
                    f"Rationale: {directive.rationale}\n"
                    f"Deterministic evidence:\n{packet.check_evidence}"
                )
                try:
                    invocation = self.worker.resume(root, prompt, session_id)
                    receipt = self.worker.run(invocation)
                    receipts.append(receipt)
                    if receipt.session_id != session_id:
                        raise RuntimeError("worker repair returned a different session ID")
                    repair_turns += 1
                except Exception as failure:
                    terminal = "worker-failed"
                    error = str(failure)
                    break

        ledger: dict[str, Any] = {
            "schema_version": 1,
            "experiment": "avo-review-repair",
            "terminal_reason": terminal,
            "task": self.task,
            "worker_session_id": session_id,
            "review_calls": review_calls,
            "repair_turns": repair_turns,
            "max_review_calls": self.max_review_calls,
            "max_repair_turns": self.max_repair_turns,
            "automatic_run_retries": 0,
            "evaluations": evaluations,
            "directives": directives,
            "worker_receipts": [asdict(value) for value in receipts],
            "worker_usage": self._worker_usage(receipts),
            "supervisor_usage": self._supervisor_usage(supervisor_usage),
            "supervisor_identity": getattr(self.supervisor, "model_identity", {}),
            "error": error,
        }
        path = self._write_ledger(root, ledger)
        ledger["ledger_path"] = str(path)
        path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return ledger
