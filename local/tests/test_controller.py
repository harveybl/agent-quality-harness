from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from local.harness.controller import Controller


class FakeWorker:
    def __init__(self, *, repair: bool) -> None:
        self.should_repair = repair
        self.calls: list[str] = []
        self.plan_read: str | None = None

    def plan(self, task: str, inventory: list[str], tools: object) -> tuple[dict, dict]:
        self.calls.append("plan")
        self.plan_read = tools.read_file("starter/calculator.py", 1, 2)
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
            "starter/calculator.py",
            "return 0",
            "return 1",
            line=2,
            anchor="return 0",
        )
        return {"model_calls": 2, "tokens": 30}

    def repair(self, task: str, evidence: str, diff: str, tools: object) -> dict:
        self.calls.append("repair")
        if self.should_repair:
            tools.replace_text(
                "starter/calculator.py",
                "return 1",
                "return a + b",
                line=2,
                anchor="return 1",
            )
        return {"model_calls": 1, "tokens": 10}


class FailingPlanWorker:
    def plan(self, task: str, inventory: list[str], tools: object) -> tuple[dict, dict]:
        error = RuntimeError("structured plan exceeded its bounded phase")
        error.model_calls = 7  # type: ignore[attr-defined]
        raise error


class ControllerTests(unittest.TestCase):
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
                        "python3",
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

    def test_runs_plan_implementation_checks_and_one_successful_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            ledger = Controller(root, FakeWorker(repair=True)).run()
        self.assertEqual(ledger["terminal_reason"], "passed-after-continuation")
        self.assertEqual(ledger["continuations"], 1)
        self.assertEqual(ledger["model_calls"], 4)
        self.assertEqual(len(ledger["checks"]), 2)

    def test_never_retries_a_failed_run_beyond_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            worker = FakeWorker(repair=False)
            ledger = Controller(root, worker).run()
        self.assertEqual(worker.calls, ["plan", "implement", "repair"])
        self.assertIn("return 0", worker.plan_read or "")
        self.assertEqual(ledger["terminal_reason"], "failed-after-bounded-continuation")
        self.assertEqual(ledger["continuations"], 1)

    def test_ledger_serializes_environment_and_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            ledger = Controller(root, FakeWorker(repair=True)).run()
            path = root / "runs/ledger.json"
            self.assertTrue(path.is_file())
            loaded = json.loads(path.read_text())
        self.assertEqual(loaded["schema_version"], 1)
        self.assertEqual(loaded["changed_files"], ["starter/calculator.py"])
        self.assertIn("python", loaded["environment"])
        self.assertIn("started_at", ledger)

    def test_phase_failure_is_ledgered_without_an_automatic_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)

            ledger = Controller(root, FailingPlanWorker()).run()
            stored = json.loads((root / "runs/ledger.json").read_text())

        self.assertEqual(ledger["terminal_reason"], "failed-plan")
        self.assertEqual(ledger["model_calls"], 7)
        self.assertEqual(ledger["automatic_run_retries"], 0)
        self.assertIn("structured plan exceeded", ledger["major_failure_reason"])
        self.assertEqual(stored["terminal_reason"], "failed-plan")


if __name__ == "__main__":
    unittest.main()
