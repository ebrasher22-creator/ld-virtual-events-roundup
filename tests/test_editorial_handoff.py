import copy
from datetime import date
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pipeline import ROOT, read, write
from editorial_handoff import receive, sha


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        # Exact existing RW49 records/approvals/input are a supervised fixture, never mutated live.
        for folder in ['data','approvals','config','templates']:
            shutil.copytree(ROOT/folder,self.root/folder)
        self.label='2026/RW49_2026-11-29_to_2026-12-05'
        input_dir=self.root/'weeks'/self.label
        input_dir.mkdir(parents=True)
        shutil.copy(ROOT/'weeks'/self.label/'editorial-input.json',input_dir/'editorial-input.json')
        self.draft=read(ROOT/'editorial-drafts/RW49_2026-11-29_to_2026-12-05/work-submission.json')
        self.path=self.root/'return.json'
        write(self.path,self.draft)

    def test_valid_work_return_assembles_complete_packet_without_changing_data(self):
        before=sha(self.root/'data/canonical-events.json')
        packet,result=receive(self.root,self.path,date(2026,11,24))
        self.assertTrue(result['mechanical_validation_passed'])
        self.assertEqual(before,sha(self.root/'data/canonical-events.json'))
        for name in ['linkedin-post.md','linkedin-post-compact.md','validation-report.json','publication-status.json','jarvis-message.txt','review-checklist.md','review-packet.zip']:
            self.assertTrue((packet/name).is_file(),name)
        self.assertEqual((packet/'linkedin-post.md').read_text(),self.draft['full_caption'])
        status=read(packet/'publication-status.json')
        self.assertEqual(status['delivery_status'],'prepared_not_sent')
        self.assertEqual(status['publication_approval_status'],'awaiting_final_human_review')
        self.assertTrue(read(packet/'protected-file-hashes.json')['unchanged'])
        with zipfile.ZipFile(packet/'review-packet.zip') as archive:
            self.assertIn('validation-report.json',archive.namelist())

    def test_failed_return_has_diagnostics_and_no_publishable_caption(self):
        self.draft['full_caption']='Wrong facts'
        write(self.path,self.draft)
        packet,result=receive(self.root,self.path,date(2026,11,24))
        self.assertFalse(result['mechanical_validation_passed'])
        self.assertTrue((packet/'REVISION-REQUIRED.md').is_file())
        self.assertFalse((packet/'linkedin-post.md').exists())
        self.assertFalse((packet/'jarvis-message.txt').exists())

    def test_cannot_write_to_approved_data_or_replace_prior_packet(self):
        with self.assertRaises(ValueError):receive(self.root,self.path,date(2026,11,24),self.root/'data')
        packet,_=receive(self.root,self.path,date(2026,11,24),Path('review-packets/test'))
        with self.assertRaises(FileExistsError):receive(self.root,self.path,date(2026,11,24),packet)

    def test_symlink_escape_is_rejected(self):
        (self.root/'review-packets').symlink_to(self.root/'data',target_is_directory=True)
        with self.assertRaises(ValueError):receive(self.root,self.path,date(2026,11,24),Path('review-packets/escape'))

    def test_stale_current_approval_fails_without_modifying_ledger(self):
        records=read(self.root/'data/canonical-events.json')
        records[0]['summary']='Changed only in the isolated negative test'
        write(self.root/'data/canonical-events.json',records)
        before=sha(self.root/'data/reviews.json')
        packet,result=receive(self.root,self.path,date(2026,11,24))
        self.assertFalse(result['mechanical_validation_passed'])
        self.assertEqual(before,sha(self.root/'data/reviews.json'))

    def test_wrong_week_or_malformed_json_fails_safely(self):
        self.draft['roundup_identifier']='2026/RW50_2026-12-06_to_2026-12-12'
        write(self.path,self.draft)
        _,result=receive(self.root,self.path,date(2026,11,24))
        self.assertFalse(result['mechanical_validation_passed'])
        self.path.write_text('not executable code or valid JSON')
        _,result=receive(self.root,self.path,date(2026,11,24))
        self.assertFalse(result['mechanical_validation_passed'])


if __name__=='__main__':unittest.main()
