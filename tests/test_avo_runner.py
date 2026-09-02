from __future__ import annotations

import json
from pathlib import Path
from contextlib import redirect_stdout
import io
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_quality_harness.experiments.avo import AvoRun
from agent_quality_harness.cli import build_parser, main
from agent_quality_harness.experiments.avo import load_gate
from agent_quality_harness.experiments.directive import Directive, SupervisorUsage
from agent_quality_harness.experiments.providers import (
    InvocationReceipt,
    NativeInvocation,
    NativeInvocationError,
)


def receipt(session: str, *, tokens: int = 10) -> InvocationReceipt:
    return InvocationReceipt(
        client="scripted",
        executable="scripted",
        model="scripted-worker",
        session_id=session,
        input_tokens=tokens - 2,
        output_tokens=2,
        cached_input_tokens=0,
        turns=1,
        tool_calls=1,
        elapsed_seconds=0.1,
        exit_code=0,
        final_output="done",
    )


class ScriptedWorker:
    def __init__(self, root: Path, edits: list[str | BaseException]) -> None:
        self.root = root
        self.edits = list(edits)
        self.calls: list[str] = []

    def start(self, workspace: Path, prompt: str) -> NativeInvocation:
        self.calls.append("start")
        return NativeInvocation(("scripted",), workspace, prompt, "pending")

    def resume(self, workspace: Path, prompt: str, session_id: str) -> NativeInvocation:
        self.calls.append(f"resume:{session_id}")
        return NativeInvocation(("scripted",), workspace, prompt, session_id)

    def run(self, invocation: NativeInvocation) -> InvocationReceipt:
        self.calls.append("run")
        action = self.edits.pop(0)
        if isinstance(action, BaseException):
            raise action
        (self.root / "app.txt").write_text(action + "\n", encoding="utf-8")
        session = "worker-session" if invocation.session_id == "pending" else invocation.session_id
        return receipt(session)


class ScriptedSupervisor:
    def __init__(self, directives: list[Directive | BaseException]) -> None:
        self.directives = list(directives)
        self.calls = 0
        self.last_usage = SupervisorUsage()

    def decide(self, packet: object) -> Directive:
        self.calls += 1
        self.last_usage = SupervisorUsage(20, 5, 25, 1, 0, 0.2)
        value = self.directives.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


REPAIR = Directive("redirect", "minimal-repair", "Repair the failed check.", "Evidence is exact.")


