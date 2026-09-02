from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from agent_quality_harness import installer
from agent_quality_harness import uninstaller


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project with spaces"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_default_install_adds_both_clients_and_all_resources(self) -> None:
        manifest = installer.install(self.root)

        self.assertEqual(manifest["tools"], ["claude", "codex"])
        self.assertEqual(manifest["state"], "complete")
        for relative in (
            ".agent-quality/completion_gate.py",
            ".agent-quality/quality_context.py",
            ".agent-quality/quality_contract.txt",
            ".agent-quality/gate.json",
            ".agent-quality/install-manifest.json",
            ".claude/settings.json",
            ".codex/hooks.json",
        ):
            self.assertTrue((self.root / relative).is_file(), relative)
        for relative in (".claude/settings.json", ".codex/hooks.json"):
            value = json.loads((self.root / relative).read_text(encoding="utf-8"))
            self.assertEqual(set(value["hooks"]), {"SessionStart", "Stop"})
        gate = json.loads((self.root / ".agent-quality/gate.json").read_text())
        self.assertEqual(gate["commands"][0]["argv"], ["git", "diff", "--check"])

    def test_narrow_install_preserves_unrelated_configuration(self) -> None:
        settings = self.root / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_text(
            json.dumps(
                {
                    "permissions": {"allow": ["Read"]},
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}]},
                }
            ),
            encoding="utf-8",
        )

        installer.install(self.root, tool="claude")

        value = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(value["permissions"]["allow"], ["Read"])
        self.assertEqual(len(value["hooks"]["Stop"]), 2)
        self.assertFalse((self.root / ".codex/hooks.json").exists())

    def test_same_input_install_is_idempotent(self) -> None:
        first_manifest = installer.install(self.root)
        first = snapshot(self.root)

        second_manifest = installer.install(self.root)

        self.assertEqual(second_manifest, first_manifest)
        self.assertEqual(snapshot(self.root), first)

    def test_malformed_json_is_rejected_without_mutation(self) -> None:
        settings = self.root / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_bytes(b"{not-json\n")
        before = snapshot(self.root)

        with self.assertRaisesRegex(ValueError, "valid JSON"):
            installer.install(self.root)

        self.assertEqual(snapshot(self.root), before)

    def test_hook_commands_support_repository_paths_with_spaces(self) -> None:
        installer.install(self.root)
        value = json.loads((self.root / ".codex/hooks.json").read_text())
        encoded = json.dumps(value)
        self.assertIn(str(self.root), encoded)
        self.assertNotIn("$(", encoded)

    def test_failure_during_second_client_write_restores_entire_tree(self) -> None:
        keep = self.root / ".claude/settings.json"
        keep.parent.mkdir()
        keep.write_bytes(b'{"custom":true}\n')
        before = snapshot(self.root)
        real_atomic_write = installer._atomic_write

        def fail_on_codex(path: Path, content: bytes) -> None:
            if path == self.root / ".codex/hooks.json":
                raise OSError("simulated disk failure")
            real_atomic_write(path, content)

        with mock.patch.object(installer, "_atomic_write", side_effect=fail_on_codex):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                installer.install(self.root)

        self.assertEqual(snapshot(self.root), before)

    def test_uninstall_restores_original_bytes(self) -> None:
        settings = self.root / ".claude/settings.json"
        settings.parent.mkdir()
        original = b'{"custom":true,"hooks":{}}\n'
        settings.write_bytes(original)
        installer.install(self.root)

        uninstaller.uninstall(self.root)

        self.assertEqual(settings.read_bytes(), original)
        self.assertFalse((self.root / ".codex/hooks.json").exists())
        self.assertFalse((self.root / ".agent-quality").exists())
        self.assertFalse((self.root / ".agent-quality-backups").exists())

    def test_uninstall_refuses_later_user_edit_without_force(self) -> None:
        installer.install(self.root)
        settings = self.root / ".claude/settings.json"
        settings.write_bytes(b'{"later":"user edit"}\n')

        with self.assertRaisesRegex(RuntimeError, "changed after installation"):
            uninstaller.uninstall(self.root)

        self.assertEqual(settings.read_bytes(), b'{"later":"user edit"}\n')
        self.assertTrue((self.root / ".agent-quality/install-manifest.json").exists())

    def test_force_uninstall_explicitly_restores_over_a_later_edit(self) -> None:
        settings = self.root / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_bytes(b'{"original":true}\n')
        installer.install(self.root)
        settings.write_bytes(b'{"later":"user edit"}\n')

        uninstaller.uninstall(self.root, force=True)

        self.assertEqual(settings.read_bytes(), b'{"original":true}\n')

    def test_different_install_requires_explicit_update(self) -> None:
        installer.install(self.root)

        with self.assertRaisesRegex(RuntimeError, "--update"):
            installer.install(self.root, tool="claude")

    def test_explicit_update_changes_client_selection(self) -> None:
        installer.install(self.root)

        manifest = installer.install(self.root, tool="claude", update=True)

        self.assertEqual(manifest["tools"], ["claude"])
        self.assertTrue((self.root / ".claude/settings.json").is_file())
        self.assertFalse((self.root / ".codex/hooks.json").exists())

    def test_failed_explicit_update_restores_the_previous_install(self) -> None:
        first_manifest = installer.install(self.root)
        before = snapshot(self.root)
        real_atomic_write = installer._atomic_write

        def fail_on_new_claude(path: Path, content: bytes) -> None:
            if path == self.root / ".claude/settings.json":
                raise OSError("simulated update failure")
            real_atomic_write(path, content)

        with mock.patch.object(installer, "_atomic_write", side_effect=fail_on_new_claude):
            with self.assertRaisesRegex(OSError, "simulated update failure"):
                installer.install(self.root, tool="claude", update=True)

        self.assertEqual(snapshot(self.root), before)
        current = json.loads(
            (self.root / ".agent-quality/install-manifest.json").read_text()
        )
        self.assertEqual(current, first_manifest)


if __name__ == "__main__":
    unittest.main()
