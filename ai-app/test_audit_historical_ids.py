import unittest

from audit import build_audit_event


class AuditHistoricalIdsTest(unittest.TestCase):
    def test_existing_call_defaults_to_empty_list(self):
        event = build_audit_event("INC-001", "CONTEXT_READY", [], [])
        self.assertEqual(event["historical_incident_ids"], [])
        self.assertEqual(event["stage"], "unspecified")
        self.assertEqual(event["matched_historical_incident_ids"], [])
        self.assertEqual(event["historical_matching_status"], "not_evaluated")

    def test_preserves_explicit_ids_and_order(self):
        event = build_audit_event(
            "INC-001", "CONTEXT_READY", [], [],
            stage="context_evaluation",
            historical_incident_ids=["HIST-002", "HIST-001"],
        )
        self.assertEqual(event["historical_incident_ids"], ["HIST-002", "HIST-001"])

    def test_empty_lists_are_independent_between_events(self):
        first = build_audit_event("INC-001", "CONTEXT_READY", [], [])
        first["historical_incident_ids"].append("HIST-001")
        first["matched_historical_incident_ids"].append("HIST-001")
        second = build_audit_event("INC-002", "P1_MANUAL_ESCALATION", [], [])
        self.assertEqual(second["historical_incident_ids"], [])
        self.assertEqual(second["matched_historical_incident_ids"], [])

    def test_copies_supplied_list(self):
        ids = ["HIST-001"]
        event = build_audit_event(
            "INC-001", "CONTEXT_READY", [], [], historical_incident_ids=ids
        )
        ids.append("HIST-002")
        self.assertEqual(event["historical_incident_ids"], ["HIST-001"])

    def test_retrieved_and_matched_ids_are_distinct_and_copied(self):
        retrieved = ["HIST-001", "HIST-002"]
        matched = ["HIST-002"]
        event = build_audit_event(
            "INC-001", "CONTEXT_READY", [], [],
            historical_incident_ids=retrieved,
            matched_historical_incident_ids=matched,
            historical_matching_status="evaluated",
        )
        retrieved.clear()
        matched.clear()
        self.assertEqual(event["historical_incident_ids"], ["HIST-001", "HIST-002"])
        self.assertEqual(event["matched_historical_incident_ids"], ["HIST-002"])
        self.assertEqual(event["historical_matching_status"], "evaluated")


if __name__ == "__main__":
    unittest.main()
