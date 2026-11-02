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
from qdrant_client.http.exceptions import ResponseHandlingException


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
        self.log_entries = []
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
        http_failure=None,
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
            {"application": application, "entries": self.log_entries},
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
        if http_failure is not None:
            index, error = http_failure
            responses[index] = error
        self.http = AsyncMock()
        self.http.__aenter__.return_value = self.http
        self.http.get.side_effect = responses
        with (
            patch.object(self.main.httpx, "AsyncClient", return_value=self.http) as factory,
            patch.object(self.main, "append_audit_event", self.append),
            patch.object(
                self.main, "match_historical_incidents",
                wraps=self.main.match_historical_incidents,
            ) as matcher,
            patch.object(
                self.main, "build_audit_event",
                wraps=self.main.build_audit_event,
            ) as build,
            TestClient(self.main.app) as client,
        ):
            response = client.post(f"/investigate/{incident_id}")
        factory.assert_called_once_with(timeout=5.0)
        self.matcher = matcher
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
        self.assertEqual(event["historical_incident_ids"], [
            record["historical_incident_id"]
            for record in response.json().get("historical_incidents", [])
        ])
        self.assertEqual(event["matched_historical_incident_ids"], [
            match["historical_incident"]["historical_incident_id"]
            for match in response.json().get("historical_incident_matches", [])
        ])
        self.assertEqual(
            event["historical_matching_status"],
            "evaluated" if "historical_incident_matches" in response.json()
            else "not_evaluated",
        )
        self.assertNotIn("matched_historical_incident_ids", response.json())
        self.assertNotIn("historical_matching_status", response.json())

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
        self.assertNotIn("historical_incident_matches", response.json())
        self.matcher.assert_not_called()
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
        self.assertEqual(self.append.call_args.args[0]["historical_incident_ids"], [])
        self.assertEqual(self.append.call_args.args[0]["matched_historical_incident_ids"], [])
        self.assertEqual(self.append.call_args.args[0]["historical_matching_status"], "not_evaluated")
        self.assertEqual(self.http.get.await_count, 1)
        self.search.assert_not_called()
        self.limits.assert_not_called()

    def test_response_matches_real_audit_file(self):
        self.load_history_and_log_fixtures("checkout")
        self.append = Mock(wraps=self.main.append_audit_event)
        response = self.request()
        self.assert_correlation(response, "CONTEXT_READY", "context_evaluation")
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])
        self.assertEqual(response.json()["audit_event_id"], event["event_id"])
        self.assertEqual(event, self.append.call_args.args[0])
        self.assertEqual(event["historical_incident_ids"], ["HIST-001", "HIST-002"])
        self.assertEqual(event["matched_historical_incident_ids"], ["HIST-001", "HIST-002"])
        self.assertEqual(event["historical_matching_status"], "evaluated")

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
                self.assertEqual(event["matched_historical_incident_ids"], [])
                self.assertEqual(event["historical_matching_status"], "not_evaluated")
                self.assertEqual(event["historical_incident_ids"], [])
                self.assertEqual(self.http.get.await_count, 2)
                self.search.assert_not_called()
                self.limits.assert_not_called()

    def test_documentation_search_failure(self):
        self.load_history_and_log_fixtures("checkout")
        self.search.side_effect = ResponseHandlingException(
            RuntimeError("Falha documental simulada")
        )
        response = self.request()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {
            "detail": "Falha na comunicação com a base documental"
        })
        event = self.append.call_args.args[0]
        self.assertEqual(event["incident_id"], "INC-001")
        self.assertEqual(event["analysis_code"], "DOCUMENT_BASE_COMMUNICATION_FAILED")
        self.assertEqual(event["stage"], "documentation_search")
        self.assertEqual(event["matched_historical_incident_ids"], ["HIST-001", "HIST-002"])
        self.assertEqual(event["historical_matching_status"], "evaluated")
        self.assertEqual(event["historical_incident_ids"], ["HIST-001", "HIST-002"])
        self.assertEqual(event["retrieved_chunk_ids"], [])
        self.assertEqual(event["limit_chunk_ids"], [])
        self.assertEqual(self.http.get.await_count, 4)
        self.search.assert_called_once()
        self.limits.assert_not_called()

    def test_mock_services_communication_failure_matrix(self):
        base = self.main.MOCK_SERVICES_URL
        calls = [
            call(f"{base}/incidents/INC-001"),
            call(f"{base}/historical-incidents", params={"application": "checkout"}),
            call(f"{base}/monitoring/checkout"),
            call(f"{base}/logs/checkout"),
        ]
        stages = [(0, "incident_lookup"), (2, "monitoring_lookup"), (3, "logs_lookup")]
        failures = [
            (httpx.ConnectError, 503, "MOCK_SERVICES_CONNECTION_FAILED",
             "Falha na conexão com Mock Services"),
            (httpx.ReadTimeout, 504, "MOCK_SERVICES_TIMEOUT",
             "Mock Services não respondeu dentro do tempo limite"),
        ]
        for index, stage in stages:
            for error_type, status, code, detail in failures:
                with self.subTest(stage=stage, error=error_type.__name__):
                    self.append = Mock()
                    response = self.request(http_failure=(
                        index, error_type("Falha simulada")
                    ))
                    self.assertEqual(response.status_code, status)
                    self.assertEqual(response.json(), {"detail": detail})
                    event = self.append.call_args.args[0]
                    self.assertEqual(event["incident_id"], "INC-001")
                    self.assertEqual(event["analysis_code"], code)
                    self.assertEqual(event["stage"], stage)
                    self.assertEqual(event["matched_historical_incident_ids"], [])
                    self.assertEqual(event["historical_matching_status"], "not_evaluated")
                    self.assertEqual(
                        event["historical_incident_ids"],
                        [] if index == 0 else ["HIST-001", "HIST-002"],
                    )
                    self.assertEqual(event["retrieved_chunk_ids"], [])
                    self.assertEqual(event["limit_chunk_ids"], [])
                    self.assertEqual(self.http.get.await_args_list, calls[:index + 1])
                    self.search.assert_not_called()
                    self.limits.assert_not_called()

    def load_history_and_log_fixtures(self, application):
        spec = importlib.util.spec_from_file_location(
            "mock_services_fixtures",
            Path(__file__).resolve().parent.parent / "mock-services" / "main.py",
        )
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        self.histories = fixtures.historical_incidents
        self.log_entries = fixtures.logs[application]["entries"]

    def test_checkout_history_matches_response(self):
        self.load_history_and_log_fixtures("checkout")
        response = self.request()
        self.assert_correlation(response, "CONTEXT_READY", "context_evaluation")
        self.assertEqual(response.json()["historical_incidents"], self.histories[:2])
        self.assertEqual(response.json()["historical_incident_matches"], [
            {
                "historical_incident": incident,
                "matched_symptoms": ["Timeout while connecting to payment service"],
            }
            for incident in self.histories[:2]
        ])
        self.matcher.assert_called_once_with(self.histories[:2], self.log_entries)

    def test_identity_match_preserves_no_documentation(self):
        self.load_history_and_log_fixtures("identity")
        self.search.return_value = []
        response = self.request(incident_id="INC-003", application="identity")
        self.assert_correlation(
            response, "NO_DOCUMENTATION", "context_evaluation", "INC-003"
        )
        self.assertEqual(response.json()["analysis_code"], "NO_DOCUMENTATION")
        self.assertEqual(response.json()["analysis_status"], "abstained")
        self.assertEqual(response.json()["documentation"], [])
        self.assertEqual(response.json()["historical_incidents"], self.histories[2:])
        self.assertEqual(response.json()["historical_incident_matches"], [{
            "historical_incident": self.histories[2],
            "matched_symptoms": ["Password reset email delivery failed"],
        }])

    def test_no_matching_symptom_preserves_all_histories(self):
        self.load_history_and_log_fixtures("checkout")
        self.log_entries = [{
            "timestamp": "2026-10-05T12:00:00Z", "level": "ERROR",
            "message": "Timeout while connecting to payment service again",
        }]
        response = self.request()
        self.assert_correlation(response, "CONTEXT_READY", "context_evaluation")
        self.assertEqual(response.json()["historical_incident_matches"], [])
        self.assertEqual(response.json()["historical_incidents"], self.histories[:2])

    def test_response_retains_nonmatching_history(self):
        self.load_history_and_log_fixtures("checkout")
        self.histories[1] = {**self.histories[1], "symptoms": ["Outro sintoma"]}
        response = self.request()
        self.assert_correlation(response, "CONTEXT_READY", "context_evaluation")
        self.assertEqual(response.json()["historical_incidents"], self.histories[:2])
        self.assertEqual(response.json()["historical_incident_matches"], [{
            "historical_incident": self.histories[0],
            "matched_symptoms": ["Timeout while connecting to payment service"],
        }])

    def test_multiple_documents_with_partial_limits(self):
        second_chunk = {
            **self.chunk, "document_id": "RB-002", "chunk_id": "RB-002-02-01"
        }
        # Resultado fora de ordem e dois trechos do mesmo documento:
        # deve consultar os limites de cada documento apenas uma vez.
        self.search.return_value = [
            {"score": 0.9, "chunk": second_chunk},
            {"score": 0.8, "chunk": self.chunk},
            {"score": 0.7, "chunk": {**self.chunk, "chunk_id": "RB-001-03-01"}},
        ]
        available_limits = [
            {**self.chunk, "chunk_id": "RB-001-05", "section": "Limites"}
        ]
        self.limits.side_effect = lambda document_id: (
            available_limits if document_id == "RB-001" else []
        )
        response = self.request()
        self.assert_correlation(
            response, "MISSING_DOCUMENT_LIMITS", "context_evaluation"
        )
        body = response.json()
        self.assertEqual(body["analysis_status"], "abstained")
        self.assertEqual(body["analysis_code"], "MISSING_DOCUMENT_LIMITS")
        self.assertEqual(body["analysis_reason"],
                         "Limites não encontrados para os documentos: RB-002")
        self.assertEqual(body["documentation_status"], "retrieved")
        self.assertEqual(body["document_limits"], [
            {**available_limits[0], "subsection": None}
        ])
        self.assertEqual(body["historical_incidents"], self.histories[:2])
        self.assertEqual(self.limits.call_args_list, [call("RB-001"), call("RB-002")])
        event = self.append.call_args.args[0]
        self.assertEqual(event["retrieved_chunk_ids"], [
            "RB-002-02-01", "RB-001-02-01", "RB-001-03-01"
        ])
        self.assertEqual(event["limit_chunk_ids"], ["RB-001-05"])


if __name__ == "__main__":
    unittest.main()
