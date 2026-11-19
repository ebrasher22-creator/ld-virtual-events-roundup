import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pipeline import ROOT, read, write
from qualification import check_event, check_key, public_target, qualification
from process_intake import stage_file, MAX_BYTES, review_pull_request

class ProductionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.event = read(ROOT/'tests/fixtures/chatgpt.json')[0]
        self.event['event_id'] = 'test'

    def page(self, text):
        return lambda link: dict(status=200, final_url=link, body=text, error=None)

    def test_live_title_alone_or_wrong_date_time_timezone_never_qualifies(self):
        base = self.event['title'] + ' Example Association webinar December 1, 2026 12:00 PM CST'
        self.assertEqual(check_event(self.event,self.page(base))['classification'], 'confirmed')
        for text in [self.event['title'], base.replace('2026','2025'), base.replace('12:00','1:00'), base.replace('CST','PST'), base.replace('webinar','dinner')]:
            with self.subTest(text=text):
                self.assertNotEqual(check_event(self.event,self.page(text))['classification'], 'confirmed')

    def test_required_fact_changes_invalidate_check(self):
        before = check_key(self.event)
        for field,value in [('summary','Unsubstantiated new description'),('timezone','America/New_York'),('event_format','in_person'),('price_type','paid')]:
            self.assertNotEqual(before,check_key(dict(self.event,**{field:value})))

    def test_unreachable_primary_page_is_not_rescued_by_generic_registration(self):
        def fetch(link):
            if '/events/' in link:return dict(status=403, final_url=link, body='', error='HTTP 403')
            return self.page('Registration catalog')(link)
        self.assertNotEqual(check_event(self.event,fetch)['classification'], 'confirmed')

    def test_private_and_redirect_destinations_blocked(self):
        for address in ['127.0.0.1','10.0.0.1','169.254.169.254','::1']:
            with patch('qualification.socket.getaddrinfo',return_value=[(None,None,None,None,(address,80))]):
                with self.assertRaises(ValueError):public_target('http://private.example/x')

    def test_reserved_synthetic_source_quarantined_and_bytes_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            raw=json.dumps([self.event]).encode()
            # Only discovery schema fields are allowed in an intake record.
            event=dict(self.event);event.pop('event_id')
            raw=json.dumps([event]).encode()
            result=stage_file(Path(t),'chatgpt','intake/chatgpt/test.json',raw,7)
            self.assertEqual(result['outcome'],'quarantined')
            self.assertEqual((Path(t)/result['location']).read_bytes(),raw)
            large=b'x'*(MAX_BYTES+1)
            result=stage_file(Path(t),'chatgpt','intake/chatgpt/large.json',large,8)
            self.assertEqual((Path(t)/result['location']).read_bytes(),large)

    def test_unknown_author_or_wrong_base_rejected_before_reading_blobs(self):
        for metadata in [dict(user={'login':'attacker'},base={'ref':'main'}),dict(user={'login':'owner'},base={'ref':'other'})]:
            pr=dict(number=1,head=dict(ref='intake/chatgpt-test',sha='abc',repo={'full_name':'owner/repo'}),**metadata)
            self.assertEqual(review_pull_request(Path('.'),None,'owner/repo',pr)['outcome'],'rejected')

    def test_persistence_accepts_only_generated_data_paths(self):
        from persist_outputs import allowed_output
        for kind in ['intake','editorial']:
            for path in ['scripts/pipeline.py','.github/workflows/validate.yml','data/reviews.json','approvals/x.md']:
                self.assertFalse(allowed_output(path,kind))
        self.assertTrue(allowed_output('intake/chatgpt/real.json','intake'))
        self.assertFalse(allowed_output('intake/gemini/old.json','intake'))
        self.assertTrue(allowed_output('weeks/current-handoff.json','editorial'))

    def test_free_is_not_inferred_from_unrelated_or_negated_text(self):
        from qualification import explicit_free
        self.assertTrue(explicit_free('Registration is free.'))
        self.assertTrue(explicit_free('A complimentary webinar.'))
        self.assertFalse(explicit_free('This event is not free.'))
        self.assertFalse(explicit_free('Download our free resources.'))

    def test_audit_record_keeps_facts_and_hash_not_entire_source_page(self):
        page=self.event['title']+' Example Association free webinar December 1, 2026 12:00 PM CST '+('Long site navigation '*10000)
        result=check_event(self.event,self.page(page))
        self.assertEqual(result['classification'],'confirmed')
        for item in result['pages']:
            self.assertNotIn('observed_text',item)
            self.assertTrue(item['free_confirmed'])
            self.assertEqual(len(item['page_sha256']),64)
