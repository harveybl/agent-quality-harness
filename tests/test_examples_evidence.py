from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ExampleEvidenceTests(unittest.TestCase):
    def test_hello_fix_starter_has_one_real_failing_public_contract(self) -> None:
        example = ROOT / "examples/hello-fix"
        contract = json.loads((example / "contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["max_continuations"], 1)
        self.assertEqual(contract["mutable_paths"], ["starter"])
        process = subprocess.run(
            contract["public_check_argv"], cwd=example, text=True, capture_output=True, check=False
        )
        self.assertEqual(process.returncode, 1)
        self.assertIn("FAILED", process.stderr + process.stdout)

    def test_qwen_ledger_is_compact_and_has_required_measurements(self) -> None:
        path = ROOT / "evidence/2026-09-01-qwen-q8/ledger.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        required = {
            "schema_version",
            "date",
            "task",
            "model",
            "quantization",
            "model_artifact_sha256",
            "task_pass",
            "controller_score",
            "corrected_public_score",
            "elapsed_seconds",
            "model_calls",
            "human_intervention",
            "continuations",
            "automatic_run_retries",
            "terminal_reason",
            "limitations",
        }
        self.assertEqual(set(value), required)
        self.assertTrue(value["task_pass"])
        self.assertEqual(value["model_calls"]["total"], 47)
        self.assertEqual(value["automatic_run_retries"], 0)

    def test_public_evidence_contains_no_local_identity_or_private_paths(self) -> None:
        evidence = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "evidence").rglob("*")
            if path.is_file()
        )
        for blocked in ("/Users/", "/home/", "192.168.", "Development-Projects"):
            self.assertNotIn(blocked, evidence)


if __name__ == "__main__":
    unittest.main()

