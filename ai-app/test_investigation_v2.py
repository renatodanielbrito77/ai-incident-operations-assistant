from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from document_collection import DocumentControl, ControlError
from document_policy import DocumentIntegrityError
from investigation_v2 import investigate_v2
from test_document_collection import FakeBackend, chunks


def snapshot(case=1):
    incident = dict(incident_id=f"INC-V2-{case:03}", application="checkout", priority="P1" if case == 4 else "P2",
                    summary="Checkout com falhas", window_start="2026-11-04T10:00:00Z", window_end="2026-11-04T10:10:00Z",
                    incident_metadata={"original": True})
    entries = [] if case == 2 else [dict(timestamp="2026-11-04T10:02:00Z", level="ERROR", message="timeout", trace_metadata={"origin": "synthetic"})]
    return dict(fictional=True, incident=incident,
                monitoring=dict(application="checkout", status="degraded", error_rate_percent=12.5,
                                latency_p95_ms=1800, timestamp="2026-11-03T10:05:00Z" if case == 3 else "2026-11-04T10:05:00Z",
                                measurement_metadata={"aggregation": "não informado"}),
                logs=dict(application="checkout", entries=entries, source_metadata={"provided": True}),
                additional_sources_provided=[], snapshot_metadata={"unchanged": [1, 2]})


def history(message="timeout", identifier="HIST-V2-001"):
    return dict(historical_incident_id=identifier, application="checkout", summary="Experiência passada",
                symptoms=[message], resolution="Registro passado, não recomendação",
                observed_result="Não comprova causa", occurred_at="2026-10-10T12:00:00Z",
                record_completeness_declared="partial", fictional=True, history_metadata={"preserve": True})


