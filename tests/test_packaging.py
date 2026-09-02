from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_release_version_is_final_and_matches_runtime(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        runtime = (ROOT / "src/agent_quality_harness/__init__.py").read_text(
            encoding="utf-8"
        )

        self.assertEqual(config["project"]["version"], "0.2.0")
        self.assertIn('__version__ = "0.2.0"', runtime)
        self.assertNotIn("dev", config["project"]["version"])

    def test_missing_extra_guidance_does_not_point_to_unpublished_pypi_name(self) -> None:
        for path in (
            ROOT / "src/agent_quality_harness/experiments/providers.py",
            ROOT / "src/agent_quality_harness/experiments/supervisor.py",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("pip install 'agent-quality-harness", text)
            self.assertIn("pinned release", text)

    def test_base_is_dependency_free_and_local_extra_is_exactly_pinned(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(config["project"]["dependencies"], [])
        self.assertEqual(
            config["project"]["optional-dependencies"]["local"],
            [
                "strands-agents[openai]==1.54.0",
                "openai==2.54.0",
                "pydantic==2.13.5",
            ],
        )

    def test_local_harness_is_explicitly_mapped_into_the_wheel(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        package_dirs = config["tool"]["setuptools"]["package-dir"]
        self.assertEqual(
            package_dirs["agent_quality_harness.local_harness"], "local/harness"
        )
        for module in ("contracts.py", "controller.py", "file_tools.py", "ledger.py", "worker.py"):
            self.assertTrue((ROOT / "local/harness" / module).is_file(), module)

    def test_experiment_extra_contains_only_supervisor_dependencies(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(
            config["project"]["optional-dependencies"]["experiment"],
            ["strands-agents==1.54.0", "pydantic==2.13.5"],
        )


if __name__ == "__main__":
    unittest.main()
