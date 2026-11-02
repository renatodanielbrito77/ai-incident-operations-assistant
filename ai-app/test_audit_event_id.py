import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, Mock, call, patch

import httpx
from fastapi.testclient import TestClient


class AuditEventIdTest(unittest.TestCase):
    def setUp(self):
        search = ModuleType("search_qdrant")
        self.chunk = {
            "chunk_id": "RB-001-02-01",
            "document_id": "RB-001",
            "source": "docs/runbooks/checkout-payment-timeout.md",
            "section": "Sintomas",
            "content": "Checkout lento",
        }
        self.search = search.search_chunks = Mock(return_value=[
            {"score": 0.9, "chunk": self.chunk}
        ])
        self.limits = search.get_document_limits = Mock(return_value=[
            {**self.chunk, "chunk_id": "RB-001-05", "section": "Limites"}
        ])
        spec = importlib.util.spec_from_file_location(
            "main_under_test", Path(__file__).with_name("main.py")
        )
        self.main = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"search_qdrant": search}):
            spec.loader.exec_module(self.main)

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.audit_path = Path(directory.name) / "events.jsonl"
        self.main.AUDIT_PATH = self.audit_path
        self.append = Mock()
        self.histories = [
            {
                "historical_incident_id": historical_id,
                "application": application,
                "summary": "Incidente fictício anterior",
                "symptoms": ["Sintoma anterior"],
                "resolution": "Intervenção realizada no passado",
                "observed_result": "Resultado observado no passado",
            }
            for historical_id, application in (
                ("HIST-001", "checkout"),
                ("HIST-002", "checkout"),
                ("HIST-003", "identity"),
            )
        ]

    def request(
        self, priority="P2", incident_id="INC-001", missing=False,
        application="checkout", history_error=None,
    ):
        payloads = [
            {
                "incident_id": incident_id,
                "application": application,
                "priority": priority,
                "summary": "Checkout lento",
            },
            {
                "application": application,
                "historical_incidents": [
                    record for record in self.histories
                    if record["application"] == application
                ],
            },
            {
                "application": application,
                "status": "degraded",
                "error_rate_percent": 1.0,
                "latency_p95_ms": 900.0,
            },
            {"application": application, "entries": []},
        ]
        responses = [
            httpx.Response(
                404 if missing and index == 0 else 200,
                json=payload,
                request=httpx.Request("GET", "http://mock.test"),
            )
            for index, payload in enumerate(payloads)
        ]
        if history_error is not None:
            responses[1] = history_error
        self.http = AsyncMock()
        self.http.__aenter__.return_value = self.http
        self.http.get.side_effect = responses
        with (
            patch.object(self.main.httpx, "AsyncClient", return_value=self.http) as factory,
            patch.object(self.main, "append_audit_event", self.append),
            patch.object(
                self.main, "build_audit_event",
                wraps=self.main.build_audit_event,
            ) as build,
            TestClient(self.main.app) as client,
        ):
            response = client.post(f"/investigate/{incident_id}")
        factory.assert_called_once_with(timeout=5.0)
        build.assert_called_once()
        self.append.assert_called_once()
        self.append.assert_called_with(
            self.append.call_args.args[0], self.audit_path
        )
        return response

    def assert_correlation(self, response, code, stage, incident_id="INC-001"):
        self.assertEqual(response.status_code, 200)
        event = self.append.call_args.args[0]
        event_id = response.json()["audit_event_id"]
        self.assertIsInstance(event_id, str)
        self.assertTrue(event_id)
        self.assertEqual(event_id, event["event_id"])
        self.assertEqual(event["incident_id"], incident_id)
        self.assertEqual(event["analysis_code"], code)
        self.assertEqual(event["stage"], stage)

    def test_context_ready(self):
        response = self.request()
        self.assert_correlation(response, "CONTEXT_READY", "context_evaluation")
        self.assertEqual(response.json()["analysis_status"], "context_ready")
        self.assertEqual(response.json()["analysis_code"], "CONTEXT_READY")
        self.assertEqual(response.json()["historical_incidents"], self.histories[:2])
        base = self.main.MOCK_SERVICES_URL
        self.assertEqual(self.http.get.await_args_list, [
            call(f"{base}/incidents/INC-001"),
            call(f"{base}/historical-incidents", params={"application": "checkout"}),
            call(f"{base}/monitoring/checkout"),
            call(f"{base}/logs/checkout"),
        ])

    def test_no_documentation(self):
        self.search.return_value = []
        response = self.request()
        self.assert_correlation(response, "NO_DOCUMENTATION", "context_evaluation")
        self.assertEqual(response.json()["analysis_status"], "abstained")
        self.assertEqual(response.json()["analysis_code"], "NO_DOCUMENTATION")
        self.assertEqual(response.json()["historical_incidents"], self.histories[:2])
        self.limits.assert_not_called()

    def test_missing_limits(self):
        self.limits.return_value = []
        response = self.request()
        self.assert_correlation(
            response, "MISSING_DOCUMENT_LIMITS", "context_evaluation"
        )
        self.assertEqual(response.json()["analysis_status"], "abstained")
        self.assertEqual(response.json()["analysis_code"], "MISSING_DOCUMENT_LIMITS")
        self.assertEqual(response.json()["historical_incidents"], self.histories[:2])

    def test_p1_escalation(self):
        response = self.request(priority="P1", incident_id="INC-002")
        self.assert_correlation(
            response, "P1_MANUAL_ESCALATION", "priority_check", "INC-002"
        )
        self.assertEqual(response.json()["status"], "manual_escalation_required")
        self.assertEqual(self.http.get.await_count, 1)
        self.http.get.assert_awaited_once_with(
            f"{self.main.MOCK_SERVICES_URL}/incidents/INC-002"
        )
        self.assertNotIn("historical_incidents", response.json())
        self.search.assert_not_called()
        self.limits.assert_not_called()

    def test_audit_write_failure(self):
        for priority in ("P2", "P1"):
            with self.subTest(priority=priority):
                self.append = Mock(side_effect=OSError("Falha simulada"))
                response = self.request(priority=priority)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json(), {
                    "detail": "Não foi possível registrar a investigação no audit"
                })
                self.assertNotIn("audit_event_id", response.json())
        self.assertFalse(self.audit_path.exists())

    def test_incident_not_found(self):
        response = self.request(incident_id="INC-999", missing=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Incident not found"})
        self.assertNotIn("audit_event_id", response.json())
        self.assertEqual(self.http.get.await_count, 1)
        self.search.assert_not_called()
        self.limits.assert_not_called()

    def test_response_matches_real_audit_file(self):
        self.append = Mock(wraps=self.main.append_audit_event)
        response = self.request()
        self.assert_correlation(response, "CONTEXT_READY", "context_evaluation")
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])
        self.assertEqual(response.json()["audit_event_id"], event["event_id"])
        self.assertEqual(event, self.append.call_args.args[0])

    def test_identity_history_without_documentation(self):
        self.search.return_value = []
        response = self.request(incident_id="INC-003", application="identity")
        self.assert_correlation(
            response, "NO_DOCUMENTATION", "context_evaluation", "INC-003"
        )
        self.assertEqual(response.json()["historical_incidents"], self.histories[2:])
        self.assertEqual(response.json()["documentation"], [])
        self.assertEqual(response.json()["document_limits"], [])
        self.assertEqual(response.json()["analysis_code"], "NO_DOCUMENTATION")
        self.assertEqual(response.json()["analysis_status"], "abstained")
        self.assertEqual(self.http.get.await_args_list[1], call(
            f"{self.main.MOCK_SERVICES_URL}/historical-incidents",
            params={"application": "identity"},
        ))

    def test_application_without_history(self):
        response = self.request(application="billing")
        self.assert_correlation(response, "CONTEXT_READY", "context_evaluation")
        self.assertEqual(response.json()["historical_incidents"], [])

    def test_history_communication_failures(self):
        scenarios = [
            (httpx.ConnectError("Falha simulada"), 503,
             "MOCK_SERVICES_CONNECTION_FAILED", "Falha na conexão com Mock Services"),
            (httpx.ReadTimeout("Timeout simulado"), 504,
             "MOCK_SERVICES_TIMEOUT", "Mock Services não respondeu dentro do tempo limite"),
        ]
        for error, status, code, detail in scenarios:
            with self.subTest(code=code):
                self.append = Mock()
                response = self.request(history_error=error)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json(), {"detail": detail})
                event = self.append.call_args.args[0]
                self.assertEqual(event["incident_id"], "INC-001")
                self.assertEqual(event["analysis_code"], code)
                self.assertEqual(event["stage"], "historical_incidents_lookup")
                self.assertEqual(self.http.get.await_count, 2)
                self.search.assert_not_called()
                self.limits.assert_not_called()


if __name__ == "__main__":
    unittest.main()
