from copy import deepcopy
from pathlib import Path
import json
import multiprocessing
import tempfile
import unittest
from unittest.mock import Mock

from document_policy import DocumentIntegrityError
from document_collection import ControlError, DocumentControl, QdrantBackend
import test_llm_input_package as package_fixtures


def try_lock(path, output):
    try:
        with DocumentControl(path,'runbook_chunks_v2_test','fake',None):
            output.put('acquired')
    except ControlError:
        output.put('locked')


class FakeBackend:
    def __init__(self):
        self.chunks=[]
        self.present=False
        self.fail=False
        self.violate=False
        self.last_filter=None
    def exists(self):return self.present
    def create(self,dimensions):self.present=True
    def upsert(self,chunks,vectors):self.chunks=deepcopy(chunks)
    def all(self):return deepcopy(self.chunks)
    def classify(self,record):
        for c in self.chunks:
            if c['chunk_id'] in record.chunk_ids:
                c.update(document_status=record.document_status,classification_revision=record.classification_revision,classified_by=record.classified_by)
                if self.fail:raise RuntimeError('interrupted')
    def search(self,vector,active,limit,threshold):
        self.last_filter=(active,limit,threshold)
        allowed={(r.document_id,r.document_version) for r in active}
        ranked=sorted(self.chunks,key=lambda c:0 if c['document_id']=='B' else 1)
        if not self.violate:
            ranked=[c for c in ranked if (c['document_id'],c['document_version']) in allowed and c['document_status']=='active']
        return [dict(score=0.99 if c['document_id']=='B' else 0.8,chunk=deepcopy(c)) for c in ranked[:limit]]


def chunks():
    return [dict(chunk_id=f'{doc}-{i}',document_id=doc,source='synthetic-test',section=section,
        subsection=None,content='provided content',document_version='1.0',
        document_status=status,classification_revision=1,classified_by='Marina',review_date=None)
        for doc,status in [('A','active'),('B','unconfirmed')] for i,section in enumerate(['Verificações','Limites'])]


class DocumentControlTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/var/tmp')
        self.backend=FakeBackend()
        self.ctl=DocumentControl(self.tmp.name,'runbook_chunks_v2_test','fake',self.backend)
        self.ctl.__enter__()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.ctl.__exit__)
        self.ctl.load(chunks(),[[1.,0.]]*4,2)
    def context(self):
        fixture=package_fixtures.LLMInputPackageTest()
        fixture.setUp()
        data=deepcopy(fixture.context)
        data['documentation']=self.ctl.search([1.,0.])
        data['document_limits']=self.ctl.limits('A','1.0')
        return data
    def test_filter_precedes_top_three_and_high_score_ineligible_never_enters(self):
        result=self.ctl.search([1.,0.])
        self.assertEqual(len(result),2)
        self.assertTrue(all(i['chunk']['document_id']=='A' for i in result))
        self.assertEqual(self.backend.last_filter[1:],(3,0.50))
    def test_package_preserves_classification_and_original_audit_id(self):
        data=self.context();package=self.ctl.package(data)
        self.assertEqual(package.audit_event_id,data['audit_event_id'])
        self.assertEqual([i.model_dump() for i in package.evidence.documentation],data['documentation'])
        self.assertEqual([c.model_dump() for c in package.evidence.document_limits],data['document_limits'])
        from document_policy import ClassifiedPackage
        self.assertEqual(ClassifiedPackage.model_validate_json(package.model_dump_json()).model_dump(),package.model_dump())
        self.assertEqual(package.evidence.documentation[0].chunk.document_version,'1.0')
        self.assertEqual(package.evidence.document_limits[0].document_status,'active')
    def test_payload_after_filter_is_error_not_silent_drop(self):
        self.backend.violate=True
        with self.assertRaises(DocumentIntegrityError):self.ctl.search([1.,0.])
    def test_missing_or_unknown_status_blocks_all_operations(self):
        for value in (None,'unknown'):
            with self.subTest(value=value):
                saved=deepcopy(self.backend.chunks)
                if value is None:self.backend.chunks[-1].pop('document_status')
                else:self.backend.chunks[-1]['document_status']=value
                with self.assertRaises(DocumentIntegrityError):self.ctl.search([1.,0.])
                self.backend.chunks=saved
    def test_content_tampering_is_error(self):
        self.backend.chunks[0]['content']='modified'
        with self.assertRaises(DocumentIntegrityError):self.ctl.limits('A','1.0')
    def test_extra_or_missing_chunk_is_error(self):
        self.backend.chunks.pop()
        with self.assertRaises(DocumentIntegrityError):self.ctl.search([1.,0.])
    def test_deprecation_updates_all_chunks_including_limits_and_rejects_old_context(self):
        data=self.context()
        self.ctl.reclassify('A','1.0','deprecated','Marina')
        self.assertEqual({c['document_status'] for c in self.backend.chunks if c['document_id']=='A'},{'deprecated'})
        self.assertEqual(self.ctl.search([1.,0.]),[])
        self.assertEqual(self.ctl.limits('A','1.0'),[])
        with self.assertRaises(DocumentIntegrityError):self.ctl.package(data)
    def test_interrupted_reclassification_persists_across_restart_and_requires_reconcile(self):
        self.backend.fail=True
        with self.assertRaises(RuntimeError):self.ctl.reclassify('A','1.0','deprecated','Marina')
        self.ctl.__exit__()
        with DocumentControl(self.tmp.name,'runbook_chunks_v2_test','fake',self.backend) as restarted:
            for op in (lambda:restarted.search([1.,0.]),lambda:restarted.limits('A','1.0'),lambda:restarted.package({})):
                with self.assertRaises(ControlError):op()
            self.backend.fail=False
            restarted.reconcile()
            self.assertEqual(restarted.search([1.,0.]),[])
    def test_exclusivity_across_processes(self):
        ctx=multiprocessing.get_context('fork')
        queue=ctx.Queue();p=ctx.Process(target=try_lock,args=(self.tmp.name,queue));p.start();p.join(5)
        if p.is_alive():p.terminate();p.join();self.fail('Process hanging')
        self.assertEqual(queue.get(timeout=2),'locked')
    def test_no_state_no_binding_no_official_collection(self):
        with self.assertRaises(ControlError):DocumentControl(self.tmp.name,'runbook_chunks','fake',self.backend)
        self.ctl.path.unlink()
        with self.assertRaises(ControlError):self.ctl.search([1.,0.])
    def test_context_limits_must_match_version(self):
        data=self.context();data['document_limits'][0]['document_version']='2.0'
        with self.assertRaises(DocumentIntegrityError):self.ctl.package(data)
    def test_controlled_abstention_no_eligible_document(self):
        data=self.context();self.ctl.reclassify('A','1.0','unconfirmed','Marina')
        from context_rules import evaluate_context
        data.update(documentation=[],document_limits=[],documentation_status='no_matches',**evaluate_context([],[]))
        self.assertEqual(self.ctl.package(data).status,'not_eligible')
    def test_p1_remains_not_eligible(self):
        data={'status':'manual_escalation_required','audit_event_id':'provided',
              'incident':dict(incident_id='P1',application='checkout',priority='P1',summary='test'), 'reason':'human'}
        self.assertEqual(self.ctl.package(data).reason_code,'P1')
    def test_load_refuses_overwrite(self):
        with self.assertRaises(ControlError):self.ctl.load(chunks(),[[1.,0.]]*4,2)
    def test_interrupted_load_stays_blocked_after_restart(self):
        with tempfile.TemporaryDirectory(dir='/var/tmp') as d:
            backend=FakeBackend()
            original=backend.upsert
            def broken(values,vectors):
                original(values[:1],vectors[:1])
                raise RuntimeError('load interrupted')
            backend.upsert=broken
            with DocumentControl(d,'runbook_chunks_v2_load','fake',backend) as ctl:
                with self.assertRaises(RuntimeError):ctl.load(chunks(),[[1.,0.]]*4,2)
            with DocumentControl(d,'runbook_chunks_v2_load','fake',backend) as ctl:
                with self.assertRaises(ControlError):ctl.search([1.,0.])
                with self.assertRaises(ControlError):ctl.reconcile()
    def test_state_binding_and_corruption_block_operations(self):
        state=json.loads(self.ctl.path.read_text())
        state['endpoint']='other'
        self.ctl.path.write_text(json.dumps(state))
        with self.assertRaises(ControlError):self.ctl.search([1.,0.])
        self.ctl.path.write_text('{invalid')
        with self.assertRaises(ControlError):self.ctl.limits('A','1.0')
    def test_reconcile_does_not_repair_unknown_content_or_classification(self):
        self.backend.fail=True
        with self.assertRaises(RuntimeError):self.ctl.reclassify('A','1.0','deprecated','Marina')
        self.backend.fail=False
        self.backend.chunks[0]['document_status']='unknown'
        with self.assertRaises(DocumentIntegrityError):self.ctl.reconcile()
        with self.assertRaises(ControlError):self.ctl.search([1.,0.])
    def test_unknown_requested_status_does_not_change_state(self):
        before=self.ctl.path.read_bytes()
        with self.assertRaises(ValueError):self.ctl.reclassify('A','1.0','unknown','Marina')
        self.assertEqual(self.ctl.path.read_bytes(),before)
    def test_missing_logs_response_does_not_build_package(self):
        data={'status':'additional_data_required','analysis_code':'NO_LOG_MESSAGE',
              'audit_event_id':'provided','incident':dict(incident_id='x',application='checkout',priority='P2',summary='test'),
              'reason':'missing','requested_data':['message']}
        self.assertEqual(self.ctl.package(data).reason_code,'NO_LOG_MESSAGE')
    def test_backend_filter_shape_before_limit(self):
        adapter=QdrantBackend.__new__(QdrantBackend)
        adapter.collection='runbook_chunks_v2_test'
        adapter.client=Mock();adapter.client.query_points.return_value.points=[]
        records=self.ctl.read()[1]
        adapter.search([1.,0.],[records[0]],3,0.50)
        args=adapter.client.query_points.call_args.kwargs
        conditions=args['query_filter'].should[0].must
        self.assertEqual({c.key:c.match.value for c in conditions},dict(document_id='A',document_version='1.0',document_status='active',classification_revision=1))
        self.assertEqual(args['limit'],3)
        self.assertEqual(args['score_threshold'],0.50)


if __name__=='__main__':unittest.main()
