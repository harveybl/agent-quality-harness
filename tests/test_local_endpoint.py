from __future__ import annotations

from dataclasses import FrozenInstanceError
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
import socket
from threading import Thread
import unittest

from agent_quality_harness.local_endpoint import diagnose_endpoint
from agent_quality_harness.cli import main


class FixtureHandler(BaseHTTPRequestHandler):
    models_body = b'{"data":[{"id":"qwen-local"}]}'

    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        if self.path == "/health":
            body = b'{"status":"ok"}'
            status = 200
        elif self.path == "/v1/models":
            body = self.models_body
            status = 200
        else:
            body = b'{"error":"not found"}'
            status = 404
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class LocalEndpointTests(unittest.TestCase):
    def serve(self, *, models_body: bytes | None = None) -> tuple[ThreadingHTTPServer, str]:
        handler = type("ConfiguredHandler", (FixtureHandler,), {})
        if models_body is not None:
            handler.models_body = models_body
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        Thread(target=server.serve_forever, daemon=True).start()
        endpoint = f"http://127.0.0.1:{server.server_port}/v1"
        return server, endpoint

    def test_healthy_endpoint_reports_exact_model_identity_and_native_bounds(self) -> None:
        server, endpoint = self.serve()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        report = diagnose_endpoint(endpoint, expected_model="qwen-local")

        self.assertTrue(report.reachable)
        self.assertTrue(report.healthy)
        self.assertTrue(report.model_match)
        self.assertEqual(report.model_ids, ("qwen-local",))
        self.assertEqual(report.containment_mode, "native-process-bounds-only")
        with self.assertRaises(FrozenInstanceError):
            report.healthy = False  # type: ignore[misc]

    def test_unexpected_model_is_reachable_but_not_ready(self) -> None:
        server, endpoint = self.serve()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        report = diagnose_endpoint(endpoint, expected_model="muse-local")

        self.assertTrue(report.reachable)
        self.assertTrue(report.healthy)
        self.assertFalse(report.model_match)
        self.assertFalse(report.ready)
        self.assertIn("muse-local", report.error or "")

    def test_invalid_models_json_is_a_bounded_diagnostic(self) -> None:
        server, endpoint = self.serve(models_body=b"not-json")
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        report = diagnose_endpoint(endpoint)

        self.assertTrue(report.reachable)
        self.assertFalse(report.ready)
        self.assertIn("valid JSON", report.error or "")

    def test_connection_refusal_is_returned_not_raised(self) -> None:
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        report = diagnose_endpoint(f"http://127.0.0.1:{port}/v1", timeout=0.2)

        self.assertFalse(report.reachable)
        self.assertFalse(report.ready)
        self.assertTrue(report.error)

    def test_endpoint_must_be_http_or_https(self) -> None:
        with self.assertRaisesRegex(ValueError, "http"):
            diagnose_endpoint("file:///tmp/model")

    def test_local_doctor_cli_prints_read_only_endpoint_facts(self) -> None:
        server, endpoint = self.serve()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        output = StringIO()

        with redirect_stdout(output):
            status = main(
                ["local", "doctor", "--endpoint", endpoint, "--model", "qwen-local"]
            )

        self.assertEqual(status, 0)
        self.assertIn("reachable: yes", output.getvalue())
        self.assertIn("model match: yes", output.getvalue())
        self.assertIn("native-process-bounds-only", output.getvalue())


if __name__ == "__main__":
    unittest.main()
