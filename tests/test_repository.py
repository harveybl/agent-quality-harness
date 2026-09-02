from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_public_entry_points_exist(self) -> None:
        for relative in ("README.md", "docs", "local", "frontier", "evaluator"):
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_ci_covers_three_desktop_platforms_and_keeps_gpu_optional(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        for runner in ("ubuntu-latest", "macos-latest", "windows-latest"):
            self.assertIn(runner, workflow)
        self.assertIn("python -m build", workflow)
        self.assertIn("test_avo_*.py", workflow)
        self.assertIn("docker compose -f local/docker-compose.yml config --quiet", workflow)
        self.assertNotIn("--gpus", workflow)
        self.assertNotIn("smoke.sh", workflow)

    def test_legacy_duplicate_hook_resources_are_removed(self) -> None:
        for relative in (
            "frontier/AGENTS.md",
            "frontier/CLAUDE.md",
            "frontier/hooks/claude/settings.fragment.json",
            "frontier/hooks/codex/hooks.fragment.json",
        ):
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()
