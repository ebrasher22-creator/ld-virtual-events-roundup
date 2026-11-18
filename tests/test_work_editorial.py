import copy
from datetime import date
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pipeline import ROOT, read, write, ingest, assign, generate
from record_attestation import record
from editorial_input import build_input, export_input
from validate_work_caption import validate_submission
from validate_editorial_drafts import validate_files


class WorkEditorialTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for directory in ['config','templates']:shutil.copytree(ROOT/directory,self.root/directory)
        statement='Synthetic owner approves the synthetic fixture for editorial inclusion.'
        source=self.root/'approvals/test.md'
        source.parent.mkdir()
        source.write_text(statement)
        write(self.root/'data/canonical-events.json',[])
        write(self.root/'data/reviews.json',{})
        self.raw=read(ROOT/'tests/fixtures/chatgpt.json')[0]
        self.raw['registration_url']='https://example.org/register/transfer/'
        write(self.root/'intake/chatgpt/test.json',[self.raw])
        ingest(self.root)
        events=assign(self.root,date(2026,11,24))
        record(self.root,[e['event_id'] for e in events],'Synthetic owner','approvals/test.md',statement,recorded_at='2026-11-18T20:00:00Z',select=True)
        self.input_path=export_input(self.root,date(2026,11,24))
        self.payload=read(self.input_path)
        text='What question would you like to explore?\n\n'+self.payload['required_heading']+'\n\n'+self.payload['events'][0]['required_fact_block']+'\n\nShare another worthwhile opportunity with the community.\n'
        self.draft=dict(format_version=1,roundup_identifier=self.payload['roundup_identifier'],editorial_input_sha256=self.payload['editorial_input_sha256'],full_caption=text,compact_caption=text)
        self.draft_path=self.root/'editorial-drafts/test.json'
        self.output=self.root/'work-output'

    def validate(self,draft=None):
        write(self.draft_path,draft if draft is not None else self.draft)
        return validate_submission(self.root,self.input_path,self.draft_path,self.output)

    def test_valid_exchange_and_original_url_preservation(self):
        event=self.payload['events'][0]
        self.assertEqual(event['registration_url'],self.raw['registration_url'])
        self.assertTrue(event['canonical_registration_url'].endswith('/transfer'))
        self.assertTrue(self.validate()['mechanical_validation_passed'])
        self.assertTrue((self.output/'linkedin-work-post.md').is_file())
        self.assertEqual(read(self.output/'validation-report.json')['publication_approval_status'],'awaiting_final_human_review')

    def test_only_approved_target_week_members_are_exported(self):
        events=read(self.root/'data/canonical-events.json')
        for event_id,when in [('future','2026-12-08T12:00:00-06:00'),('pending','2026-12-02T12:00:00-06:00')]:
            e=copy.deepcopy(events[0]);e.update(event_id=event_id,start_datetime=when,title=event_id,verification_status='pending')
            events.append(e)
        write(self.root/'data/canonical-events.json',events)
        assign(self.root,date(2026,11,24))
        payload=build_input(self.root,date(2026,11,24))
        self.assertEqual(len(payload['events']),1)
        self.assertEqual(payload['events'][0]['title'],self.raw['title'])

    def test_no_generation_timestamp_churn_in_editorial_input(self):
        self.assertEqual(self.payload,build_input(self.root,date(2026,11,24)))
        generate(self.root,date(2026,11,24),generated_at='2026-11-18T20:00:00Z')
        self.assertEqual(self.payload,read(self.input_path))

    def test_reject_changed_event_facts_links_and_length(self):
        event=self.payload['events'][0]
        replacements=[(event['title'],'Different title'),(event['organizer'],'Different host'),('Dec 1, 2026','Dec 2, 2026'),('12:00 PM CST','1:00 PM CST'),('CST','EST'),(event['registration_url'],'https://example.org/fake/')]
        for old,new in replacements:
            draft=copy.deepcopy(self.draft)
            draft['full_caption']=draft['full_caption'].replace(old,new)
            with self.subTest(old=old):self.assertFalse(self.validate(draft)['mechanical_validation_passed'])
        draft=copy.deepcopy(self.draft);draft['compact_caption']+='x'*3000
        self.assertFalse(self.validate(draft)['mechanical_validation_passed'])

    def test_reject_missing_duplicate_and_extra_event_assertions(self):
        for replacement in ['',self.payload['events'][0]['required_fact_block']+'\n\n'+self.payload['events'][0]['required_fact_block']]:
            draft=copy.deepcopy(self.draft)
            draft['full_caption']=draft['full_caption'].replace(self.payload['events'][0]['required_fact_block'],replacement)
            self.assertFalse(self.validate(draft)['mechanical_validation_passed'])
        for extra in ['More: https://example.org/unapproved','Another session: Wednesday at 3 PM EST','These are free sessions.']:
            draft=copy.deepcopy(self.draft);draft['full_caption']+='\n\n'+extra
            with self.subTest(extra=extra):self.assertFalse(self.validate(draft)['mechanical_validation_passed'])

    def test_reject_week_hash_input_tampering_and_stale_approval(self):
        for key,value in [('roundup_identifier','2026/RW50_2026-12-06_to_2026-12-12'),('editorial_input_sha256','fake')]:
            draft=copy.deepcopy(self.draft);draft[key]=value
            self.assertFalse(self.validate(draft)['mechanical_validation_passed'])
        payload=copy.deepcopy(self.payload);payload['events'][0]['summary']='Changed after approval'
        write(self.input_path,payload)
        self.assertFalse(self.validate()['mechanical_validation_passed'])
        write(self.input_path,self.payload)
        events=read(self.root/'data/canonical-events.json');events[0]['organizer']='Changed organizer'
        write(self.root/'data/canonical-events.json',events)
        self.assertFalse(self.validate()['mechanical_validation_passed'])

    def test_failed_resubmission_removes_old_passing_caption(self):
        self.assertTrue(self.validate()['mechanical_validation_passed'])
        self.draft['full_caption']='Bad draft'
        self.assertFalse(self.validate()['mechanical_validation_passed'])
        self.assertFalse((self.output/'linkedin-work-post.md').exists())

    def test_invalid_json_and_wrong_shapes_report_fail_without_execution(self):
        self.draft_path.parent.mkdir(parents=True,exist_ok=True)
        for value in ['not json','[]','{"full_caption": 3}']:
            self.draft_path.write_text(value)
            result=validate_submission(self.root,self.input_path,self.draft_path,self.output)
            self.assertFalse(result['mechanical_validation_passed'])
        draft=copy.deepcopy(self.draft);draft['run_shell']='touch unsafe'
        self.assertFalse(self.validate(draft)['mechanical_validation_passed'])
        self.assertFalse((self.root/'unsafe').exists())

    def test_owner_mediated_file_return_scan(self):
        write(self.draft_path,self.draft)
        self.assertTrue(validate_files(self.root))
        self.assertTrue((self.root/'reports/work-editorial/test/validation-report.json').is_file())
        self.draft['compact_caption']='Wrong'
        write(self.draft_path,self.draft)
        self.assertFalse(validate_files(self.root,[self.draft_path]))

    def test_reordered_blocks_and_wrong_preparation_week_fail(self):
        events=read(self.root/'data/canonical-events.json')
        extra=copy.deepcopy(events[0])
        extra.update(event_id='second-event',title='Second approved synthetic event',start_datetime='2026-12-02T12:00:00-06:00',registration_url='https://example.org/second',submissions=[])
        events.append(extra)
        write(self.root/'data/canonical-events.json',events)
        record(self.root,[extra['event_id']],'Synthetic owner','approvals/test.md','Synthetic owner approves the synthetic fixture for editorial inclusion.',recorded_at='2026-11-18T20:00:00Z',select=True)
        self.input_path=export_input(self.root,date(2026,11,24))
        self.payload=read(self.input_path)
        draft=copy.deepcopy(self.draft)
        draft['editorial_input_sha256']=self.payload['editorial_input_sha256']
        draft['full_caption']='A question for the community.\n\n'+self.payload['required_heading']+'\n\n'+'\n\n'.join(e['required_fact_block'] for e in reversed(self.payload['events']))+'\n\nWhat will you explore?'
        draft['compact_caption']=draft['full_caption']
        self.assertFalse(self.validate(draft)['mechanical_validation_passed'])
        write(self.draft_path,self.draft)
        self.assertFalse(validate_files(self.root,[self.draft_path],date(2026,12,1)))

    def test_semantic_review_is_never_claimed_automated(self):
        draft=copy.deepcopy(self.draft)
        # Arbitrary prose cannot be proved true by exact factual-field checks.
        draft['full_caption']='Every attendee will transform their career.\n\n'+draft['full_caption']
        result=self.validate(draft)
        self.assertTrue(result['mechanical_validation_passed'])
        self.assertTrue(result['semantic_review_required'])
        self.assertEqual(result['publication_approval_status'],'awaiting_final_human_review')


if __name__=='__main__':unittest.main()
