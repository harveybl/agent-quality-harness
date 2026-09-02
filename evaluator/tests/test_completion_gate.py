from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest import mock


class CompletionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = importlib.import_module("evaluator.completion_gate")

    def fixture(
        self,
        root: Path,
        *,
        max_blocks: int = 2,
        protected_paths: list[str] | None = None,
    ) -> Path:
        quality = root / ".agent-quality"
        quality.mkdir()
        script = quality / "completion_gate.py"
        script.write_text("fixture\n", encoding="utf-8")
        (quality / "gate.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "max_blocks": max_blocks,
                    "protected_paths": protected_paths or [],
                    "commands": [
                        {
                            "name": "tests",
                            "argv": [sys.executable, "-c", "print('ok')"],
                            "timeout_seconds": 10,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return script

    def payload(self, root: Path, **overrides: object) -> dict[str, object]:
        value: dict[str, object] = {
            "hook_event_name": "Stop",
            "cwd": str(root),
            "session_id": "session-a",
            "turn_id": "turn-a",
            "model": "fixture-model",
            "permission_mode": "default",
            "stop_hook_active": False,
        }
        value.update(overrides)
        return value

    def test_rejects_invalid_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = self.fixture(root)
            (script.with_name("gate.json")).write_text(
                json.dumps({"schema_version": 2, "max_blocks": 2, "commands": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "schema_version"):
                self.gate.load_config(script)

    def test_passing_commands_allow_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = self.fixture(root)
            payload = self.payload(root)
            result = self.gate.process(payload, script)
            state = json.loads(self.gate.state_path(root.resolve(), payload).read_text())
        self.assertNotIn("decision", result)
        self.assertIn("1/1 checks", result["systemMessage"])
        self.assertEqual(state["model"], "fixture-model")
        self.assertEqual(state["permission_mode"], "default")

    def test_failure_blocks_only_to_configured_budget(self) -> None:
        failed = [
            {
                "name": "tests",
                "argv": ["test"],
                "passed": False,
                "exit_code": 1,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": "assertion failed",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = self.fixture(root, max_blocks=1)
            with mock.patch.object(self.gate, "run_commands", return_value=failed):
                first = self.gate.process(self.payload(root), script)
                exhausted = self.gate.process(
                    self.payload(root, stop_hook_active=True), script
                )
        self.assertEqual(first["decision"], "block")
        self.assertIn("assertion failed", first["reason"])
        self.assertNotIn("decision", exhausted)
        self.assertIn("exhausted", exhausted["systemMessage"])

    def test_missing_turn_id_still_exhausts_one_block_budget(self) -> None:
        failed = [
            {
                "name": "tests",
                "argv": ["test"],
                "passed": False,
                "exit_code": 1,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": "still failing",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = self.fixture(root, max_blocks=1)
            payload = self.payload(root, turn_id=None, stop_hook_active=False)
            with mock.patch.object(self.gate, "run_commands", return_value=failed):
                first = self.gate.process(payload, script)
                exhausted = self.gate.process(payload, script)

        self.assertEqual(first["decision"], "block")
        self.assertNotIn("decision", exhausted)
        self.assertIn("exhausted", exhausted["systemMessage"])

    def test_payload_without_ids_uses_a_deterministic_bounded_fallback(self) -> None:
        failed = [
            {
                "name": "tests",
                "argv": ["test"],
                "passed": False,
                "exit_code": 1,
                "timed_out": False,
                "stdout_tail": "",
                "stderr_tail": "still failing",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = self.fixture(root, max_blocks=1)
            payload = self.payload(
                root, session_id=None, turn_id=None, stop_hook_active=False
            )
            self.assertEqual(
                self.gate.state_path(root, payload), self.gate.state_path(root, payload)
            )
            with mock.patch.object(self.gate, "run_commands", return_value=failed):
                self.gate.process(payload, script)
                exhausted = self.gate.process(payload, script)

        self.assertIn("exhausted", exhausted["systemMessage"])

    def test_timeout_is_returned_as_repair_evidence(self) -> None:
        timeout = [
            {
                "name": "slow-check",
                "argv": ["slow"],
                "passed": False,
                "exit_code": None,
                "timed_out": True,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = self.fixture(root)
            with mock.patch.object(self.gate, "run_commands", return_value=timeout):
                result = self.gate.process(self.payload(root), script)
        self.assertIn("timed_out=True", result["reason"])

    def test_state_is_stable_for_one_session_and_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path_a = self.gate.state_path(root, self.payload(root))
            path_b = self.gate.state_path(
                root, self.payload(root, stop_hook_active=True)
            )
            path_c = self.gate.state_path(root, self.payload(root, turn_id="turn-b"))
        self.assertEqual(path_a, path_b)
        self.assertNotEqual(path_a, path_c)

    @unittest.skipUnless(shutil.which("git"), "Git-backed protected-path integration test")
    def test_changed_protected_path_blocks_even_when_checks_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            protected = root / "public_checks.py"
            protected.write_text("EXPECTED = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "public_checks.py"], cwd=root, check=True)
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
            script = self.fixture(root, protected_paths=["public_checks.py"])
            protected.write_text("EXPECTED = 0\n", encoding="utf-8")
            result = self.gate.process(self.payload(root), script)
        self.assertEqual(result["decision"], "block")
        self.assertIn("protected paths changed", result["reason"])


if __name__ == "__main__":
    unittest.main()
