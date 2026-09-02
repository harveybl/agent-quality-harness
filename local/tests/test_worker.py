from __future__ import annotations

from types import SimpleNamespace
import unittest

from local.harness.worker import _metrics


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


if __name__ == "__main__":
    unittest.main()
