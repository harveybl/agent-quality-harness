from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from local.harness.file_tools import FileTools, ToolPolicyError


class FileToolsTests(unittest.TestCase):
    def tools(self, root: Path, *, budget: int = 5) -> FileTools:
        (root / "starter").mkdir(exist_ok=True)
        (root / "public_checks").mkdir(exist_ok=True)
        return FileTools(
            root,
            mutable_paths=["starter"],
            protected_paths=["public_checks", "contract.json"],
            public_check_argv=[sys.executable, "-c", "print('ok')"],
            navigation_budget=budget,
        )

    def test_read_and_write_stay_in_exact_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = self.tools(root)
            tools.write_file("starter/a.py", "VALUE = 1\n")
            self.assertEqual(tools.read_file("starter/a.py"), "VALUE = 1\n")
            with self.assertRaisesRegex(ToolPolicyError, "mutable allowlist"):
                tools.write_file("other.py", "VALUE = 2\n")
            with self.assertRaisesRegex(ToolPolicyError, "protected"):
                tools.write_file("public_checks/test_a.py", "pass\n")

    def test_rejects_escape_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = self.tools(root)
            outside = root.parent / "outside-agent-quality.txt"
            outside.write_text("secret", encoding="utf-8")
            try:
                (root / "starter/link").symlink_to(outside)
                with self.assertRaisesRegex(ToolPolicyError, "symlink"):
                    tools.read_file("starter/link")
                with self.assertRaisesRegex(ToolPolicyError, "workspace"):
                    tools.read_file("../outside-agent-quality.txt")
            finally:
                outside.unlink(missing_ok=True)

    def test_navigation_budget_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = self.tools(root, budget=1)
            (root / "starter/a.txt").write_text("needle", encoding="utf-8")
            tools.list_files("starter")
            with self.assertRaisesRegex(ToolPolicyError, "navigation budget"):
                tools.search_text("needle", "starter")
            tools.reset_navigation_budget()
            self.assertEqual(tools.search_text("needle", "starter"), ["starter/a.txt:1:needle"])

    def test_python_syntax_is_checked_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tools = self.tools(Path(temporary))
            with self.assertRaisesRegex(ToolPolicyError, "Python syntax"):
                tools.write_file("starter/a.py", "def broken(:\n")
            self.assertFalse((Path(temporary) / "starter/a.py").exists())

    def test_public_checks_are_denied_before_first_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tools = self.tools(Path(temporary))
            with self.assertRaisesRegex(ToolPolicyError, "first accepted write"):
                tools.run_public_tests()
            tools.write_file("starter/a.py", "VALUE = 1\n")
            result = tools.run_public_tests()
            self.assertTrue(result["passed"])

    def test_replace_requires_exact_line_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = self.tools(root)
            (root / "starter/a.py").write_text(
                "def add(a, b):\n    return 0\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ToolPolicyError, "anchor"):
                tools.replace_text(
                    "starter/a.py", "return 0", "return a + b", line=1, anchor="return 0"
                )
            tools.replace_text(
                "starter/a.py", "return 0", "return a + b", line=2, anchor="return 0"
            )
            self.assertIn("a + b", (root / "starter/a.py").read_text())


if __name__ == "__main__":
    unittest.main()