class AvoRunnerTests(unittest.TestCase):
    def test_cli_experiment_is_explicit_and_requires_named_models_and_gate(self) -> None:
        args = build_parser().parse_args(
            [
                "experiment",
                "avo",
                "/tmp/candidate",
                "--task-file",
                "task.md",
                "--gate",
                "gate.json",
                "--worker",
                "codex",
                "--worker-model",
                "gpt-5.6-sol",
                "--supervisor-model",
                "fable",
            ]
        )

        self.assertEqual(args.experiment_command, "avo")
        self.assertEqual(args.worker, "codex")
        self.assertEqual(args.max_repair_turns, 2)

    def test_gate_loader_rejects_shell_strings_and_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gate = root / "gate.json"
            gate.write_text(
                '{"schema_version":1,"commands":[{"argv":"pytest"}],'
                '"protected_paths":[]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "argv string array"):
                load_gate(gate)
            gate.write_text(
                '{"schema_version":1,"commands":[{"argv":["pytest"]}],'
                '"protected_paths":["../secret"]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "inside"):
                load_gate(gate)

    def test_cli_wires_one_explicit_live_run_from_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "task.md").write_text("Implement task.\n", encoding="utf-8")
            (root / "gate.json").write_text(
                '{"schema_version":1,"commands":[{"argv":["python3","check.py"]}],'
                '"protected_paths":["check.py"]}',
                encoding="utf-8",
            )
            fake_run = unittest.mock.Mock()
            fake_run.run.return_value = {
                "terminal_reason": "passed",
                "worker_usage": {"model_calls": 1},
            }
            with (
                patch(
                    "agent_quality_harness.experiments.providers.claude_strands_model",
                    return_value=object(),
                ) as model_factory,
                patch(
                    "agent_quality_harness.experiments.supervisor.AvoSupervisor",
                    return_value=object(),
                ) as supervisor_factory,
                patch(
                    "agent_quality_harness.experiments.avo.AvoRun",
                    return_value=fake_run,
                ) as run_factory,
            ):
                with redirect_stdout(io.StringIO()):
                    status = main(
                        [
                            "experiment",
                            "avo",
                            str(root),
                            "--task-file",
                            "task.md",
                            "--gate",
                            "gate.json",
                            "--worker",
                            "codex",
                            "--worker-model",
                            "gpt-5.6-sol",
                            "--supervisor-model",
                            "fable",
                        ]
                    )

        self.assertEqual(status, 0)
        model_factory.assert_called_once()
        supervisor_factory.assert_called_once()
        configuration = run_factory.call_args.kwargs
        self.assertEqual(configuration["task"], "Implement task.\n")
        self.assertEqual(configuration["evaluator_argv"], (("python3", "check.py"),))
        self.assertEqual(configuration["protected_paths"], ("check.py",))

    def fixture(self, root: Path) -> None:
        (root / "app.txt").write_text("bad\n", encoding="utf-8")
        (root / "check.py").write_text(
            "from pathlib import Path\n"
            "raise SystemExit(0 if Path('app.txt').read_text().strip() == 'good' else 1)\n",
            encoding="utf-8",
        )
        (root / "protected.txt").write_text("keep\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=root,
            check=True,
        )

    def run_config(
        self,
        root: Path,
        worker: ScriptedWorker,
        supervisor: ScriptedSupervisor,
        *,
        max_reviews: int = 2,
        max_repairs: int = 2,
    ) -> AvoRun:
        return AvoRun(
            workspace=root,
            task="Make app.txt contain good.",
            worker=worker,
            supervisor=supervisor,
            evaluator_argv=((sys.executable, "check.py"),),
            protected_paths=("protected.txt", "check.py"),
            max_review_calls=max_reviews,
            max_repair_turns=max_repairs,
        )

    def test_initial_pass_uses_no_supervisor_credit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            worker = ScriptedWorker(root, ["good"])
            supervisor = ScriptedSupervisor([])

            ledger = self.run_config(root, worker, supervisor).run()

        self.assertEqual(ledger["terminal_reason"], "passed")
        self.assertEqual(supervisor.calls, 0)
        self.assertEqual(ledger["review_calls"], 0)
        self.assertEqual(ledger["repair_turns"], 0)

    def test_failure_is_reviewed_and_same_worker_session_resumes_to_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            worker = ScriptedWorker(root, ["still bad", "good"])
            supervisor = ScriptedSupervisor([REPAIR])

            ledger = self.run_config(root, worker, supervisor).run()
            stored = json.loads(Path(ledger["ledger_path"]).read_text())

        self.assertEqual(ledger["terminal_reason"], "passed-after-repair")
        self.assertEqual(worker.calls, ["start", "run", "resume:worker-session", "run"])
        self.assertEqual(ledger["review_calls"], 1)
        self.assertEqual(ledger["repair_turns"], 1)
        self.assertEqual(ledger["automatic_run_retries"], 0)
        self.assertEqual(ledger["worker_usage"]["total_tokens"], 20)
        self.assertEqual(ledger["supervisor_usage"]["total_tokens"], 25)
        self.assertEqual(stored["terminal_reason"], "passed-after-repair")

    def test_review_packet_includes_untracked_worker_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            worker = ScriptedWorker(root, ["still bad"])
            supervisor = ScriptedSupervisor([Directive("stop", "done", "Stop.", "Enough.")])
            original_run = worker.run

            def create_file(invocation: NativeInvocation) -> InvocationReceipt:
                value = original_run(invocation)
                (root / "new.py").write_text("NEW_VALUE = 1\n", encoding="utf-8")
                return value

            worker.run = create_file  # type: ignore[method-assign]
            packets: list[object] = []
            original_decide = supervisor.decide

            def capture(packet: object) -> Directive:
                packets.append(packet)
                return original_decide(packet)

            supervisor.decide = capture  # type: ignore[method-assign]
            self.run_config(root, worker, supervisor).run()

        self.assertIn("new.py", packets[0].worker_diff)  # type: ignore[attr-defined]
        self.assertIn("NEW_VALUE = 1", packets[0].worker_diff)  # type: ignore[attr-defined]

    def test_repeated_failure_stops_at_configured_budget_without_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            worker = ScriptedWorker(root, ["bad-1", "bad-2", "bad-3"])
            supervisor = ScriptedSupervisor([REPAIR, REPAIR])

            ledger = self.run_config(root, worker, supervisor).run()

        self.assertEqual(ledger["terminal_reason"], "failed-after-bounded-repair")
        self.assertEqual(worker.calls.count("start"), 1)
        self.assertEqual(ledger["review_calls"], 2)
        self.assertEqual(ledger["repair_turns"], 2)
        self.assertEqual(len(ledger["evaluations"]), 3)

    def test_worker_failure_is_terminal_and_never_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            failure = NativeInvocationError("worker failed", exit_code=2, elapsed_seconds=0.1)
            worker = ScriptedWorker(root, [failure])
            supervisor = ScriptedSupervisor([])

            ledger = self.run_config(root, worker, supervisor).run()

        self.assertEqual(ledger["terminal_reason"], "worker-failed")
        self.assertEqual(worker.calls, ["start", "run"])
        self.assertEqual(ledger["automatic_run_retries"], 0)

    def test_supervisor_failure_and_protected_change_are_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            worker = ScriptedWorker(root, ["still bad"])
            supervisor = ScriptedSupervisor([RuntimeError("review failed")])
            failed_review = self.run_config(root, worker, supervisor).run()
        self.assertEqual(failed_review["terminal_reason"], "supervisor-failed")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            worker = ScriptedWorker(root, ["still bad"])
            original_run = worker.run

            def alter_protected(invocation: NativeInvocation) -> InvocationReceipt:
                value = original_run(invocation)
                (root / "protected.txt").write_text("changed\n", encoding="utf-8")
                return value

            worker.run = alter_protected  # type: ignore[method-assign]
            protected = self.run_config(root, worker, ScriptedSupervisor([REPAIR])).run()
        self.assertEqual(protected["terminal_reason"], "protected-path-changed")
        self.assertEqual(protected["review_calls"], 0)


if __name__ == "__main__":
    unittest.main()
