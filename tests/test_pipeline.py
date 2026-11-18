import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pipeline import *

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for directory in ['config','data','intake','tests/fixtures']:
            shutil.copytree(ROOT/directory,self.root/directory)
        for agent in ['chatgpt','gemini']:
            shutil.copy(ROOT/f'tests/fixtures/{agent}.json', self.root/f'intake/{agent}/sample.json')
        self.e=read(ROOT/'tests/fixtures/chatgpt.json')[0]
    def test_valid(self): validate(self.e)
    def test_invalid(self):
        for field,value in [('registration_url','javascript:alert(1)'),('event_url','https://bad host.org'),('start_datetime','2026-12-01T12:00:00'),('timezone',''),('topics','learning'),('discovered_by',['unknown']),('price_type','maybe'),('cost',-1),('unsupported','value')]:
            with self.subTest(field=field),self.assertRaises((ValueError,KeyError,TypeError)):
                validate(dict(self.e,**{field:value}))
    def test_week_boundaries(self):
        self.assertEqual(week(date(2026,11,29)),'2026/RW49_2026-11-29_to_2026-12-05')
        self.assertEqual(week(date(2026,12,5)),week(date(2026,11,29)))
        self.assertEqual(target(date(2026,11,24)),week(date(2026,11,29)))
        self.assertEqual(week(date(2020,12,31)),'2020/RW53_2020-12-27_to_2021-01-02')
        self.assertEqual(week(date(2021,1,3)),'2021/RW01_2021-01-03_to_2021-01-09')
    def test_dst(self):
        for timestamp in ['2026-03-08T01:30:00-06:00','2026-03-08T03:30:00-05:00','2026-11-01T01:30:00-05:00','2026-11-01T01:30:00-06:00']:
            validate(dict(self.e,start_datetime=timestamp))
        with self.assertRaises(ValueError): validate(dict(self.e,start_datetime='2026-03-08T02:30:00-06:00'))
    def test_ingest_idempotence_provenance_conflict_future(self):
        events=ingest(self.root)
        self.assertEqual(len(events),2)
        overlap=next(e for e in events if len(e['submissions'])==3)
        self.assertEqual(overlap['discovered_by'],['chatgpt','gemini'])
        self.assertIn('start_datetime',overlap['conflict_flags'])
        before=(self.root/'data/canonical-events.json').read_bytes()
        ingest(self.root)
        self.assertEqual(before,(self.root/'data/canonical-events.json').read_bytes())
        assign(self.root,date(2026,11,24))
        self.assertEqual(len(read(self.root/'data/future-events.json')),1)
    def test_transactional_invalid_batch(self):
        write(self.root/'intake/gemini/bad.json',[{}])
        with self.assertRaises(ValueError):ingest(self.root)
        self.assertEqual(read(self.root/'data/canonical-events.json'),[])
    def test_unverified_excluded_and_output_reproducible(self):
        ingest(self.root);assign(self.root,date(2026,11,24))
        folder=generate(self.root,date(2026,11,24))
        self.assertEqual(read(folder/'review.json')['selected_ids'],[])
        first=(folder/'linkedin-roundup.md').read_bytes()
        generate(self.root,date(2026,11,24))
        self.assertEqual(first,(folder/'linkedin-roundup.md').read_bytes())
    def test_agent_cannot_self_verify(self):
        forged=dict(self.e,verification_status='verified',editorial_status='selected')
        write(self.root/'intake/chatgpt/sample.json',[forged])
        self.assertTrue(all(e['verification_status']=='pending' for e in ingest(self.root)))
    def test_review_binds_exact_record(self):
        (self.root/'intake/gemini/sample.json').unlink()
        ingest(self.root);events=assign(self.root,date(2026,11,24));e=events[0]
        review=dict(record_sha256=fingerprint(e),decision='verified',editorial_decision='selected',reviewer='Fixture reviewer',verified_at='2026-11-24T20:00:00Z',claims={k:dict(primary_url=e['event_url'],observation='Synthetic test observation') for k in CLAIMS})
        write(self.root/'data/reviews.json',{e['event_id']:review})
        self.assertTrue(eligible(e,{e['event_id']:review}))
        folder=generate(self.root,date(2026,11,24))
        self.assertIn(e['title'],(folder/'linkedin-roundup.md').read_text())
        changed=dict(e,summary='Changed claim')
        self.assertFalse(eligible(changed,{e['event_id']:review}))
    def test_length_limit(self):
        ingest(self.root);assign(self.root,date(2026,11,24))
        write(self.root/'config/editorial-rules.yml',dict(target_min=8,target_max=12,linkedin_max_characters=10))
        with self.assertRaises(ValueError):generate(self.root,date(2026,11,24))

if __name__=='__main__': unittest.main()
