from __future__ import annotations

from pathlib import Path
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
            self.assertIn('pip install "agent-quality-harness[local]"', text)
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


if __name__ == "__main__":
    unittest.main()
