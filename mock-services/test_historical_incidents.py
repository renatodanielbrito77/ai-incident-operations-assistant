import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class HistoricalIncidentsTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

    def test_checkout_contract_and_order(self):
        # A ordem da resposta não deve depender da ordem dos dados em memória.
        with patch.object(main, "historical_incidents", list(reversed(main.historical_incidents))):
            response = self.client.get(
                "/historical-incidents", params={"application": "checkout"}
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["application"], "checkout")
        records = body["historical_incidents"]
        self.assertEqual(
            [record["historical_incident_id"] for record in records],
            ["HIST-001", "HIST-002"],
        )
        for record in records:
            self.assertEqual(record["application"], "checkout")
            self.assert_contract(record)

    def assert_contract(self, record):
        self.assertEqual(set(record), {
            "historical_incident_id", "application", "summary",
            "symptoms", "resolution", "observed_result",
        })
        for field in set(record) - {"symptoms"}:
            self.assertIsInstance(record[field], str)
            self.assertTrue(record[field])
        self.assertIsInstance(record["symptoms"], list)
        self.assertTrue(record["symptoms"])
        for symptom in record["symptoms"]:
            self.assertIsInstance(symptom, str)
            self.assertTrue(symptom)

    def test_identity(self):
        response = self.client.get(
            "/historical-incidents", params={"application": "identity"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["application"], "identity")
        self.assertEqual(len(body["historical_incidents"]), 1)
        record = body["historical_incidents"][0]
        self.assertEqual(record["historical_incident_id"], "HIST-003")
        self.assertEqual(record["application"], "identity")
        self.assert_contract(record)

    def test_no_history(self):
        response = self.client.get(
            "/historical-incidents", params={"application": "billing"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "application": "billing", "historical_incidents": []
        })

    def test_required_nonempty_application(self):
        for params in ({}, {"application": ""}):
            with self.subTest(params=params):
                response = self.client.get("/historical-incidents", params=params)
                self.assertEqual(response.status_code, 422)

    def test_case_sensitive_filter(self):
        response = self.client.get(
            "/historical-incidents", params={"application": "Checkout"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "application": "Checkout", "historical_incidents": []
        })

    def test_unique_ids(self):
        ids = [record["historical_incident_id"] for record in main.historical_incidents]
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), len(ids))

    def test_existing_incident(self):
        response = self.client.get("/incidents/INC-001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "incident_id": "INC-001",
            "application": "checkout",
            "priority": "P2",
            "summary": "Aumento de erros no checkout",
        })

    def test_missing_incident(self):
        response = self.client.get("/incidents/INC-999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Incident not found"})


if __name__ == "__main__":
    unittest.main()
