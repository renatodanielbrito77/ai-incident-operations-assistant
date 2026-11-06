import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_document_collection import FakeBackend, chunks

spec=importlib.util.spec_from_file_location('document_control_cli',Path(__file__).resolve().parents[1]/'experiments/document_control.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)


class DocumentCLITest(unittest.TestCase):
    def test_validation_uses_only_two_separate_collections_and_no_model(self):
        # Remplace source input only: no external lot, model, audit or services.
        from test_llm_input_package import LLMInputPackageTest
        import json
        with tempfile.TemporaryDirectory(dir='/var/tmp') as d:
            root=Path(d);(root/'incidents').mkdir()
            fixture=LLMInputPackageTest();fixture.setUp()
            data={k:fixture.context[k] for k in ('incident','monitoring','logs')}
            (root/'incidents/INC-V2-001.json').write_text(json.dumps(data))
            values=chunks()
            for c in values:c['document_id']='RB-V2-001' if c['document_id']=='A' else 'RB-V2-002'
            backends={}
            def factory(url,name):
                self.assertEqual(url,'http://vector-db:6333')
                backends[name]=FakeBackend();return backends[name]
            with patch.object(cli,'prepare',return_value=values),patch.object(cli,'QdrantBackend',side_effect=factory):
                code=cli.main(['validate','--source-dir',str(root),'--state-dir',str(root/'state'),'--output-dir',str(root/'results')])
            self.assertEqual(code,0)
            self.assertEqual(set(backends),set(cli.VALIDATION_COLLECTIONS))
            report=json.loads((root/'results/validation.json').read_text())
            self.assertTrue(report['collections'][1]['old_context_rejected'])
    def test_preparation_preserves_text_and_explicit_classifications(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory(dir='/var/tmp') as d:
            root=Path(d);(root/'procedures').mkdir()
            files=[]
            for doc in ('RB-V2-001','RB-V2-002'):
                p=root/'procedures'/f'{doc}.md'
                p.write_text('# Original title\n\n## Verificações\n  original spacing  \n\n## Limites\nOriginal limits.\n')
                files.append(dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
            manifest=json.dumps({'files':files}).encode()
            (root/'manifest.json').write_bytes(manifest)
            with patch.object(cli,'APPROVED_MANIFEST_SHA256',hashlib.sha256(manifest).hexdigest()):
                prepared=cli.prepare(root)
            for doc in ('RB-V2-001','RB-V2-002'):
                selected=[c for c in prepared if c['document_id']==doc]
                self.assertEqual(''.join(c['content'] for c in selected),(root/'procedures'/f'{doc}.md').read_text())
                self.assertEqual({c['document_status'] for c in selected},{'active' if doc=='RB-V2-001' else 'unconfirmed'})
                self.assertEqual(sum(c['section']=='Limites' for c in selected),1)
            self.assertEqual(len({c['chunk_id'] for c in prepared}),len(prepared))
    def test_unapproved_manifest_is_error_before_backend(self):
        with tempfile.TemporaryDirectory(dir='/var/tmp') as d:
            root=Path(d);(root/'manifest.json').write_text('{}')
            with self.assertRaises(cli.ControlError):cli.prepare(root)
    def test_error_is_recorded_and_not_repaired(self):
        with tempfile.TemporaryDirectory(dir='/var/tmp') as d:
            out=Path(d)/'results'
            with patch.object(cli,'prepare',side_effect=ValueError('bad source')):
                code=cli.main(['validate','--source-dir',d,'--state-dir',str(Path(d)/'state'),'--output-dir',str(out)])
            self.assertEqual(code,2);self.assertTrue((out/'error.json').exists())
    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory(dir='/var/tmp') as d:
            self.assertEqual(cli.main(['validate','--state-dir',d,'--output-dir',d]),2)


if __name__=='__main__':unittest.main()
