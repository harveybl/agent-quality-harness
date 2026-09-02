from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from local.harness.contracts import Plan, PlanChange, validate_anchor


class ContractTests(unittest.TestCase):
    def test_plan_requires_native_object_with_acceptance_ids(self) -> None:
        value = {
            "changes": [
                {
                    "path": "starter/calculator.py",
                    "line": 3,
                    "anchor": "def add",
                    "change": "return the sum",
                    "acceptance_ids": ["AC-1"],
                }
            ]
        }
        plan = Plan.from_object(value)
        self.assertEqual(plan.changes[0].path, "starter/calculator.py")

    def test_plan_rejects_markdown_or_missing_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "JSON object"):
            Plan.from_object("```json\n{}\n```")
        with self.assertRaisesRegex(ValueError, "exactly"):
            PlanChange.from_object({"path": "a.py"})

    def test_anchor_must_match_exact_declared_line(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "a.py"
            path.write_text("one\ndef add(a, b):\n    return 0\n", encoding="utf-8")
            validate_anchor(path, 2, "def add")
            with self.assertRaisesRegex(ValueError, "anchor"):
                validate_anchor(path, 1, "def add")


if __name__ == "__main__":
    unittest.main()

