from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from frontier.scripts import install_hooks, uninstall_hooks


class HookInstallerTests(unittest.TestCase):
    def repo(self, root: Path) -> Path:
        subprocess.run(["git", "init", "-q", root], check=True)
        return root

    def test_refuses_target_outside_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Git repository"):
                install_hooks.install(Path(temporary), ["claude"])

    def test_fresh_install_adds_both_native_hooks_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.repo(Path(temporary))
            manifest = install_hooks.install(root, ["claude", "codex"])
            claude = json.loads((root / ".claude/settings.json").read_text())
            codex = json.loads((root / ".codex/hooks.json").read_text())
            self.assertEqual(len(claude["hooks"]["Stop"]), 1)
            self.assertEqual(len(codex["hooks"]["Stop"]), 1)
            self.assertTrue((root / ".agent-quality/completion_gate.py").is_file())
            self.assertTrue((root / ".agent-quality/gate.json").is_file())
            self.assertEqual(manifest["schema_version"], 1)
            self.assertTrue((root / ".agent-quality/install-manifest.json").is_file())

    def test_preserves_unrelated_hooks_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.repo(Path(temporary))
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_text(
                json.dumps(
                    {
                        "permissions": {"allow": ["Read"]},
                        "hooks": {
                            "Stop": [
                                {
                                    "hooks": [
                                        {"type": "command", "command": "echo existing"}
                                    ]
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            install_hooks.install(root, ["claude"])
            first = settings.read_bytes()
            install_hooks.install(root, ["claude"])
            value = json.loads(settings.read_text())
            self.assertEqual(settings.read_bytes(), first)
            self.assertEqual(value["permissions"]["allow"], ["Read"])
            self.assertEqual(len(value["hooks"]["Stop"]), 2)

    def test_existing_files_get_timestamped_backups_and_exact_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.repo(Path(temporary))
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            original = b'{"custom":true,"hooks":{}}\n'
            settings.write_bytes(original)
            manifest = install_hooks.install(root, ["claude"])
            backup = root / manifest["files"][".claude/settings.json"]["backup"]
            self.assertTrue(backup.is_file())
            self.assertEqual(backup.read_bytes(), original)
            uninstall_hooks.uninstall(root)
            self.assertEqual(settings.read_bytes(), original)
            self.assertFalse((root / ".agent-quality/install-manifest.json").exists())

    def test_uninstall_removes_only_files_created_by_installer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.repo(Path(temporary))
            keep = root / ".claude/keep.txt"
            keep.parent.mkdir()
            keep.write_text("keep", encoding="utf-8")
            install_hooks.install(root, ["claude"])
            uninstall_hooks.uninstall(root)
            self.assertEqual(keep.read_text(), "keep")
            self.assertFalse((root / ".claude/settings.json").exists())

    def test_malformed_json_is_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.repo(Path(temporary))
            settings = root / ".claude/settings.json"
            settings.parent.mkdir()
            settings.write_bytes(b"{not-json\n")
            with self.assertRaisesRegex(ValueError, "valid JSON"):
                install_hooks.install(root, ["claude"])
            self.assertEqual(settings.read_bytes(), b"{not-json\n")
            self.assertFalse((root / ".agent-quality").exists())

    def test_uninstall_refuses_managed_file_changed_after_install(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.repo(Path(temporary))
            install_hooks.install(root, ["claude"])
            (root / ".claude/settings.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "changed after installation"):
                uninstall_hooks.uninstall(root)
            uninstall_hooks.uninstall(root, force=True)

    def test_installed_gate_blocks_then_passes_a_synthetic_stop_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self.repo(Path(temporary))
            test_file = root / "test_fixture.py"
            test_file.write_text(
                "import unittest\nclass T(unittest.TestCase):\n"
                "    def test_value(self): self.assertEqual(1, 2)\n",
                encoding="utf-8",
            )
            gate = {
                "schema_version": 1,
                "max_blocks": 1,
                "protected_paths": [],
                "commands": [
                    {
                        "name": "fixture",
                        "argv": [sys.executable, "-m", "unittest", "test_fixture.py"],
                        "timeout_seconds": 30,
                    }
                ],
            }
            gate_source = root / "fixture-gate.json"
            gate_source.write_text(json.dumps(gate), encoding="utf-8")
            install_hooks.install(root, ["claude"], gate_source=gate_source)
            payload = {
                "hook_event_name": "Stop",
                "cwd": str(root),
                "session_id": "s",
                "turn_id": "t",
                "stop_hook_active": False,
            }
            command = [sys.executable, str(root / ".agent-quality/completion_gate.py")]
            failed = subprocess.run(
                command,
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(json.loads(failed.stdout)["decision"], "block")
            test_file.write_text(
                "import unittest\nclass T(unittest.TestCase):\n"
                "    def test_value(self): self.assertTrue(True)\n",
                encoding="utf-8",
            )
            passed = subprocess.run(
                command,
                input=json.dumps({**payload, "stop_hook_active": True}),
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("passed", json.loads(passed.stdout)["systemMessage"])


if __name__ == "__main__":
    unittest.main()
