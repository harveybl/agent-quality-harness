from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_help_lists_every_public_command(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        process = subprocess.run(
            [sys.executable, "-m", "agent_quality_harness.cli", "--help"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        for command in (
            "install",
            "doctor",
            "verify",
            "uninstall",
            "local",
            "experiment",
        ):
            self.assertIn(command, process.stdout)


if __name__ == "__main__":
    unittest.main()
