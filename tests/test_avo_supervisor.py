from __future__ import annotations

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from agent_quality_harness.experiments.directive import Directive, ReviewPacket
from agent_quality_harness.experiments.supervisor import AvoSupervisor


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


if __name__ == "__main__":
    unittest.main()
