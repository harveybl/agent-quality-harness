from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_public_entry_points_exist(self) -> None:
        for relative in ("README.md", "docs", "local", "frontier", "evaluator"):
            self.assertTrue((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()

