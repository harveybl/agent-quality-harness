from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from agent_quality_harness.hooks import build_hooks, resource_bytes


class HookTests(unittest.TestCase):
    def test_hooks_use_absolute_paths_without_shell_substitution(self) -> None:
        interpreter = Path("/opt/Python Runtime/bin/python")
        target = Path("/tmp/project with spaces")

        hooks = build_hooks(interpreter, target, platform="posix")

        encoded = json.dumps(hooks)
        self.assertIn("SessionStart", hooks["hooks"])
        self.assertIn("Stop", hooks["hooks"])
        self.assertNotIn("$(", encoded)
        self.assertNotIn("python3", encoded)
        self.assertIn(str(target / ".agent-quality/completion_gate.py"), encoded)
        self.assertIn(str(target / ".agent-quality/quality_context.py"), encoded)

    def test_windows_hook_command_uses_windows_quoting(self) -> None:
        hooks = build_hooks(
            Path(r"C:\Program Files\Python\python.exe"),
            Path(r"C:\work tree\project"),
            platform="windows",
        )
        encoded = json.dumps(hooks)
        self.assertIn(r"C:\\Program Files\\Python\\python.exe", encoded)
        self.assertNotIn("$(", encoded)

    def test_quality_context_returns_the_packaged_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "quality_context.py"
            contract = root / "quality_contract.txt"
            script.write_bytes(resource_bytes("quality_context.py"))
            contract.write_bytes(resource_bytes("quality_contract.txt"))
            process = subprocess.run(
                [sys.executable, str(script)],
                input=json.dumps({"hook_event_name": "SessionStart"}),
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(process.returncode, 0, process.stderr)
        value = json.loads(process.stdout)
        output = value["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("short implementation plan", output["additionalContext"])
        self.assertIn("protected paths", output["additionalContext"])


if __name__ == "__main__":
    unittest.main()
