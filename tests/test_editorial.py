import copy
from datetime import date, datetime
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pipeline import (ROOT, read, write, ingest, assign, generate, eligible, fingerprint,
                      confirmed_price_label, CLAIMS)
from record_attestation import record
from prepare_wednesday import is_wednesday_slot, prepare
from validate_post import validate_output


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for directory in ['config','templates']: shutil.copytree(ROOT/directory,self.root/directory)
        self.source=self.root/'approvals/test-owner.md'
        self.source.parent.mkdir()
        self.statement='Synthetic test owner approves these synthetic events for inclusion.'
        self.source.write_text(self.statement)
        write(self.root/'data/canonical-events.json',[])
        write(self.root/'data/reviews.json',{})
        self.raw=read(ROOT/'tests/fixtures/chatgpt.json')[0]
        write(self.root/'intake/chatgpt/test.json',[self.raw])
        ingest(self.root)
        self.events=assign(self.root,date(2026,11,24))
        self.e=self.events[0]
        self.approve()

    def approve(self):
        events=read(self.root/'data/canonical-events.json')
        return record(self.root,[e['event_id'] for e in events],'Synthetic test owner','approvals/test-owner.md',self.statement,recorded_at='2026-11-18T20:00:00Z',select=True)

    def test_explicit_owner_attestation_has_no_invented_observations_or_check_time(self):
        e=read(self.root/'data/canonical-events.json')[0]
        reviews=read(self.root/'data/reviews.json')
        review=reviews[e['event_id']]
        self.assertTrue(eligible(e,reviews,self.root))
        self.assertEqual(review['claims'],{})
        self.assertIsNone(review['verified_at'])
        self.assertIsNone(e['last_verified_at'])
        self.assertEqual(review['attestation']['recorded_at'],'2026-11-18T20:00:00Z')

    def test_unknown_pricing_stays_eligible_without_price_claim(self):
        events=read(self.root/'data/canonical-events.json')
        events[0]['price_type']='unknown'
        write(self.root/'data/canonical-events.json',events)
        self.approve()
        folder=generate(self.root,date(2026,11,24))
        report=read(folder/'editorial-report.json')
        text=(folder/'linkedin-post.md').read_text()
        self.assertEqual(len(report['events_included']),1)
        self.assertNotIn('Free',text)
        self.assertNotIn('Paid',text)
        self.assertNotIn('unknown',text)
        self.assertEqual(read(self.root/'data/canonical-events.json')[0]['price_type'],'unknown')
        self.assertEqual(len(report['missing_optional_pricing']),1)

    def test_known_but_unconfirmed_price_is_not_advertised_or_changed(self):
        folder=generate(self.root,date(2026,11,24))
        self.assertNotIn('| Free',(folder/'linkedin-post.md').read_text())
        self.assertEqual(read(self.root/'data/canonical-events.json')[0]['price_type'],'free')

    def test_confirmed_free_and_paid_labels(self):
        for kind in ['free','paid']:
            with self.subTest(kind=kind):
                events=read(self.root/'data/canonical-events.json')
                events[0]['price_type']=kind
                write(self.root/'data/canonical-events.json',events)
                reviews=self.approve()
                reviews[events[0]['event_id']]['claims']['price']={'primary_url':self.raw['event_url'],'observation':'Synthetic independent price confirmation'}
                write(self.root/'data/reviews.json',reviews)
                folder=generate(self.root,date(2026,11,24))
                self.assertIn('| '+kind.title(),(folder/'linkedin-post.md').read_text())

    def test_legacy_observations_without_optional_price_claim(self):
        e=read(self.root/'data/canonical-events.json')[0]
        review=dict(record_sha256=fingerprint(e),decision='verified',editorial_decision='selected',reviewer='Synthetic human',verified_at='2026-11-18T20:00:00Z',claims={k:dict(primary_url=e['event_url'],observation='Synthetic independently recorded observation') for k in CLAIMS-{'price'}})
        self.assertTrue(eligible(e,{e['event_id']:review},self.root))
        review['claims'].pop('datetime')
        self.assertFalse(eligible(e,{e['event_id']:review},self.root))

    def test_record_or_source_change_invalidates_approval(self):
        e=read(self.root/'data/canonical-events.json')[0]
        reviews=read(self.root/'data/reviews.json')
        for field,value in [('title','Changed title'),('registration_url','https://example.org/changed'),('start_datetime','2026-12-02T12:00:00-06:00'),('price_type','unknown')]:
            with self.subTest(field=field):self.assertFalse(eligible(dict(e,**{field:value}),reviews,self.root))
        self.source.write_text(self.statement+' changed')
        self.assertFalse(eligible(e,reviews,self.root))

    def test_incomplete_or_fake_attestation_cannot_approve(self):
        e=read(self.root/'data/canonical-events.json')[0]
        reviews=read(self.root/'data/reviews.json')
        for key,value in [('authority','assistant'),('covered_claims',[]),('statement','Not in the supplied source'),('source_path','../outside.md')]:
            modified=copy.deepcopy(reviews)
            modified[e['event_id']]['attestation'][key]=value
            with self.subTest(key=key): self.assertFalse(eligible(e,modified,self.root))
        modified=copy.deepcopy(reviews)
        modified[e['event_id']]['editorial_decision']='pending'
        self.assertFalse(eligible(e,modified,self.root))

    def test_future_week_is_excluded_and_remains_available(self):
        events=read(self.root/'data/canonical-events.json')
        future=copy.deepcopy(events[0])
        future.update(event_id='future-test',start_datetime='2026-12-08T12:00:00-06:00',title='Synthetic future event',registration_url='https://example.org/future',roundup_week='2026/RW50_2026-12-06_to_2026-12-12')
        events.append(future)
        write(self.root/'data/canonical-events.json',events)
        self.approve()
        folder=prepare(self.root,date(2026,11,24))
        report=read(folder/'editorial-report.json')
        self.assertEqual(len(report['events_included']),1)
        self.assertEqual(report['events_excluded'][0]['reason'],'outside_target_week')
        self.assertEqual(len(read(self.root/'data/future-events.json')),1)
        later=generate(self.root,date(2026,12,1))
        self.assertIn('Synthetic future event',(later/'linkedin-post.md').read_text())

    def test_above_target_does_not_silently_cap_collection(self):
        baseline=read(self.root/'data/canonical-events.json')[0]
        events=[]
        for index in range(13):
            e=copy.deepcopy(baseline)
            e.update(event_id=f'event-{index}',title=f'Event {index}',organizer='Host',registration_url=f'https://example.org/{index}')
            events.append(e)
        write(self.root/'data/canonical-events.json',events)
        self.approve()
        folder=generate(self.root,date(2026,11,24))
        report=read(folder/'editorial-report.json')
        self.assertEqual(len(report['events_included']),13)
        self.assertTrue(report['above_target'])

    def test_overflow_writes_explicit_exception_and_preserves_all_events(self):
        rules=read(self.root/'config/editorial-rules.yml')
        rules['linkedin_max_characters']=50
        write(self.root/'config/editorial-rules.yml',rules)
        with self.assertRaises(ValueError):generate(self.root,date(2026,11,24))
        folder=self.root/'weeks/2026/RW49_2026-11-29_to_2026-12-05'
        report=read(folder/'editorial-report.json')
        self.assertEqual(len(report['events_included']),1)
        self.assertFalse(report['within_character_limit'])
        self.assertTrue(report['editorial_exceptions'])
        self.assertIn(self.raw['title'],(folder/'linkedin-post.md').read_text())

    def test_shorten_optional_text_before_dropping_essential_details(self):
        brand=read(self.root/'config/branding.yml')
        brand['introduction']='Long introductory text '*300
        write(self.root/'config/branding.yml',brand)
        folder=generate(self.root,date(2026,11,24))
        report=read(folder/'editorial-report.json')
        self.assertTrue(report['within_character_limit'])
        self.assertEqual(report['caption_strategy'],'shortened_introduction')
        self.assertIn(self.raw['registration_url'],(folder/'linkedin-post.md').read_text())

    def test_repeat_execution_stable_except_declared_timestamp(self):
        folder=generate(self.root,date(2026,11,24),generated_at='2026-11-18T20:00:00Z')
        full=(folder/'linkedin-post.md').read_bytes()
        compact=(folder/'linkedin-post-compact.md').read_bytes()
        first=read(folder/'editorial-report.json')
        generate(self.root,date(2026,11,24),generated_at='2026-11-18T20:00:01Z')
        second=read(folder/'editorial-report.json')
        self.assertEqual(full,(folder/'linkedin-post.md').read_bytes())
        self.assertEqual(compact,(folder/'linkedin-post-compact.md').read_bytes())
        self.assertNotEqual(first.pop('generated_at'),second.pop('generated_at'))
        self.assertEqual(first,second)
        self.assertTrue(read(folder/'review.json')['below_target'])
        validate_output(self.root,date(2026,11,24))

    def test_stale_selected_record_causes_workflow_exception(self):
        events=read(self.root/'data/canonical-events.json')
        events[0]['summary']='Substantively changed after approval'
        write(self.root/'data/canonical-events.json',events)
        with self.assertRaises(ValueError):prepare(self.root,date(2026,11,24))
        report=read(self.root/'weeks/2026/RW49_2026-11-29_to_2026-12-05/editorial-report.json')
        self.assertEqual(report['events_included'],[])
        self.assertEqual(report['approval_blockers'][0]['reason'],'missing_or_stale_approval')

    def test_wednesday_seven_central_guard_handles_dst(self):
        for timestamp,expected in [('2026-11-25T13:00:00+00:00',True),('2026-07-01T12:00:00+00:00',True),('2026-11-25T12:00:00+00:00',False),('2026-07-01T13:00:00+00:00',False),('2026-11-24T13:00:00+00:00',False)]:
            with self.subTest(timestamp=timestamp):self.assertEqual(is_wednesday_slot(datetime.fromisoformat(timestamp)),expected)

    def test_cdt_and_cst_display(self):
        for timestamp,as_of,expected in [('2026-12-01T12:00:00-06:00',date(2026,11,24),'12:00 PM CST'),('2026-07-01T12:00:00-05:00',date(2026,6,24),'12:00 PM CDT')]:
            events=read(self.root/'data/canonical-events.json')
            events[0]['start_datetime']=timestamp
            write(self.root/'data/canonical-events.json',events)
            assign(self.root,as_of)
            self.approve()
            folder=generate(self.root,as_of)
            self.assertIn(expected,(folder/'linkedin-post.md').read_text())


if __name__=='__main__':unittest.main()
