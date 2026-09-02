from __future__ import annotations

from pathlib import Path
import re
import unittest

from scripts.lint_steps import lint_repository


ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_runbook_steps_have_complete_operational_fields_in_order(self) -> None:
        errors = lint_repository(ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_local_quickstart_is_endpoint_first_and_container_optional(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        runbook = (ROOT / "docs/local-deploy.md").read_text(encoding="utf-8")
        how = (ROOT / "docs/how-it-works.md").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        for text in (readme, runbook):
            self.assertIn('pip install \\', text)
            self.assertIn('"agent-quality-harness[local] @ https://github.com/', text)
            self.assertIn("aqh local doctor", text)
            self.assertIn("aqh local run", text)
        self.assertLessEqual(runbook.count("## Step "), 4)
        self.assertIn("AQH does not start or stop", runbook)
        self.assertIn("user-supplied endpoint", runbook)
        self.assertIn("native process bounds", runbook)
        self.assertIn("Optional NVIDIA/Docker reproducibility", runbook)
        self.assertIn("existing endpoint", how)
        self.assertIn("not container isolation", security)

    def test_frontier_runbook_separates_synthetic_and_product_native_checks(self) -> None:
        text = (ROOT / "docs/frontier-deploy.md").read_text(encoding="utf-8")
        self.assertIn("Synthetic verification", text)
        self.assertIn("Product-native verification", text)
        self.assertIn("/hooks", text)
        self.assertIn("claude", text)
        self.assertIn("codex", text)
        self.assertIn("aqh install", text)
        self.assertIn("aqh uninstall", text)
        self.assertNotIn("frontier/scripts/install_hooks.py", text)

    def test_avo_is_explicitly_experimental_bounded_and_cli_only(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        runbook = (ROOT / "docs/avo-experiment.md").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        combined = "\n".join((readme, runbook, security)).lower()
        for phrase in (
            "experimental",
            "cli-only",
            "completion gate",
            "both personal subscriptions",
            "no external paid routes",
            "max-review-calls",
            "max-repair-turns",
            "one hard-task observation",
            "not a broad benchmark",
            "desktop is not qualified",
        ):
            self.assertIn(phrase, combined)
        self.assertIn('"agent-quality-harness[experiment] @ https://github.com/', runbook)
        self.assertIn("automatic full-run retries", runbook.lower())
        self.assertIn("danger-full-access", runbook)
        self.assertIn("disposable worktree", runbook)
        self.assertIn("machine-local absolute", combined)

    def test_install_commands_use_the_pinned_github_release_not_pypi(self) -> None:
        sources = [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "docs/frontier-deploy.md").read_text(encoding="utf-8"),
            (ROOT / "docs/local-deploy.md").read_text(encoding="utf-8"),
            (ROOT / "docs/avo-experiment.md").read_text(encoding="utf-8"),
        ]
        wheel = (
            "https://github.com/harveybl/agent-quality-harness/releases/download/"
            "v0.2.0/agent_quality_harness-0.2.0-py3-none-any.whl"
        )
        for text in sources:
            self.assertIn(wheel, text)
        self.assertIn("not PyPI", sources[1])
        self.assertIn("not on PyPI", sources[2])

    def test_current_evidence_leads_with_the_qualified_matrix(self) -> None:
        text = (ROOT / "docs/evidence.md").read_text(encoding="utf-8")
        self.assertIn("native hooks", text)
        self.assertIn("3/5 to 5/5", text)
        self.assertIn("Qwen hit the endpoint's 32K context", text)
        self.assertIn("Muse reached its generation ceiling", text)
        self.assertIn("2026-09-02-inventory-matrix/summary.md", text)

    def test_all_repository_relative_markdown_links_exist(self) -> None:
        missing: list[str] = []
        for source in (ROOT / "README.md", *(ROOT / "docs").glob("*.md")):
            text = source.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#") or target.startswith("mailto:"):
                    continue
                relative = target.split("#", 1)[0]
                if relative and not (source.parent / relative).resolve().exists():
                    missing.append(f"{source.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
