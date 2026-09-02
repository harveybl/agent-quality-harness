"""Four-phase local coding controller with one bounded continuation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import time
from typing import Any, Protocol

from .contracts import Plan, anchor_window, validate_anchor
from .file_tools import FileTools
from .ledger import environment, write_ledger


class Worker(Protocol):
    def plan(self, task: str, inventory: list[str]) -> tuple[dict, dict]: ...
    def implement(self, task: str, plan: Plan, windows: dict[str, str], tools: FileTools) -> dict: ...
    def repair(self, task: str, evidence: str, diff: str, tools: FileTools) -> dict: ...


def _snapshot(root: Path, prefixes: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for prefix in prefixes:
        base = root / prefix
        files = [base] if base.is_file() else base.rglob("*") if base.exists() else []
        for path in files:
            if path.is_file() and not path.is_symlink():
                relative = path.relative_to(root).as_posix()
                if relative.split("/", 1)[0] in {"runs", ".git"}:
                    continue
                try:
                    values[relative] = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
    return values


def _diff(before: dict[str, str], root: Path) -> tuple[list[str], str]:
    rows: list[str] = []
    changed: list[str] = []
    paths = set(before)
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            relative = path.relative_to(root).as_posix()
            if relative.split("/", 1)[0] in {"runs", ".git"}:
                continue
            paths.add(relative)
    for relative in sorted(paths):
        old = before.get(relative, "")
        path = root / relative
        try:
            new = path.read_text(encoding="utf-8") if path.is_file() else ""
        except UnicodeDecodeError:
            continue
        if old == new:
            continue
        changed.append(relative)
        rows.extend(
            difflib.unified_diff(
                old.splitlines(),
                new.splitlines(),
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
                lineterm="",
            )
        )
    return changed, "\n".join(rows[-800:])


class Controller:
    def __init__(
        self,
        root: Path,
        worker: Worker,
        *,
        run_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.worker = worker
        self.run_metadata = dict(run_metadata or {})

    def run(self) -> dict[str, Any]:
        started = datetime.now(timezone.utc).isoformat()
        config = json.loads((self.root / "contract.json").read_text(encoding="utf-8"))
        task = (self.root / "task.md").read_text(encoding="utf-8")
        required = {
            "mutable_paths",
            "protected_paths",
            "public_check_argv",
            "navigation_budget",
            "max_continuations",
        }
        if set(config) != required:
            raise ValueError(f"contract.json must contain exactly {sorted(required)}")
        if config["max_continuations"] not in (0, 1):
            raise ValueError("max_continuations must be 0 or 1")
        tools = FileTools(
            self.root,
            mutable_paths=config["mutable_paths"],
            protected_paths=config["protected_paths"],
            public_check_argv=config["public_check_argv"],
            navigation_budget=config["navigation_budget"],
        )
        baseline = _snapshot(self.root, ["."])
        mutable_prefixes = tuple(path.rstrip("/") for path in config["mutable_paths"])
        inventory = sorted(
            path
            for path in baseline
            if any(path == prefix or path.startswith(prefix + "/") for prefix in mutable_prefixes)
        )
        phase_seconds: dict[str, float] = {}
        model_calls = 0
        tokens = 0

        mark = time.monotonic()
        plan_value, metrics = self.worker.plan(task, inventory)
        phase_seconds["plan"] = round(time.monotonic() - mark, 3)
        model_calls += int(metrics.get("model_calls", 1))
        tokens += int(metrics.get("tokens", 0))
        plan = Plan.from_object(plan_value)
        windows: dict[str, str] = {}
        for change in plan.changes:
            path = self.root / change.path
            validate_anchor(path, change.line, change.anchor)
            windows[change.path] = anchor_window(path, change.line)

        mark = time.monotonic()
        metrics = self.worker.implement(task, plan, windows, tools)
        phase_seconds["implementation"] = round(time.monotonic() - mark, 3)
        model_calls += int(metrics.get("model_calls", 1))
        tokens += int(metrics.get("tokens", 0))
        checks: list[dict[str, Any]] = []
        changed, diff = _diff(baseline, self.root)
        if not changed:
            terminal = "failed-no-change"
            continuations = 0
        else:
            mark = time.monotonic()
            result = tools.run_public_tests()
            phase_seconds["evaluation"] = round(time.monotonic() - mark, 3)
            checks.append(result)
            continuations = 0
            if result["passed"]:
                terminal = "passed"
            elif config["max_continuations"] == 1:
                continuations = 1
                evidence = (result["stderr_tail"] or result["stdout_tail"] or "no output").strip()
                mark = time.monotonic()
                metrics = self.worker.repair(task, evidence, diff, tools)
                phase_seconds["continuation"] = round(time.monotonic() - mark, 3)
                model_calls += int(metrics.get("model_calls", 1))
                tokens += int(metrics.get("tokens", 0))
                result = tools.run_public_tests()
                checks.append(result)
                terminal = "passed-after-continuation" if result["passed"] else "failed-after-bounded-continuation"
            else:
                terminal = "failed"
        changed, _ = _diff(baseline, self.root)
        ledger = {
            "schema_version": 1,
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "terminal_reason": terminal,
            "model_calls": model_calls,
            "tokens": tokens,
            "tool_calls": tools.tool_calls,
            "first_write_at": tools.first_write_at,
            "changed_files": changed,
            "checks": checks,
            "continuations": continuations,
            "automatic_run_retries": 0,
            "phase_seconds": phase_seconds,
            "environment": environment(self.root),
        }
        ledger.update(self.run_metadata)
        write_ledger(self.root, ledger)
        return ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--endpoint", default="http://model:8080/v1")
    parser.add_argument("--model", default="qwen-local")
    args = parser.parse_args()
    from .worker import StrandsWorker

    ledger = Controller(args.workspace, StrandsWorker(args.endpoint, args.model)).run()
    print(json.dumps(ledger, indent=2, sort_keys=True))
    return 0 if ledger["terminal_reason"].startswith("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
