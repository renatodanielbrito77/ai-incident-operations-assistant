import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi.testclient import TestClient
from qdrant_client.http.exceptions import ResponseHandlingException


class DocumentLimitsFailureTest(unittest.TestCase):
    def test_document_limits_failure(self):
        search_module = ModuleType("search_qdrant")
        search_module.search_chunks = Mock(return_value=[
            {"chunk": {"document_id": "RB-001"}}
        ])
        search_module.get_document_limits = Mock(
            side_effect=ResponseHandlingException(
                RuntimeError("Falha simulada")
            )
        )

        spec = importlib.util.spec_from_file_location(
            "main_under_test",
            Path(__file__).with_name("main.py"),
        )
        main = importlib.util.module_from_spec(spec)

        with patch.dict(sys.modules, {"search_qdrant": search_module}):
            spec.loader.exec_module(main)

        responses = [
            httpx.Response(200, json={
                "incident_id": "INC-001",
                "application": "checkout",
                "priority": "P2",
                "summary": "Checkout lento",
            }),
            httpx.Response(200, json={
                "application": "checkout",
                "historical_incidents": [{"historical_incident_id": "HIST-001"}],
            }),
            httpx.Response(200, json={
                "application": "checkout",
                "status": "degraded",
                "error_rate_percent": 1.0,
                "latency_p95_ms": 900.0,
            }),
            httpx.Response(200, json={
                "application": "checkout",
                "entries": [],
            }),
        ]
        for response in responses:
            response.request = httpx.Request("GET", "http://mock.test")

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = responses
        persist = AsyncMock()

        with (
            patch.object(
                main.httpx, "AsyncClient", return_value=mock_client
            ),
            patch.object(main, "persist_audit_event", persist),
            TestClient(main.app) as client,
        ):
            response = client.post("/investigate/INC-001")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {
            "detail": "Falha na comunicação com a base documental"
        })

        self.assertEqual(mock_client.get.await_count, 4)
        search_module.search_chunks.assert_called_once()
        search_module.get_document_limits.assert_called_once_with("RB-001")

        persist.assert_awaited_once()
        event = persist.await_args.args[0]
        self.assertEqual(event["incident_id"], "INC-001")
        self.assertEqual(
            event["analysis_code"],
            "DOCUMENT_BASE_COMMUNICATION_FAILED",
        )
        self.assertEqual(event["stage"], "document_limits_lookup")
        self.assertEqual(event["historical_incident_ids"], ["HIST-001"])


if __name__ == "__main__":
    unittest.main()
