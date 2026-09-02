from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from agent_quality_harness.cli import main
from agent_quality_harness.local_endpoint import EndpointReport
from agent_quality_harness.local_runner import run_local


class FakeWorker:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def plan(self, task: str, inventory: list[str]) -> tuple[dict, dict]:
        self.calls.append("plan")
        return (
            {
                "changes": [
                    {
                        "path": "starter/calculator.py",
                        "line": 2,
                        "anchor": "return 0",
                        "change": "implement addition",
                        "acceptance_ids": ["AC-1"],
                    }
                ]
            },
            {"model_calls": 1, "tokens": 20},
        )

    def implement(self, task: str, plan: object, windows: dict, tools: object) -> dict:
        self.calls.append("implement")
        tools.replace_text(
            "starter/calculator.py", "return 0", "return 1", line=2, anchor="return 0"
        )
        return {"model_calls": 1, "tokens": 30}

    def repair(self, task: str, evidence: str, diff: str, tools: object) -> dict:
        self.calls.append("repair")
        tools.replace_text(
            "starter/calculator.py", "return 1", "return a + b", line=2, anchor="return 1"
        )
        return {"model_calls": 1, "tokens": 10}


def ready_report(endpoint: str, model: str) -> EndpointReport:
    return EndpointReport(
        endpoint=endpoint,
        reachable=True,
        healthy=True,
        model_ids=(model,),
        expected_model=model,
        model_match=True,
        containment_mode="native-process-bounds-only",
        missing_optional_dependencies=(),
        error=None,
    )


class LocalRunnerTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        (root / "starter").mkdir()
        (root / "public_checks").mkdir()
        (root / "starter/calculator.py").write_text(
            "def add(a, b):\n    return 0\n", encoding="utf-8"
        )
        (root / "public_checks/test_calculator.py").write_text(
            "import unittest\nfrom starter.calculator import add\n"
            "class T(unittest.TestCase):\n"
            "    def test_add(self): self.assertEqual(add(2, 3), 5)\n",
            encoding="utf-8",
        )
        (root / "task.md").write_text("Implement add.\n", encoding="utf-8")
        (root / "contract.json").write_text(
            json.dumps(
                {
                    "mutable_paths": ["starter"],
                    "protected_paths": ["public_checks", "contract.json"],
                    "public_check_argv": [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "public_checks",
                        "-v",
                    ],
                    "navigation_budget": 8,
                    "max_continuations": 1,
                }
            ),
            encoding="utf-8",
        )

    def test_run_uses_endpoint_model_one_continuation_and_zero_run_retries(self) -> None:
        endpoint = "http://127.0.0.1:8080/v1"
        worker = FakeWorker()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            with mock.patch(
                "agent_quality_harness.local_runner.diagnose_endpoint",
                return_value=ready_report(endpoint, "qwen-local"),
            ) as diagnose:
                ledger = run_local(root, endpoint, "qwen-local", worker=worker)

        diagnose.assert_called_once_with(endpoint, expected_model="qwen-local")
        self.assertEqual(worker.calls, ["plan", "implement", "repair"])
        self.assertEqual(ledger["terminal_reason"], "passed-after-continuation")
        self.assertEqual(ledger["continuations"], 1)
        self.assertEqual(ledger["automatic_run_retries"], 0)
        self.assertEqual(ledger["model"], "qwen-local")
        self.assertEqual(ledger["endpoint"], endpoint)

    def test_cli_local_run_prints_ledger_and_maps_failure_to_exit_one(self) -> None:
        ledger = {
            "terminal_reason": "failed-after-bounded-continuation",
            "automatic_run_retries": 0,
        }
        output = StringIO()
        with mock.patch(
            "agent_quality_harness.local_runner.run_local", return_value=ledger
        ) as run:
            with redirect_stdout(output):
                status = main(
                    [
                        "local",
                        "run",
                        "/tmp/workspace",
                        "--endpoint",
                        "http://127.0.0.1:8080/v1",
                        "--model",
                        "muse-local",
                    ]
                )

        self.assertEqual(status, 1)
        run.assert_called_once_with(
            Path("/tmp/workspace"), "http://127.0.0.1:8080/v1", "muse-local"
        )
        self.assertIn("failed-after-bounded-continuation", output.getvalue())


if __name__ == "__main__":
    unittest.main()
