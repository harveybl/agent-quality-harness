from __future__ import annotations

from pathlib import Path
import unittest

from scripts.lint_steps import lint_repository


ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_runbook_steps_have_complete_operational_fields_in_order(self) -> None:
        errors = lint_repository(ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_local_runbook_has_all_eleven_deployment_stages(self) -> None:
        text = (ROOT / "docs/local-deploy.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("## Step "), 11)

    def test_frontier_runbook_separates_synthetic_and_product_native_checks(self) -> None:
        text = (ROOT / "docs/frontier-deploy.md").read_text(encoding="utf-8")
        self.assertIn("Synthetic verification", text)
        self.assertIn("Product-native verification", text)
        self.assertIn("/hooks", text)
        self.assertIn("claude", text)
        self.assertIn("codex", text)


if __name__ == "__main__":
    unittest.main()