class InvestigationV2Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/var/tmp")
        self.addCleanup(self.temp.cleanup)
        self.backend = FakeBackend()
        self.queries = []
        self.evidence = snapshot()
        self.evidence_provider = Mock(side_effect=lambda: self.evidence)
        self.history_provider = Mock(return_value=[history()])
        self.encoder = Mock(side_effect=lambda query: self.queries.append(query) or [1.0, 0.0])
        self.factory = Mock(side_effect=self.documents)
        self.result = None

    @contextmanager
    def documents(self):
        with DocumentControl(self.temp.name, "runbook_chunks_v2_flow_test", "fake", self.backend) as control:
            if not self.backend.present:
                control.load(chunks(), [[1., 0.]] * 4, 2)
            yield control

    def run_case(self, value=None):
        if value is not None:
            self.evidence = value
        self.result = investigate_v2(self.evidence["incident"], evidence_provider=self.evidence_provider,
                                     history_provider=self.history_provider, document_control_factory=self.factory,
                                     encode_query=self.encoder, audit_event_id="provided-audit-id")
        return self.result

    def assert_no_documents(self):
        self.factory.assert_not_called()
        self.encoder.assert_not_called()
        self.history_provider.assert_not_called()
        self.assertIsNone(self.result.package)

    def test_four_expected_paths_and_p1_without_evidence_or_state(self):
        for case, expected in ((1, "CONTEXT_READY"), (2, "NO_LOG_MESSAGE"), (3, "MONITORING_OUTSIDE_WINDOW"), (4, "P1_MANUAL_ESCALATION")):
            with self.subTest(case=case):
                self.evidence_provider.reset_mock(); self.history_provider.reset_mock(); self.factory.reset_mock(); self.encoder.reset_mock()
                result = self.run_case(snapshot(case))
                self.assertEqual(result.state, expected)
                if case != 1:
                    self.assert_no_documents()
                if case == 4:
                    self.evidence_provider.assert_not_called()
                    self.assertFalse(result.handoff.notification_sent)
                    self.assertIsNone(result.handoff.channel_address)
                    self.assertIsNone(result.evidence)

    def test_p1_does_not_open_missing_corrupt_or_locked_document_control(self):
        for failure in (FileNotFoundError("missing"), ControlError("corrupt"), ControlError("locked")):
            with self.subTest(failure=failure):
                factory = Mock(side_effect=failure)
                evidence = Mock(side_effect=AssertionError("evidence accessed"))
                hist = Mock(side_effect=AssertionError("history accessed"))
                encode = Mock(side_effect=AssertionError("encoder accessed"))
                result = investigate_v2(snapshot(4)["incident"], evidence_provider=evidence, history_provider=hist,
                                         document_control_factory=factory, encode_query=encode, audit_event_id="provided")
                self.assertEqual(result.state, "P1_MANUAL_ESCALATION")
                for mock in (factory, evidence, hist, encode):
                    mock.assert_not_called()

    def test_p1_does_not_validate_invalid_nested_evidence(self):
        value = snapshot(4); value["monitoring"] = "invalid"; value["logs"] = None
        self.assertEqual(self.run_case(value).state, "P1_MANUAL_ESCALATION")
        self.evidence_provider.assert_not_called()

    def test_mixed_logs_only_current_used_for_history_and_query(self):
        current = self.evidence["logs"]["entries"][0]
        old = {**current, "timestamp": "2026-11-03T10:02:00Z", "message": "old-only-message"}
        blank = {**current, "message": " \t"}
        self.evidence["logs"]["entries"] = [old, blank, current]
        self.history_provider.return_value = [history(), history("old-only-message", "HIST-V2-002")]
        result = self.run_case()
        self.assertEqual(result.state, "CONTEXT_READY")
        self.assertNotIn("old-only-message", self.queries[0])
        self.assertEqual([m.historical_incident.historical_incident_id for m in result.context.historical_incident_matches], ["HIST-V2-001"])
        self.assertEqual(len(result.context.historical_incidents), 2)
        self.assertEqual(len(result.context.logs.entries), 3)
        self.assertEqual([e.model_dump() for e in result.context.applicable_log_entries], [current])

    def test_old_only_logs_stop_before_history_and_documents(self):
        self.evidence["logs"]["entries"][0]["timestamp"] = "2026-11-03T10:02:00Z"
        result = self.run_case()
        self.assertEqual(result.state, "LOGS_OUTSIDE_WINDOW")
        self.assert_no_documents()
        self.assertEqual(result.evidence.logs.entries[0].timestamp, "2026-11-03T10:02:00Z")
        self.assertIn("2026-11-04T10:00:00Z", result.requested_data[0])

    def test_empty_and_blank_logs_no_message_not_document_abstention(self):
        for entries in ([], [{**self.evidence["logs"]["entries"][0], "message": " \n"}]):
            with self.subTest(entries=entries):
                self.evidence["logs"]["entries"] = entries
                self.assertEqual(self.run_case().state, "NO_LOG_MESSAGE")
                self.assert_no_documents()

    def test_old_metrics_retained_and_requested_without_documents(self):
        original = snapshot(3)
        result = self.run_case(original)
        self.assertEqual(result.state, "MONITORING_OUTSIDE_WINDOW")
        self.assertEqual(result.evidence.model_dump(), original)
        self.assertEqual(result.temporal_assessment.monitoring_applicability, "outside_window")
        self.assert_no_documents()

    def test_all_evidence_and_metadata_survive_package_serialization(self):
        original = deepcopy(self.evidence)
        result = self.run_case()
        self.assertEqual(result.state, "CONTEXT_READY")
        package = result.package
        self.assertEqual(package.evidence.source_snapshot.model_dump(), original)
        self.assertEqual(package.evidence.incident.model_dump(), original["incident"])
        self.assertEqual(package.evidence.monitoring.model_dump(), original["monitoring"])
        self.assertIs(type(package.evidence.monitoring.latency_p95_ms), int)
        self.assertEqual(package.evidence.logs.model_dump(), original["logs"])
        self.assertEqual(package.evidence.historical_incidents[0].model_dump(), history())
        self.assertEqual(package.audit_event_id, "provided-audit-id")
        from investigation_v2_models import InvestigationPackageV2
        self.assertEqual(InvestigationPackageV2.model_validate_json(package.model_dump_json()).model_dump(), package.model_dump())
        self.assertTrue(all(i.chunk.document_status == "active" for i in package.evidence.documentation))
        self.assertEqual({c.document_version for c in package.evidence.document_limits}, {"1.0"})
        self.assertEqual(self.evidence, original)

    def test_invalid_or_naive_timestamp_is_contract_error_even_with_empty_logs(self):
        for field in ("monitoring", "logs"):
            with self.subTest(field=field):
                value = snapshot()
                if field == "monitoring":
                    value["monitoring"]["timestamp"] = "2026-11-04T10:05:00"
                    value["logs"]["entries"] = []
                else:
                    value["logs"]["entries"][0]["timestamp"] = "bad"
                self.assertEqual(self.run_case(value).state, "CONTRACT_ERROR")
                self.assert_no_documents()

    def test_invalid_window_and_mismatched_snapshot_are_contract_errors(self):
        value = snapshot(); value["incident"]["window_end"] = "2026-11-03T10:00:00Z"
        self.assertEqual(self.run_case(value).state, "CONTRACT_ERROR")
        self.evidence_provider.assert_not_called()
        value = snapshot(); self.evidence = value
        self.evidence_provider.side_effect = lambda: {**value, "incident": {**value["incident"], "summary": "different"}}
        self.assertEqual(self.run_case().state, "CONTRACT_ERROR")

    def test_integrity_error_not_empty_documentation(self):
        self.backend.violate = True
        result = self.run_case()
        self.assertEqual(result.state, "DOCUMENT_INTEGRITY_ERROR")
        self.assertIsNone(result.package)

    def test_no_active_documents_is_controlled_abstention(self):
        with self.documents() as control:
            control.reclassify("A", "1.0", "unconfirmed", "Marina")
        result = self.run_case()
        self.assertEqual(result.state, "NO_DOCUMENTATION")
        self.assertIsNone(result.error)
        self.assertIsNone(result.package)

    def test_missing_limits_is_controlled_abstention(self):
        values = chunks()
        values = [c for c in values if not (c["document_id"] == "A" and c["section"] == "Limites")]
        with DocumentControl(self.temp.name, "runbook_chunks_v2_flow_test", "fake", self.backend) as control:
            control.load(values, [[1., 0.]] * len(values), 2)
        self.assertEqual(self.run_case().state, "MISSING_DOCUMENT_LIMITS")

    def test_blocked_state_and_network_failure_are_errors_not_no_documentation(self):
        self.factory.side_effect = ControlError("blocked")
        self.assertEqual(self.run_case().state, "DOCUMENT_CONTROL_ERROR")
        self.factory.side_effect = OSError("unavailable")
        self.assertEqual(self.run_case().state, "OPERATIONAL_ERROR")


if __name__ == "__main__":
    unittest.main()
