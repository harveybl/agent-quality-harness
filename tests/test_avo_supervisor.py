from __future__ import annotations

from pathlib import Path
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent_quality_harness.experiments.directive import Directive, ReviewPacket
from agent_quality_harness.experiments.supervisor import AvoSupervisor
from agent_quality_harness.experiments.providers import (
    _claude_json_result,
    claude_strands_model,
)


class ScriptedAgent:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, prompt: str, **kwargs: object) -> object:
        self.prompts.append(prompt)
        return SimpleNamespace(
            structured_output={
                "action": "redirect",
                "strategy": "minimal-repair",
                "instruction": "Repair only the failing assertion.",
                "rationale": "The deterministic check isolates one regression.",
            },
            metrics=SimpleNamespace(
                accumulated_usage={
                    "inputTokens": 120,
                    "outputTokens": 30,
                    "totalTokens": 150,
                },
                cycle_durations=(0.4, 0.6),
                tool_metrics={},
            ),
        )


class AvoSupervisorTests(unittest.TestCase):
    def test_current_claude_verbose_json_array_selects_one_result_event(self) -> None:
        output = (
            '[{"type":"system","apiKeySource":"none"},'
            '{"type":"result","structured_output":{"action":"redirect"},'
            '"usage":{"input_tokens":10,"output_tokens":4}}]'
        )

        result = _claude_json_result(output)

        self.assertEqual(result["structured_output"], {"action": "redirect"})
        self.assertEqual(result["usage"]["output_tokens"], 4)

    def test_claude_json_object_receipt_remains_supported(self) -> None:
        output = '{"structured_output":{"action":"stop"},"usage":{}}'
        self.assertEqual(_claude_json_result(output)["structured_output"]["action"], "stop")

    def test_directive_requires_bounded_action_and_nonempty_text(self) -> None:
        for action in ("continue", "redirect", "stop"):
            directive = Directive.from_object(
                {
                    "action": action,
                    "strategy": "minimal-repair",
                    "instruction": "Use the evidence.",
                    "rationale": "It is bounded.",
                }
            )
            self.assertEqual(directive.action, action)
        for invalid in ("restart", "", None):
            with self.assertRaises(ValueError):
                Directive.from_object(
                    {
                        "action": invalid,
                        "strategy": "minimal-repair",
                        "instruction": "Use the evidence.",
                        "rationale": "It is bounded.",
                    }
                )
        with self.assertRaises(ValueError):
            Directive.from_object(
                {
                    "action": "continue",
                    "strategy": "",
                    "instruction": "",
                    "rationale": "",
                }
            )

    def test_supervisor_is_toolless_persistent_external_and_reports_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            workspace = base / "candidate"
            session_root = base / "sessions"
            workspace.mkdir()
            captured: dict[str, object] = {}
            scripted = ScriptedAgent()

            def factory(**kwargs: object) -> ScriptedAgent:
                captured.update(kwargs)
                return scripted

            supervisor = AvoSupervisor(
                workspace=workspace,
                session_root=session_root,
                session_id="review-1",
                model=object(),
                agent_factory=factory,
            )
            directive = supervisor.decide(
                ReviewPacket(
                    task_summary="Fix inventory reservation semantics.",
                    worker_diff="- return False\n+ return reserved",
                    check_evidence="test_reserve: expected true, got false",
                    repair_cycle=1,
                    repairs_remaining=2,
                )
            )

            self.assertTrue(session_root.is_dir())
            if os.name != "nt":
                self.assertEqual(session_root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(captured["tools"], [])
        self.assertEqual(captured["session_id"], "review-1")
        self.assertEqual(captured["session_root"], session_root.resolve())
        self.assertEqual(directive.action, "redirect")
        self.assertEqual(supervisor.last_usage.total_tokens, 150)
        self.assertEqual(supervisor.last_usage.cycles, 2)
        self.assertEqual(supervisor.last_usage.tool_calls, 0)
        self.assertIn("inventory reservation", scripted.prompts[0])

    def test_session_state_cannot_live_inside_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            with self.assertRaisesRegex(ValueError, "outside"):
                AvoSupervisor(
                    workspace=workspace,
                    session_root=workspace / ".sessions",
                    session_id="review-1",
                    model=object(),
                    agent_factory=lambda **kwargs: ScriptedAgent(),
                )

    def test_pinned_strands_agent_accepts_native_cli_model_without_external_tools(self) -> None:
        try:
            import strands  # noqa: F401
        except ImportError:
            self.skipTest("experiment optional dependencies are not installed")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "candidate"
            workspace.mkdir()
            model = claude_strands_model(
                model_id="fable", effort="high", working_dir=root / "model"
            )
            supervisor = AvoSupervisor(
                workspace=workspace,
                session_root=root / "sessions",
                session_id="strands-smoke",
                model=model,
            )
            output = SimpleNamespace(
                returncode=0,
                stderr="",
                stdout=(
                    '{"structured_output":{"action":"stop","strategy":"done",'
                    '"instruction":"Stop.","rationale":"Checks pass."},'
                    '"usage":{"input_tokens":10,"output_tokens":4}}'
                ),
            )
            with patch(
                "agent_quality_harness.experiments.providers.subprocess.run",
                return_value=output,
            ) as native_run:
                directive = supervisor.decide(
                    ReviewPacket("task", "diff", "failed", 0, 2)
                )

        self.assertEqual(directive.action, "stop")
        self.assertEqual(supervisor.last_usage.total_tokens, 14)
        self.assertEqual(supervisor.last_usage.tool_calls, 0)
        argv = native_run.call_args.args[0]
        self.assertEqual(argv[0], "claude")
        self.assertEqual(argv[argv.index("--tools") + 1], "")


if __name__ == "__main__":
    unittest.main()
