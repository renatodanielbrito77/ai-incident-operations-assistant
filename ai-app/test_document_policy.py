import unittest
from copy import deepcopy
from pydantic import ValidationError
from document_policy import Classification, ClassifiedChunk, DocumentIntegrityError, eligible, payload_hash


class DocumentPolicyTest(unittest.TestCase):
    def setUp(self):
        self.chunk=dict(chunk_id='c',document_id='d',source='synthetic',section='Limites',content='text',subsection=None,
            document_version='1',document_status='active',classification_revision=1,classified_by='Marina',review_date=None)
        self.record=Classification(document_id='d',document_version='1',document_status='active',
            classification_revision=1,classified_by='Marina',chunk_ids=['c'],payload_hashes={'c':payload_hash(self.chunk)})
    def test_each_consistent_status_and_no_input_mutation(self):
        for status in ('active','deprecated','unconfirmed'):
            c={**self.chunk,'document_status':status}
            r=Classification.model_validate({**self.record.model_dump(),'document_status':status})
            original=deepcopy(c)
            self.assertEqual(eligible(c,[r]),status=='active');self.assertEqual(c,original)
    def test_classification_disagreement_is_error(self):
        with self.assertRaises(DocumentIntegrityError):eligible({**self.chunk,'document_status':'deprecated'},[self.record])
    def test_missing_status_is_error_even_with_new_review_date(self):
        c=dict(self.chunk);c.pop('document_status');c['review_date']='2099-01-01'
        with self.assertRaises(DocumentIntegrityError):eligible(c,[self.record])
    def test_old_date_does_not_deprecate(self):
        c={**self.chunk,'review_date':'1900-01-01'}
        r=Classification.model_validate({**self.record.model_dump(),'payload_hashes':{'c':payload_hash(c)}})
        self.assertTrue(eligible(c,[r]))
    def test_no_default_for_version_or_status(self):
        for key in ('document_version','document_status','classified_by'):
            c=dict(self.chunk);c.pop(key)
            with self.assertRaises(ValidationError):ClassifiedChunk.model_validate(c)


if __name__=='__main__':unittest.main()
