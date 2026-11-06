from copy import deepcopy
import unittest
from pydantic import ValidationError
from investigation_v2_models import EvidenceSnapshotV2, InvestigationContextV2
import test_investigation_v2 as fixtures
from test_investigation_v2 import snapshot


class V2ModelsTest(unittest.TestCase):
    def test_imports_do_not_load_api_or_embedding_model(self):
        import subprocess
        import sys
        subprocess.run([sys.executable, '-c',
                        "import sys; import investigation_v2; import investigation_v2_models; "
                        "assert not {'main', 'search_qdrant', 'sentence_transformers'} & set(sys.modules)"],
                       check=True, timeout=10)

    def test_contract_rejects_conversion_and_missing_fields(self):
        for edit in (lambda d: d['monitoring'].update(latency_p95_ms='1800'),
                     lambda d: d['incident'].pop('window_start'),
                     lambda d: d['monitoring'].update(timestamp='2026-11-04T10:05:00')):
            value = snapshot(); edit(value)
            with self.assertRaises(ValidationError):
                EvidenceSnapshotV2.model_validate(value)

    def test_metadata_offsets_and_numeric_types_survive_json(self):
        value = snapshot()
        value['monitoring']['timestamp'] = '2026-11-04T07:05:00-03:00'
        model = EvidenceSnapshotV2.model_validate(value)
        restored = EvidenceSnapshotV2.model_validate_json(model.model_dump_json())
        self.assertEqual(restored.model_dump(), value)
        self.assertIs(type(restored.monitoring.latency_p95_ms), int)

    def test_ready_context_rejects_forged_temporal_and_changed_evidence(self):
        fixture = fixtures.InvestigationV2Test(); fixture.setUp()
        try:
            context = fixture.run_case().context.model_dump()
            for edit in (lambda d: d['temporal_assessment'].update(monitoring_applicability='outside_window'),
                         lambda d: d.update(applicable_log_entries=[]),
                         lambda d: d['logs']['entries'][0].update(message='changed'),
                         lambda d: d.update(historical_incident_matches=[])):
                value = deepcopy(context); edit(value)
                with self.assertRaises(ValidationError):
                    InvestigationContextV2.model_validate(value)
        finally:
            fixture.doCleanups()


if __name__ == '__main__':
    unittest.main()
