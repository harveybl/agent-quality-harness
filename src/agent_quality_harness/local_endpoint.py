"""Read-only probes for an existing llama.cpp-compatible endpoint."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class EndpointReport:
    endpoint: str
    reachable: bool
    healthy: bool
    model_ids: tuple[str, ...]
    expected_model: str | None
    model_match: bool | None
    containment_mode: str
    missing_optional_dependencies: tuple[str, ...]
    error: str | None

    @property
    def ready(self) -> bool:
        return self.reachable and self.healthy and self.model_match is not False


def _normalize(endpoint: str) -> tuple[str, str]:
    value = urlsplit(endpoint)
    if value.scheme not in {"http", "https"} or not value.hostname:
        raise ValueError("endpoint must be an http or https URL")
    if value.username or value.password or value.query or value.fragment:
        raise ValueError("endpoint must not contain credentials, a query, or a fragment")
    path = value.path.rstrip("/")
    if path not in {"", "/v1"}:
        raise ValueError("endpoint path must be empty or /v1")
    origin = urlunsplit((value.scheme, value.netloc, "", "", ""))
    return f"{origin}/v1", origin


def _read_json(url: str, timeout: float) -> object:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "aqh/doctor"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError("response exceeded the 1 MiB diagnostic limit")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("endpoint did not return valid JSON") from error


def _missing_dependencies() -> tuple[str, ...]:
    modules = {"strands": "strands-agents", "openai": "openai", "pydantic": "pydantic"}
    return tuple(
        distribution
        for module, distribution in modules.items()
        if importlib.util.find_spec(module) is None
    )


def diagnose_endpoint(
    endpoint: str,
    *,
    expected_model: str | None = None,
    timeout: float = 5.0,
) -> EndpointReport:
    """Probe health and model identity without starting, stopping, or changing a server."""
    if timeout <= 0 or timeout > 30:
        raise ValueError("timeout must be greater than zero and at most 30 seconds")
    normalized, origin = _normalize(endpoint)
    host = urlsplit(normalized).hostname
    containment = (
        "native-process-bounds-only"
        if host in {"127.0.0.1", "::1", "localhost"}
        else "remote-endpoint-no-workspace-isolation"
    )
    missing = _missing_dependencies()
    try:
        health = _read_json(f"{origin}/health", timeout)
        healthy = isinstance(health, dict)
        models = _read_json(f"{normalized}/models", timeout)
        if not isinstance(models, dict) or not isinstance(models.get("data"), list):
            raise ValueError("models response must contain a data array")
        model_ids = tuple(
            item["id"]
            for item in models["data"]
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
        )
        if not model_ids:
            raise ValueError("models response did not contain any model IDs")
        match = expected_model in model_ids if expected_model is not None else None
        error = None
        if match is False:
            error = f"expected model {expected_model!r} was not advertised"
        return EndpointReport(
            endpoint=normalized,
            reachable=True,
            healthy=healthy,
            model_ids=model_ids,
            expected_model=expected_model,
            model_match=match,
            containment_mode=containment,
            missing_optional_dependencies=missing,
            error=error,
        )
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        reachable = not isinstance(error, (URLError, TimeoutError, OSError)) or isinstance(
            error, HTTPError
        )
        return EndpointReport(
            endpoint=normalized,
            reachable=reachable,
            healthy=False,
            model_ids=(),
            expected_model=expected_model,
            model_match=False if expected_model is not None else None,
            containment_mode=containment,
            missing_optional_dependencies=missing,
            error=str(error),
        )
