from __future__ import annotations

import importlib.util
from types import SimpleNamespace
import unittest

from local.harness.worker import PhaseLimitError, _ModelCallBudget, _metrics


class WorkerMetricsTests(unittest.TestCase):
    def test_reads_current_strands_metrics_shape(self) -> None:
        metrics = SimpleNamespace(
            accumulated_usage={
                "inputTokens": 120,
                "outputTokens": 30,
                "totalTokens": 150,
            },
            cycle_count=3,
            get_summary=lambda: {
                "total_cycles": 3,
                "accumulated_usage": {
                    "inputTokens": 120,
                    "outputTokens": 30,
                    "totalTokens": 150,
                },
            },
        )

        result = _metrics(SimpleNamespace(metrics=metrics))

        self.assertEqual(result, {"model_calls": 3, "tokens": 150})

    def test_preserves_legacy_strands_metrics_shape(self) -> None:
        metrics = SimpleNamespace(
            get_summary=lambda: {
                "cycleCount": 2,
                "accumulatedUsage": {"totalTokens": 75},
            }
        )

        result = _metrics(SimpleNamespace(metrics=metrics))

        self.assertEqual(result, {"model_calls": 2, "tokens": 75})

    def test_model_call_budget_stops_one_phase_without_retrying(self) -> None:
        budget = _ModelCallBudget("implementation", maximum=2)

        budget(object())
        budget(object())
        with self.assertRaisesRegex(PhaseLimitError, "implementation.*2 model calls"):
            budget(object())

        self.assertEqual(budget.calls, 3)

    @unittest.skipUnless(importlib.util.find_spec("strands"), "local extra not installed")
    def test_implementation_tools_exclude_navigation(self) -> None:
        from local.harness.worker import StrandsWorker

        tools = StrandsWorker._implementation_tools(SimpleNamespace())
        names = {
            getattr(tool, "tool_name", None)
            or getattr(tool, "name", None)
            or getattr(tool, "__name__", None)
            for tool in tools
        }

        self.assertEqual(names, {"replace_text", "write_file", "run_public_tests"})


if __name__ == "__main__":
    unittest.main()
