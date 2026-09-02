"""Public command-line interface for Agent Quality Harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Sequence
from uuid import uuid4

from . import doctor, installer, local_endpoint, local_runner, uninstaller, verifier


COMMANDS = (
    ("install", "Install repository-local Claude Code and Codex hooks"),
    ("doctor", "Diagnose an installed repository treatment"),
    ("verify", "Run synthetic hook verification without model calls"),
    ("uninstall", "Restore the repository to its pre-install state"),
    ("local", "Use an existing local model endpoint"),
    ("experiment", "Run explicitly experimental quality comparisons"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aqh",
        description="Quality checks for native Claude Code, Codex, and local models.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in COMMANDS:
        command = subparsers.add_parser(name, help=help_text)
        if name == "install":
            command.add_argument("--target", type=Path, default=Path.cwd())
            command.add_argument(
                "--tool", choices=("claude", "codex", "both"), default="both"
            )
            command.add_argument("--gate", type=Path)
            command.add_argument(
                "--update",
                action="store_true",
                help="Transactionally replace an existing different installation",
            )
        elif name == "uninstall":
            command.add_argument("--target", type=Path, default=Path.cwd())
            command.add_argument(
                "--force",
                action="store_true",
                help="Discard later edits to managed files and restore pre-install bytes",
            )
        elif name == "doctor":
            command.add_argument("--target", type=Path, default=Path.cwd())
        elif name == "verify":
            command.add_argument("--target", type=Path, default=Path.cwd())
        elif name == "local":
            local_commands = command.add_subparsers(dest="local_command", required=True)
            local_doctor = local_commands.add_parser(
                "doctor", help="Probe an existing OpenAI-compatible local endpoint"
            )
            local_doctor.add_argument(
                "--endpoint", default="http://127.0.0.1:8080/v1"
            )
            local_doctor.add_argument("--model")
            local_run = local_commands.add_parser(
                "run", help="Run the enhanced worker against an existing endpoint"
            )
            local_run.add_argument("workspace", type=Path)
            local_run.add_argument(
                "--endpoint", default="http://127.0.0.1:8080/v1"
            )
            local_run.add_argument("--model", required=True)
        elif name == "experiment":
            experiment_commands = command.add_subparsers(
                dest="experiment_command", required=True
            )
            avo = experiment_commands.add_parser(
                "avo", help="Run bounded Claude-reviewed repair cycles"
            )
            avo.add_argument("workspace", type=Path)
            avo.add_argument("--task-file", type=Path, required=True)
            avo.add_argument("--gate", type=Path, required=True)
            avo.add_argument("--worker", choices=("claude", "codex"), required=True)
            avo.add_argument("--worker-model", required=True)
            avo.add_argument("--worker-effort", default="high")
            avo.add_argument("--supervisor-model", required=True)
            avo.add_argument("--supervisor-effort", default="high")
            avo.add_argument("--max-review-calls", type=int, default=2)
            avo.add_argument("--max-repair-turns", type=int, default=2)
            avo.add_argument("--session-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "install":
        manifest = installer.install(
            args.target,
            tool=args.tool,
            gate_source=args.gate,
            update=args.update,
        )
        names = {
            ("claude",): "Claude Code",
            ("codex",): "Codex",
            ("claude", "codex"): "Claude Code and Codex",
        }[tuple(manifest["tools"])]
        print(f"Installed Agent Quality Harness for {names}.")
        print("Next: run `aqh doctor`, then open the repository in your native client.")
        return 0
    if args.command == "uninstall":
        uninstaller.uninstall(args.target, force=args.force)
        print("Restored the repository to its exact pre-install state.")
        return 0
    if args.command == "doctor":
        report = doctor.diagnose(args.target)
        print(f"status: {report['status']}")
        print(f"clients: {', '.join(report['tools'])}")
        print(f"gate: {report['gate_kind']}")
        if report["latest_evidence"] is None:
            print("latest evidence: none yet")
        else:
            evidence = report["latest_evidence"]
            print(
                "latest evidence: "
                f"{evidence['outcome']}, {evidence['check_count']} checks, "
                f"{evidence['blocks']} blocks, model {evidence['model']}"
            )
        for issue in report["issues"]:
            print(f"issue: {issue}")
        print(f"next: {report['recommendation']}")
        return 0 if report["status"] == "ok" else 1
    if args.command == "verify":
        report = verifier.verify(args.target)
        for name, status in report["checks"].items():
            print(f"{status.upper()} {name}")
        return 0 if report["status"] == "pass" else 1
    if args.command == "local" and args.local_command == "doctor":
        report = local_endpoint.diagnose_endpoint(
            args.endpoint, expected_model=args.model
        )
        print(f"endpoint: {report.endpoint}")
        print(f"reachable: {'yes' if report.reachable else 'no'}")
        print(f"healthy: {'yes' if report.healthy else 'no'}")
        model_match = "not requested" if report.model_match is None else (
            "yes" if report.model_match else "no"
        )
        print(f"model match: {model_match}")
        print(f"models: {', '.join(report.model_ids) if report.model_ids else 'none'}")
        print(f"containment: {report.containment_mode}")
        missing = report.missing_optional_dependencies
        print(f"local extra: {'ready' if not missing else 'missing ' + ', '.join(missing)}")
        if report.error:
            print(f"diagnostic: {report.error}")
        return 0 if report.ready else 1
    if args.command == "local" and args.local_command == "run":
        ledger = local_runner.run_local(args.workspace, args.endpoint, args.model)
        print(json.dumps(ledger, indent=2, sort_keys=True))
        return 0 if ledger["terminal_reason"].startswith("passed") else 1
    if args.command == "experiment" and args.experiment_command == "avo":
        # Keep experiment-only imports out of the dependency-free everyday path.
        from .experiments.avo import AvoRun, load_gate
        from .experiments.providers import (
            ClaudeProvider,
            CodexProvider,
            claude_strands_model,
        )
        from .experiments.supervisor import AvoSupervisor

        workspace = args.workspace.resolve()
        task_path = args.task_file
        if not task_path.is_absolute():
            task_path = workspace / task_path
        gate_path = args.gate
        if not gate_path.is_absolute():
            gate_path = workspace / gate_path
        try:
            task = task_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(f"cannot read AVO task file {task_path}: {error}") from error
        commands, protected_paths = load_gate(gate_path)
        worker = (
            ClaudeProvider(args.worker_model, args.worker_effort)
            if args.worker == "claude"
            else CodexProvider(args.worker_model, args.worker_effort)
        )
        session_root = (
            args.session_root.resolve()
            if args.session_root is not None
            else Path(tempfile.gettempdir()) / "agent-quality-harness" / "avo-sessions"
        )
        supervisor_model = claude_strands_model(
            model_id=args.supervisor_model,
            effort=args.supervisor_effort,
            working_dir=session_root,
        )
        supervisor = AvoSupervisor(
            workspace=workspace,
            session_root=session_root,
            session_id=f"avo-{uuid4()}",
            model=supervisor_model,
        )
        ledger = AvoRun(
            workspace=workspace,
            task=task,
            worker=worker,
            supervisor=supervisor,
            evaluator_argv=commands,
            protected_paths=protected_paths,
            max_review_calls=args.max_review_calls,
            max_repair_turns=args.max_repair_turns,
        ).run()
        print(json.dumps(ledger, indent=2, sort_keys=True))
        return 0 if ledger["terminal_reason"].startswith("passed") else 1
    print(f"aqh {args.command} is not available in this build", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
