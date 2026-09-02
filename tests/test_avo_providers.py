from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from uuid import UUID

from agent_quality_harness.experiments.providers import (
    ClaudeProvider,
    CodexProvider,
    _validate_environment,
    claude_supervisor_argv,
)


FORBIDDEN = {
    "--api-key",
    "--base-url",
    "--fallback-model",
    "--bare",
    "--safe-mode",
    "--ignore-user-config",
    "--dangerously-bypass-approvals-and-sandbox",
    "--max-budget-usd",
}


class AvoProviderTests(unittest.TestCase):
    def test_claude_supervisor_is_toolless_without_replacing_normal_auth_settings(self) -> None:
        argv = claude_supervisor_argv(
            model="fable",
            effort="high",
            schema={"type": "object"},
            system_prompt="Return a directive.",
        )

        self.assertEqual(argv[0], "claude")
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertIn("--json-schema", argv)
        self.assertEqual(FORBIDDEN.intersection(argv), set())
        self.assertNotIn("--setting-sources", argv)

    def test_paid_or_external_route_environment_is_rejected(self) -> None:
        for key in (
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_BASE_URL",
            "OPENAI_BASE_URL",
            "CLAUDE_CODE_USE_BEDROCK",
        ):
            with self.subTest(key=key):
                with self.assertRaisesRegex(RuntimeError, key):
                    _validate_environment({key: "configured"})

    def test_claude_uses_normal_native_environment_and_exact_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ClaudeProvider(model="claude-fable-5-1", effort="high")

            start = provider.start(root, "Implement the task")
            resumed = provider.resume(root, "Repair this failure", start.session_id)

        self.assertEqual(start.argv[0], "claude")
        self.assertEqual(UUID(start.session_id).version, 4)
        self.assertIn("--print", start.argv)
        self.assertIn("stream-json", start.argv)
        self.assertIn("--session-id", start.argv)
        self.assertIn("--resume", resumed.argv)
        self.assertIn(start.session_id, resumed.argv)
        self.assertEqual(FORBIDDEN.intersection(start.argv), set())
        self.assertNotIn("Implement the task", start.argv)
        self.assertEqual(start.stdin, "Implement the task")

    def test_codex_uses_normal_exec_json_and_exact_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = CodexProvider(model="gpt-5.6-sol", effort="high")

            start = provider.start(root, "Implement the task")
            resumed = provider.resume(root, "Repair this failure", "thread-123")

        self.assertEqual(start.argv[:2], ("codex", "exec"))
        self.assertIn("--json", start.argv)
        self.assertIn("--cd", start.argv)
        self.assertEqual(start.argv[start.argv.index("--sandbox") + 1], "danger-full-access")
        self.assertIn('model_reasoning_effort="high"', start.argv)
        self.assertIn("resume", resumed.argv)
        self.assertIn("thread-123", resumed.argv)
        self.assertEqual(FORBIDDEN.intersection(start.argv), set())
        self.assertNotIn("Implement the task", start.argv)
        self.assertEqual(start.stdin, "Implement the task")

    def test_claude_parses_identity_usage_elapsed_and_final_result(self) -> None:
        session = "12345678-1234-4678-9234-567812345678"
        output = "\n".join(
            (
                json.dumps(
                    {
                        "type": "system",
                        "session_id": session,
                        "model": "claude-fable-5-1",
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "session_id": session,
                        "model": "claude-fable-5-1",
                        "result": "completed change",
                        "num_turns": 3,
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 25,
                            "cache_read_input_tokens": 40,
                        },
                    }
                ),
            )
        )

        receipt = ClaudeProvider("claude-fable-5-1", "high").parse(
            output, elapsed_seconds=4.5, exit_code=0, requested_session_id=session
        )

        self.assertEqual(receipt.client, "claude")
        self.assertEqual(receipt.model, "claude-fable-5-1")
        self.assertEqual(receipt.session_id, session)
        self.assertEqual(receipt.input_tokens, 100)
        self.assertEqual(receipt.output_tokens, 25)
        self.assertEqual(receipt.cached_input_tokens, 40)
        self.assertEqual(receipt.elapsed_seconds, 4.5)
        self.assertEqual(receipt.final_output, "completed change")

    def test_codex_parses_identity_usage_elapsed_and_final_result(self) -> None:
        output = "\n".join(
            (
                json.dumps(
                    {
                        "type": "thread.started",
                        "thread_id": "thread-123",
                        "model": "gpt-5.6-sol",
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "id": "message-1",
                            "type": "agent_message",
                            "text": "completed change",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 90,
                            "cached_input_tokens": 30,
                            "output_tokens": 20,
                        },
                    }
                ),
            )
        )

        receipt = CodexProvider("gpt-5.6-sol", "high").parse(
            output, elapsed_seconds=3.25, exit_code=0
        )

        self.assertEqual(receipt.client, "codex")
        self.assertEqual(receipt.model, "gpt-5.6-sol")
        self.assertEqual(receipt.session_id, "thread-123")
        self.assertEqual(receipt.total_tokens, 110)
        self.assertEqual(receipt.cached_input_tokens, 30)
        self.assertEqual(receipt.elapsed_seconds, 3.25)
        self.assertEqual(receipt.final_output, "completed change")


if __name__ == "__main__":
    unittest.main()
