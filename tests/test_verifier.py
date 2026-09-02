from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_quality_harness import installer, verifier


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


class VerifierTests(unittest.TestCase):
    def test_verify_proves_hooks_pass_bound_fail_and_leave_target_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "target with spaces"
            root.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "application.txt").write_text("do not change\n", encoding="utf-8")
            installer.install(root)
            before = snapshot(root)

            result = verifier.verify(root)

            self.assertEqual(snapshot(root), before)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(
            result["checks"],
            {
                "hook_shape": "pass",
                "session_start": "pass",
                "passing_stop": "pass",
                "bounded_failure": "pass",
                "target_immutable": "pass",
            },
        )


if __name__ == "__main__":
    unittest.main()
