from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from agent_quality_harness import doctor, installer


class DoctorTests(unittest.TestCase):
    def test_reports_install_health_minimum_gate_and_latest_native_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            gate = root / "failing-gate.json"
            gate.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "max_blocks": 2,
                        "protected_paths": [],
                        "commands": [
                            {
                                "name": "fixture",
                                "argv": [sys.executable, "-c", "raise SystemExit(1)"],
                                "timeout_seconds": 10,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            installer.install(root, tool="claude", gate_source=gate)
            script = root / ".agent-quality/completion_gate.py"
            payload = {
                "hook_event_name": "Stop",
                "cwd": str(root),
                "session_id": "doctor-session",
                "turn_id": "doctor-turn",
                "model": "claude-sonnet-test",
                "permission_mode": "default",
                "stop_hook_active": False,
            }
            subprocess.run(
                [sys.executable, str(script)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
            )

            result = doctor.diagnose(root)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["tools"], ["claude"])
        self.assertEqual(result["gate_kind"], "custom")
        self.assertEqual(result["latest_evidence"]["outcome"], "blocked-for-repair")
        self.assertEqual(result["latest_evidence"]["blocks"], 1)
        self.assertEqual(result["latest_evidence"]["check_count"], 1)
        self.assertEqual(result["latest_evidence"]["model"], "claude-sonnet-test")

    def test_default_gate_is_identified_as_minimum_safety_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            installer.install(root)

            result = doctor.diagnose(root)

        self.assertEqual(result["gate_kind"], "minimum")
        self.assertIn("project-specific", result["recommendation"])

    def test_moved_repository_reports_stale_absolute_hook_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "original"
            root.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            installer.install(root)
            moved = parent / "moved"
            root.rename(moved)

            result = doctor.diagnose(moved)

        self.assertEqual(result["status"], "repair-needed")
        self.assertTrue(any("path" in issue for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
