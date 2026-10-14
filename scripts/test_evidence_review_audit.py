"""Boundary tests for enrichment review; fixtures do not enter the research database."""
import importlib.util
import json
import tempfile
import unittest
import hashlib
from pathlib import Path

spec = importlib.util.spec_from_file_location('review_audit', Path(__file__).with_name('audit_evidence_enrichment.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReviewBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        (self.root / 'test.pdf').write_bytes(b'test fixture, not research evidence')
        sha = hashlib.sha256((self.root / 'test.pdf').read_bytes()).hexdigest()
        self.row = {'candidate_id':'TEST-1','asset_code':'RS-DT-SPILLWAY','kind':'INSPECTION',
                    'sha256':sha,'drive_file_id':'test-id','source_locator':'PDF:p1:test',
                    'source_code':'RS-SRC-TEST','attribute_key':'','label':'Test observation',
                    'value':'fixture only','unit':'','decision':'VERIFIED',
                    'mapping_verified':'true','source_eligibility':'ELIGIBLE',
                    'temporal_precision':'FULL_DATE','as_of_date_or_period':'2024-05-15',
                    'completion_status':'VERIFIED','source_state':'DATED_OBSERVATION'}
        self.register = {'files':[{'sha256':sha,'path':'test.pdf','drive_file_id':'test-id','pages':1}]}
        self.approval = {'decision':'APPROVED','reviewer_role':'DOMAIN_EXPERT',
                         'reviewer_name':'Fixture human','reviewer_is_ai':False,
                         'reviewed_at':'2026-10-14T12:00:00+07:00',
                         'binding':{k:self.row[k] for k in ['candidate_id','asset_code','sha256','source_locator','attribute_key','value','unit']}}

    def audit(self, approval=None):
        return module.audit([self.row],self.register,self.root,[],[{'source_code':'RS-SRC-TEST'}],
                            {'TEST-1':approval or self.approval})['candidates'][0]

    def test_ai_label_cannot_satisfy_human_review(self):
        self.approval.update(reviewer_role='AI_METHOD_REVIEWER',reviewer_is_ai=True)
        self.assertIn('HUMAN_DOMAIN_APPROVAL_REQUIRED',self.audit()['blockers'])

    def test_review_does_not_survive_source_or_value_changes(self):
        self.row['value']='changed fixture'
        self.assertIn('REVIEW_BINDING_MISMATCH:value',self.audit()['blockers'])
        (self.root/'test.pdf').write_bytes(b'changed bytes')
        self.assertIn('SOURCE_BYTES_MISMATCH',self.audit()['blockers'])

    def test_procedure_cannot_become_verified_event(self):
        self.row['source_state']='PROCEDURE_ONLY'
        self.assertIn('PROCEDURE_OR_DESIGN_IS_NOT_AN_EVENT',self.audit()['blockers'])
        self.row['source_state']='DATED_OBSERVATION'
        self.row['temporal_precision']='YEAR_ONLY'
        self.assertIn('FULL_DATE_REQUIRED',self.audit()['blockers'])

    def test_exact_declaration_can_only_reach_existing_compiler(self):
        self.assertTrue(self.audit()['eligible_for_compiler'])
        self.row['mapping_verified']='false'
        self.assertIn('ASSET_IDENTITY_UNRESOLVED',self.audit()['blockers'])

    def test_researcher_approval_is_limited_to_optional_reported_l2(self):
        self.row['kind'] = 'TECHNICAL'
        self.approval.update(reviewer_role='RESEARCHER', approval_scope='OPTIONAL_REPORTED_TECHNICAL_L2', verification_level='L2')
        rule = {'category_code':'RS-CAT-SPILLWAY','attribute_key':'','attribute_label':'Test observation','expected_unit':'','required_by_maim':'false'}
        def result():
            return module.audit([self.row], self.register, self.root, [rule], [{'source_code':'RS-SRC-TEST'}], {'TEST-1':self.approval})['candidates'][0]
        self.assertTrue(result()['eligible_for_compiler'])
        rule['required_by_maim'] = 'true'
        self.assertIn('HUMAN_DOMAIN_APPROVAL_REQUIRED', result()['blockers'])
        rule['required_by_maim'] = 'false'
        self.approval['verification_level'] = 'L3'
        self.assertIn('HUMAN_DOMAIN_APPROVAL_REQUIRED', result()['blockers'])
        self.approval['verification_level'] = 'L2'
        self.row['kind'] = 'INSPECTION'
        self.assertIn('HUMAN_DOMAIN_APPROVAL_REQUIRED', result()['blockers'])

if __name__ == '__main__':
    unittest.main()
