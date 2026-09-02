"""Public adapter for the optional enhanced local-model controller."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .local_endpoint import diagnose_endpoint


def _controller_types() -> tuple[type[Any], type[Any]]:
    try:
        from .local_harness.controller import Controller
        from .local_harness.worker import StrandsWorker
    except ModuleNotFoundError:  # Source checkout before wheel installation.
        from local.harness.controller import Controller
        from local.harness.worker import StrandsWorker
    return Controller, StrandsWorker


def run_local(
    workspace: Path,
    endpoint: str,
    model: str,
    *,
    worker: Any | None = None,
) -> dict[str, Any]:
    """Run once against an existing endpoint; never manage or retry the server."""
    report = diagnose_endpoint(endpoint, expected_model=model)
    if not report.ready:
        raise RuntimeError(report.error or "local endpoint is not ready")
    Controller, StrandsWorker = _controller_types()
    if worker is None:
        if report.missing_optional_dependencies:
            missing = ", ".join(report.missing_optional_dependencies)
            raise RuntimeError(
                f"local dependencies are missing ({missing}); install agent-quality-harness[local]"
            )
        worker = StrandsWorker(report.endpoint, model)
    return Controller(
        workspace,
        worker,
        run_metadata={
            "endpoint": report.endpoint,
            "model": model,
            "containment_mode": report.containment_mode,
        },
    ).run()
