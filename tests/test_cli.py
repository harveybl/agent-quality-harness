from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "agent_quality_harness.cli", *arguments],
            cwd=cwd,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

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

    def test_install_defaults_to_current_repository_and_both_clients(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "sample project"
            subprocess.run(["git", "init", "-q", root], check=True)

            process = self.run_cli("install", cwd=root)

            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("Claude Code and Codex", process.stdout)
            self.assertTrue((root / ".claude/settings.json").is_file())
            self.assertTrue((root / ".codex/hooks.json").is_file())

    def test_install_accepts_a_single_client_and_custom_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", root], check=True)
            gate = root / "custom gate.json"
            gate.write_text(
                '{"schema_version":1,"commands":[],"protected_paths":[],"max_blocks":2}',
                encoding="utf-8",
            )

            process = self.run_cli(
                "install", "--tool", "claude", "--gate", str(gate), cwd=root
            )

            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertTrue((root / ".claude/settings.json").is_file())
            self.assertFalse((root / ".codex/hooks.json").exists())

    def test_uninstall_restores_the_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", root], check=True)
            self.assertEqual(self.run_cli("install", cwd=root).returncode, 0)

            process = self.run_cli("uninstall", cwd=root)

            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("Restored", process.stdout)
            self.assertFalse((root / ".agent-quality").exists())

    def test_uninstall_force_is_an_explicit_option(self) -> None:
        parser = __import__(
            "agent_quality_harness.cli", fromlist=["build_parser"]
        ).build_parser()

        args = parser.parse_args(["uninstall", "--force"])

        self.assertTrue(args.force)

    def test_install_update_is_an_explicit_option(self) -> None:
        parser = __import__(
            "agent_quality_harness.cli", fromlist=["build_parser"]
        ).build_parser()

        args = parser.parse_args(["install", "--update"])

        self.assertTrue(args.update)


if __name__ == "__main__":
    unittest.main()
