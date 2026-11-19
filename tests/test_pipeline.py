import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import subprocess
import unittest
from datetime import date, datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pipeline import *
sys.path.insert(0,str(Path(__file__).resolve().parent))
from helpers import confirm, GENERATED_AT

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for directory in ['config','templates','tests/fixtures']:
            shutil.copytree(ROOT/directory,self.root/directory)
        for agent in ['chatgpt','gemini']:
            (self.root/f'intake/{agent}').mkdir(parents=True)
            shutil.copy(ROOT/f'tests/fixtures/{agent}.json', self.root/f'intake/{agent}/sample.json')
        write(self.root/'data/canonical-events.json',[])
        write(self.root/'data/reviews.json',{})
        self.e=read(ROOT/'tests/fixtures/chatgpt.json')[0]
    def test_valid(self): validate(self.e)
    def test_invalid(self):
        for field,value in [('registration_url','javascript:alert(1)'),('event_url','https://bad host.org'),('start_datetime','2026-12-01T12:00:00'),('timezone',''),('topics','learning'),('discovered_by',['unknown']),('price_type','maybe'),('cost',-1),('unsupported','value')]:
            with self.subTest(field=field),self.assertRaises((ValueError,KeyError,TypeError)):
                validate(dict(self.e,**{field:value}))
    def test_schema_contract_invalid_shapes(self):
        for field,value in [('event_url',None),('registration_url',None),('start_datetime',None),('discovered_by',[{}]),('evidence',[dict(claim=7,source_url='https://example.org',excerpt='x')]),('cost',float('nan')),('editorial_score','high'),('topics',[]),('source_urls',[]),('evidence',[])]:
            with self.subTest(field=field),self.assertRaises(ValueError): validate(dict(self.e,**{field:value}))
    def test_utc_instant_with_iana_display_zone(self):
        validate(dict(self.e,start_datetime='2026-12-01T18:00:00Z'))
        (self.root/'intake/gemini/sample.json').unlink()
        ingest(self.root)
        write(self.root/'intake/gemini/utc.json',[dict(self.e,start_datetime='2026-12-01T18:00:00Z',discovered_by=['gemini'])])
        events=ingest(self.root)
        self.assertEqual(events[0]['conflict_flags'],[])
    def test_schema_required_fields_and_registry(self):
        self.assertEqual(REQUIRED,set(SCHEMA['items']['required']))
        registry=read(ROOT/'config/sources.yml')
        self.assertTrue(registry['allow_beyond_list'])
        names=set()
        for lead in registry['leads']:
            self.assertNotIn(lead['name'],names)
            names.add(lead['name'])
            self.assertEqual(lead['status'],'discovery_lead_only')
            if lead['url']: url(lead['url'])
        self.assertEqual(len(names),76)
    def test_manual_cli_intake(self):
        for script in ['validate','ingest','assign_weeks','generate_post']:
            result=subprocess.run([sys.executable,str(ROOT/f'scripts/{script}.py'),'--root',str(self.root),'--as-of','2026-11-24'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(read(self.root/'data/canonical-events.json')),2)
        folder=self.root/'weeks/2026/RW49_2026-11-29_to_2026-12-05'
        self.assertTrue((folder/'linkedin-roundup.md').is_file())
        self.assertEqual(read(folder/'review.json')['selected_ids'],[])
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
        # Historical owner attestations still bind exact records, but they no longer gate publication.
        self.assertTrue(eligible(e,{e['event_id']:review}))
        changed=dict(e,summary='Changed claim')
        self.assertFalse(eligible(changed,{e['event_id']:review}))
        folder=generate(self.root,date(2026,11,24),generated_at=GENERATED_AT)
        self.assertNotIn(e['title'],(folder/'linkedin-roundup.md').read_text())  # approval alone is insufficient: no live check
        confirm(self.root,[e])
        folder=generate(self.root,date(2026,11,24),generated_at=GENERATED_AT)
        self.assertIn(e['title'],(folder/'linkedin-roundup.md').read_text())
    def test_length_limit(self):
        (self.root/'intake/gemini/sample.json').unlink()
        ingest(self.root);confirm(self.root,assign(self.root,date(2026,11,24)))
        write(self.root/'config/editorial-rules.yml',dict(target_min=8,target_max=12,linkedin_max_characters=10))
        with self.assertRaises(ValueError):generate(self.root,date(2026,11,24),generated_at=GENERATED_AT)

    def test_p1_agent_identity_and_legacy_compatibility(self):
        self.assertEqual(SCHEMA['items']['properties']['discovered_by']['items']['enum'],['chatgpt','antigravity','gemini'])
        ag=read(ROOT/'tests/fixtures/antigravity.json')
        validate_intake_batch(self.root/'intake/antigravity/a.json',ag)
        validate_intake_batch(self.root/'intake/gemini/legacy.json',read(ROOT/'tests/fixtures/gemini.json'))
        for folder,data in [('antigravity',read(ROOT/'tests/fixtures/gemini.json')),('chatgpt',ag),('gemini',ag),('unknown',ag)]:
            with self.subTest(folder=folder),self.assertRaises(ValueError):
                validate_intake_batch(self.root/f'intake/{folder}/x.json',data)
        self.assertEqual(canonical_streams(['gemini','chatgpt']),['antigravity','chatgpt'])
        (self.root/'intake/gemini/sample.json').unlink()
        write(self.root/'intake/antigravity/sample.json',ag)
        events=ingest(self.root)
        overlap=next(e for e in events if len(e['submissions'])>1)
        self.assertEqual(overlap['discovered_by'],['antigravity','chatgpt'])
        write(self.root/'intake/antigravity/mislabelled.json',read(ROOT/'tests/fixtures/chatgpt.json'))
        with self.assertRaises(ValueError):ingest(self.root)

    def test_historical_production_intake_is_preserved_and_valid(self):
        gemini=ROOT/'intake/gemini/gemini-2026-11-18.json'
        chatgpt=ROOT/'intake/chatgpt/chatgpt-2026-11-18-pilot.json'
        manifest={e['repository_path']:e['sha256'] for e in read(ROOT/'reports/pilots/discovery-consolidation-2026-11-18/originals/manifest.json')}
        import hashlib
        self.assertEqual(hashlib.sha256(chatgpt.read_bytes()).hexdigest(),manifest['intake/chatgpt/chatgpt-2026-11-18-pilot.json'])
        self.assertEqual(hashlib.sha256(gemini.read_bytes()).hexdigest(),manifest['intake/gemini/gemini-2026-11-18.json'])
        for path in sorted((ROOT/'intake').glob('*/*.json')):validate_intake_batch(path,read(path))
        for path in sorted((ROOT/'intake').rglob('*.json')):self.assertNotIn('SYNTHETIC',path.read_text(),path)

    def test_scoped_organizer_aliases_and_domain_enforcement(self):
        (self.root/'intake/chatgpt/sample.json').unlink()
        (self.root/'intake/gemini/sample.json').unlink()
        base = dict(
            self.e,
            title='AI in the Flow of Work: How L&D Professionals Are Working Alongside AI',
            organizer='Training Industry',
            event_url='https://trainingindustry.com/webinar/artificial-intelligence/ai-in-the-flow-of-work/',
            registration_url='https://trainingindustry.com/webinar/artificial-intelligence/ai-in-the-flow-of-work/',
            start_datetime='2026-12-08T11:00:00-05:00',
            timezone='America/New_York',
            source_urls=['https://trainingindustry.com/webinar/artificial-intelligence/ai-in-the-flow-of-work/'],
            discovered_by=['chatgpt'],
        )
        corroborating = dict(
            base,
            organizer='Training Industry, Inc.',
            organizer_url='https://trainingindustry.com',
            registration_url='https://events.zoom.us/ev/example-zoom-registration',
            discovered_by=['gemini'],
        )
        impostor_domain = dict(
            base,
            organizer='Training Industry, Inc.',
            event_url='https://unverified-host.example.org/events/ai-flow',
            registration_url='https://unverified-host.example.org/register/ai-flow',
            source_urls=['https://unverified-host.example.org/events/ai-flow'],
            discovered_by=['gemini'],
        )
        unlisted_suffix = dict(
            base,
            organizer='Example Association, Inc.',
            event_url='https://example.org/events/unlisted',
            registration_url='https://example.org/register/unlisted-1',
            source_urls=['https://example.org/events/unlisted'],
        )
        unlisted_plain = dict(
            unlisted_suffix,
            organizer='Example Association',
            registration_url='https://example.org/register/unlisted-2',
            discovered_by=['gemini'],
        )
        write(self.root/'intake/chatgpt/aliases.json', [base, unlisted_suffix])
        write(self.root/'intake/gemini/aliases.json', [corroborating, impostor_domain, unlisted_plain])
        events = ingest(self.root)
        # base + corroborating merge (1); impostor_domain stays separate (1); unlisted suffix/plain stay separate (2) -> 4 total
        self.assertEqual(len(events), 4)
        merged = next(x for x in events if x['organizer'] == 'Training Industry')
        self.assertEqual(merged['discovered_by'], ['chatgpt', 'gemini'])
        self.assertNotIn('organizer', merged['conflict_flags'])
        self.assertIn('registration_url', merged['conflict_flags'])

    def test_meaningful_description_differences_and_conflicting_evidence_preserved(self):
        (self.root/'intake/chatgpt/sample.json').unlink()
        (self.root/'intake/gemini/sample.json').unlink()
        first = dict(
            self.e,
            title='L&D as a Conductor: Orchestrating People, AI, and Business Priorities',
            organizer='iSpring',
            event_url='https://www.ispringsolutions.com/webinars/l-d-as-a-conductor',
            registration_url='https://www.ispringsolutions.com/webinars/l-d-as-a-conductor',
            start_datetime='2026-12-02T10:00:00-05:00',
            end_datetime=None,
            timezone='America/New_York',
            summary='Short description of training ROI and stakeholder alignment.',
            source_urls=['https://www.ispringsolutions.com/webinars/l-d-as-a-conductor'],
            discovered_at='2026-11-18T19:39:10+00:00',
            discovered_by=['chatgpt'],
            evidence=[dict(claim='datetime', source_url='https://www.ispringsolutions.com/webinars/l-d-as-a-conductor', excerpt='ChatGPT primary excerpt')],
        )
        second = dict(
            first,
            title='L&D As A Conductor: Orchestrating People, AI, And Business Priorities',
            organizer='iSpring Solutions',
            organizer_url='https://www.ispringsolutions.com',
            registration_url='https://www.ispringsolutions.com/webinars/l-d-as-a-conductor?utm_source=partner',
            end_datetime='2026-12-02T11:00:00-05:00',
            summary='Detailed description covering iSpring 2026 ROI Playbook across 140+ professionals and four barriers.',
            discovered_at='2026-11-18T14:21:32-06:00',
            discovered_by=['gemini'],
            evidence=[dict(claim='price', source_url='https://www.ispringsolutions.com/webinars/l-d-as-a-conductor', excerpt='Gemini primary excerpt')],
        )
        write(self.root/'intake/chatgpt/desc.json', [first])
        write(self.root/'intake/gemini/desc.json', [second])
        events = ingest(self.root)
        self.assertEqual(len(events), 1)
        merged = events[0]
        self.assertEqual(merged['conflict_flags'], ['summary'])
        self.assertEqual(len(merged['evidence']), 2)
        self.assertEqual(len(merged['submissions']), 2)
        # 14:21:32-06:00 is 20:21:32Z, which is chronologically after 19:39:10+00:00
        self.assertEqual(merged['updated_at'], '2026-11-18T14:21:32-06:00')

    def test_audited_approval_fingerprint_migration_preserves_unchanged_and_rejects_core_conflicts(self):
        (self.root/'intake/gemini/sample.json').unlink()
        first = dict(
            self.e,
            title='[Leader Talk] The 2027 Learning Experience',
            organizer='Training Industry',
            event_url='https://trainingindustry.com/webinar/strategy-alignment-and-planning/leader-talk-the-2027-learning-experience/',
            registration_url='https://trainingindustry.com/webinar/strategy-alignment-and-planning/leader-talk-the-2027-learning-experience/',
            start_datetime='2026-12-03T11:00:00-05:00',
            end_datetime=None,
            timezone='America/New_York',
            source_urls=['https://trainingindustry.com/webinar/strategy-alignment-and-planning/leader-talk-the-2027-learning-experience/'],
        )
        write(self.root/'intake/chatgpt/sample.json', [first])
        events = ingest(self.root)
        e = events[0]
        e['verification_status'] = 'verified'
        e['editorial_status'] = 'selected'
        e['updated_at'] = '2026-11-18T19:39:10+00:00'
        write(self.root/'data/canonical-events.json', [e])
        old_sha = fingerprint(e)
        review = dict(
            record_sha256=old_sha,
            decision='verified',
            editorial_decision='selected',
            reviewer='Fixture reviewer',
            verified_at='2026-11-18T19:39:10Z',
            claims={k: dict(primary_url=e['event_url'], observation='Verified primary page') for k in CLAIMS - {'price'}},
        )
        write(self.root/'data/reviews.json', {e['event_id']: review})
        self.assertTrue(eligible(e, read(self.root/'data/reviews.json'), self.root))

        # Corroborating submission with different summary and proposed end_datetime enrichment preserves approval
        corroborating = dict(
            first,
            organizer='Training Industry, Inc.',
            end_datetime='2026-12-03T15:45:00-05:00',
            summary='Expanded multi-session agenda description from second discovery agent.',
            discovered_by=['gemini'],
            discovered_at='2026-11-18T14:20:03-06:00',
        )
        write(self.root/'intake/gemini/corroborating.json', [corroborating])
        migrated_events = ingest(self.root)
        self.assertEqual(len(migrated_events), 1)
        m = migrated_events[0]
        migrated_reviews = read(self.root/'data/reviews.json')
        self.assertTrue(eligible(m, migrated_reviews, self.root))
        self.assertEqual(m['summary'], first['summary'])
        self.assertIsNone(m['end_datetime'])
        self.assertEqual(m['conflict_flags'], ['summary'])
        mig = migrated_reviews[m['event_id']]['migration']
        self.assertEqual(mig['from_record_sha256'], old_sha)
        self.assertEqual(mig['to_record_sha256'], fingerprint(m))
        self.assertEqual(mig['acknowledged_conflict_flags'], ['summary'])
        self.assertTrue(any(p['field'] == 'summary' and not p['adopted'] for p in mig['unadopted_proposals']))

        # Forged migration acknowledging a core conflict ('start_datetime') must be rejected
        forged_reviews = copy.deepcopy(migrated_reviews)
        forged_reviews[m['event_id']]['migration']['acknowledged_conflict_flags'] = ['start_datetime']
        self.assertEqual(approval_problem(m, forged_reviews, self.root), 'invalid_approval_migration')

        # Core conflict (different start_datetime) must invalidate approval and refuse migration
        conflicting_time = dict(corroborating, start_datetime='2026-12-03T13:00:00-05:00', discovered_at='2026-11-18T15:00:00-06:00')
        write(self.root/'intake/gemini/conflicting.json', [conflicting_time])
        after_conflict = ingest(self.root)[0]
        self.assertEqual(after_conflict['verification_status'], 'pending')
        self.assertIn('start_datetime', after_conflict['conflict_flags'])
        self.assertFalse(eligible(after_conflict, read(self.root/'data/reviews.json'), self.root))

    def test_pilot_consolidation_eleven_candidates_and_editorial_package_migration(self):
        events = read(ROOT/'tests/fixtures/historical-pilot/canonical-events.json')
        reviews = read(ROOT/'tests/fixtures/historical-pilot/reviews.json')
        future = read(ROOT/'tests/fixtures/historical-pilot/future-events.json')
        self.assertEqual(len(events), 11)
        self.assertEqual(len(future), 5)
        rw49 = [e for e in events if e['roundup_week'] == '2026/RW49_2026-11-29_to_2026-12-05']
        rw50 = [e for e in events if e['roundup_week'] == '2026/RW50_2026-12-06_to_2026-12-12']
        rw03 = [e for e in events if e['roundup_week'] == '2027/RW03_2027-01-17_to_2027-01-23']
        rw04 = [e for e in events if e['roundup_week'] == '2027/RW04_2027-01-24_to_2027-01-30']
        self.assertEqual((len(rw49), len(rw50), len(rw03), len(rw04)), (6, 3, 1, 1))
        self.assertEqual(sum(eligible(e, reviews, ROOT) for e in rw49), 5)
        self.assertEqual(sum(eligible(e, reviews, ROOT) for e in rw50), 2)
        pending = [e for e in events if e['verification_status'] == 'pending']
        self.assertEqual(len(pending), 4)
        self.assertTrue(all(not eligible(e, reviews, ROOT) and e['editorial_status'] == 'pending' for e in pending))
        overlaps = [e for e in events if e['discovered_by'] == ['chatgpt', 'gemini']]
        self.assertEqual(len(overlaps), 3)
        self.assertTrue(all('summary' in e['conflict_flags'] and len(e['evidence']) > 1 for e in overlaps))
        self.assertTrue(all('migration' in reviews[e['event_id']] and eligible(e, reviews, ROOT) for e in overlaps))



if __name__=='__main__': unittest.main()
