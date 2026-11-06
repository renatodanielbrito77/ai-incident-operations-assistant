import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_document_collection import FakeBackend, chunks
from test_investigation_v2 import snapshot, history

EXPERIMENTS = Path(__file__).resolve().parents[1] / 'experiments'
sys.path.insert(0, str(EXPERIMENTS))
spec = importlib.util.spec_from_file_location('investigate_v2_cli', EXPERIMENTS / 'investigate_v2.py')
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
import document_control


class V2CLITest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/var/tmp'); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'incidents').mkdir(); (self.root / 'history').mkdir()
        for case in range(1, 5):
            (self.root / 'incidents' / f'INC-V2-{case:03}.json').write_text(json.dumps(snapshot(case)))
        (self.root / 'history/h.json').write_text(json.dumps(history()))
        self.args = ['--source-dir', str(self.root), '--state-dir', str(self.root/'state'),
                     '--output-dir', str(self.root/'results'), '--controlled-vectors']

    def test_four_paths_serialization_and_separate_collection(self):
        backend = FakeBackend()
        with patch.object(cli, 'QdrantBackend', return_value=backend) as factory, patch.object(document_control, 'prepare', return_value=chunks()) as prepare:
            self.assertEqual(cli.main(self.args), 0)
        factory.assert_called_once_with('http://vector-db:6333', cli.COLLECTION)
        prepare.assert_called_once_with(self.root)
        summary = json.loads((self.root/'results/summary.json').read_text())
        self.assertEqual([c['state'] for c in summary['cases']], ['CONTEXT_READY', 'NO_LOG_MESSAGE', 'MONITORING_OUTSIDE_WINDOW', 'P1_MANUAL_ESCALATION'])
        result = json.loads((self.root/'results/INC-V2-001-result.json').read_text())
        self.assertEqual(result['package']['evidence']['source_snapshot'], snapshot())
        self.assertEqual(result['package']['audit_event_id'], cli.AUDIT_MARKER)

    def test_p1_never_constructs_backend_or_reads_histories(self):
        (self.root/'history/h.json').write_text('invalid json')
        with patch.object(cli, 'QdrantBackend', side_effect=AssertionError('access')) as factory, patch.object(document_control, 'prepare') as prepare:
            self.assertEqual(cli.main(self.args + ['--incident-id', 'INC-V2-004']), 0)
        factory.assert_not_called(); prepare.assert_not_called()
        self.assertFalse((self.root/'state').exists())

    def test_existing_results_not_overwritten(self):
        (self.root/'results').mkdir(); marker = self.root/'results/keep'; marker.write_text('original')
        self.assertEqual(cli.main(self.args), 2)
        self.assertEqual(marker.read_text(), 'original')

    def test_existing_state_not_reused(self):
        (self.root/'state').mkdir()
        with patch.object(cli, 'QdrantBackend') as factory:
            self.assertEqual(cli.main(self.args + ['--incident-id', 'INC-V2-001']), 2)
        factory.assert_not_called()
        value = json.loads((self.root/'results/INC-V2-001-result.json').read_text())
        self.assertEqual(value['state'], 'DOCUMENT_CONTROL_ERROR')

    def test_invalid_contract_is_exit_two_and_no_backend(self):
        value = snapshot(); value['monitoring']['timestamp'] = 'bad'
        (self.root/'incidents/INC-V2-001.json').write_text(json.dumps(value))
        with patch.object(cli, 'QdrantBackend') as factory:
            self.assertEqual(cli.main(self.args + ['--incident-id', 'INC-V2-001']), 2)
        factory.assert_not_called()

    def test_missing_history_directory_is_not_silent_empty_history(self):
        (self.root/'history/h.json').unlink(); (self.root/'history').rmdir()
        with patch.object(cli, 'QdrantBackend') as factory:
            self.assertEqual(cli.main(self.args + ['--incident-id', 'INC-V2-001']), 2)
        factory.assert_not_called()
        result = json.loads((self.root/'results/INC-V2-001-result.json').read_text())
        self.assertEqual(result['state'], 'OPERATIONAL_ERROR')

    def test_existing_collection_is_preserved(self):
        backend = FakeBackend(); backend.present = True; backend.chunks = chunks()
        original = backend.all()
        with patch.object(cli, 'QdrantBackend', return_value=backend), patch.object(document_control, 'prepare', return_value=chunks()):
            self.assertEqual(cli.main(self.args + ['--incident-id', 'INC-V2-001']), 2)
        self.assertEqual(backend.all(), original)


if __name__ == '__main__':
    unittest.main()
