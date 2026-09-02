from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class RuntimeFileTests(unittest.TestCase):
    def test_compose_pins_images_and_keeps_model_on_loopback(self) -> None:
        compose = (ROOT / "local/docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("ghcr.io/ggml-org/llama.cpp@sha256:", compose)
        self.assertIn('127.0.0.1:${MODEL_PORT:-8080}:8080', compose)
        self.assertIn("internal: true", compose)
        self.assertIn(":/models:ro", compose)

    def test_sandbox_is_non_root_read_only_and_has_no_docker_socket(self) -> None:
        compose = (ROOT / "local/docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('user: "65532:65532"', compose)
        self.assertGreaterEqual(compose.count("read_only: true"), 2)
        self.assertIn("no-new-privileges:true", compose)
        self.assertIn("cap_drop:", compose)
        self.assertIn("- ALL", compose)
        self.assertIn("pids_limit:", compose)
        self.assertNotIn("/var/run/docker.sock", compose)

    def test_sandbox_base_and_python_dependencies_are_exactly_pinned(self) -> None:
        dockerfile = (ROOT / "local/Dockerfile.sandbox").read_text(encoding="utf-8")
        self.assertRegex(dockerfile.splitlines()[0], r"^FROM python:.*@sha256:[0-9a-f]{64}$")
        requirements = (ROOT / "local/requirements.lock").read_text(encoding="utf-8")
        for line in requirements.splitlines():
            if line.strip():
                self.assertIn("==", line)
        openai_pin = next(line for line in requirements.splitlines() if line.startswith("openai=="))
        self.assertRegex(openai_pin, r"^openai==2\.", "Strands 1.54 requires OpenAI Python <3")

    def test_model_lock_names_tested_qwen_hash_without_private_location(self) -> None:
        lock = json.loads((ROOT / "local/models.lock.example").read_text(encoding="utf-8"))
        model = lock["models"][0]
        self.assertEqual(model["sha256"], "a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348")
        self.assertEqual(model["size_bytes"], 29047086048)
        self.assertNotIn("/Users/", json.dumps(lock))

    def test_generated_and_sensitive_runtime_paths_are_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for value in ("models/", "runs/", ".env", "local/config.json"):
            self.assertIn(value, ignored)

    def test_local_streaming_requests_usage_metrics(self) -> None:
        worker = (ROOT / "local/harness/worker.py").read_text(encoding="utf-8")
        self.assertIn('"stream_options": {"include_usage": True}', worker)

    def test_planner_gets_bounded_read_only_tools(self) -> None:
        worker = (ROOT / "local/harness/worker.py").read_text(encoding="utf-8")
        self.assertIn("tools=self._plan_tools(tools)", worker)
        plan_tools = worker.split("def _plan_tools", 1)[1].split(
            "def _agent_tools", 1
        )[0]
        self.assertIn("def read_file", plan_tools)
        self.assertNotIn("def replace_text", plan_tools)
        self.assertNotIn("def write_file", plan_tools)
        implementation_tools = worker.split("def _agent_tools", 1)[1].split(
            "def implement", 1
        )[0]
        self.assertIn("def replace_text", implementation_tools)
        self.assertIn("def write_file", implementation_tools)
        controller = (ROOT / "local/harness/controller.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(controller.count("tools.reset_navigation_budget()"), 2)


if __name__ == "__main__":
    unittest.main()
