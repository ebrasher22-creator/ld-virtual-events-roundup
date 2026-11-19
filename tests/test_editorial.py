import copy
from datetime import date, datetime
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import ROOT, read, write, ingest, assign, generate
from qualification import (qualification, pricing_label, classify_page, check_event, run_checks, is_eligible, CHECKS_PATH)
from prepare_wednesday import is_wednesday_slot, should_run_scheduled, prepare
from validate_post import validate_output
from helpers import confirm, CHECKED_AT, GENERATED_AT

AS_OF = date(2026, 11, 24)
REF = datetime.fromisoformat('2026-11-25T13:05:00+00:00')


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ['config', 'templates']:
            shutil.copytree(ROOT / directory, self.root / directory)
        write(self.root / 'data/canonical-events.json', [])
        self.raw = read(ROOT / 'tests/fixtures/chatgpt.json')[0]
        write(self.root / 'intake/chatgpt/test.json', [self.raw])
        ingest(self.root)
        self.events = assign(self.root, AS_OF)
        self.e = self.events[0]
        confirm(self.root)

    def gen(self, day=AS_OF, generated_at=GENERATED_AT):
        return generate(self.root, day, generated_at=generated_at)

    def set_events(self, events):
        write(self.root / 'data/canonical-events.json', events)
        assign(self.root, AS_OF)
        return read(self.root / 'data/canonical-events.json')

    def test_qualified_without_any_human_review_record(self):
        self.assertFalse((self.root / 'data/reviews.json').exists())
        folder = self.gen()
        report = read(folder / 'editorial-report.json')
        self.assertEqual(report['qualification_mode'], 'automated_no_per_event_human_approval')
        self.assertEqual([e['event_id'] for e in report['events_included']], [self.e['event_id']])
        self.assertEqual(self.e['verification_status'], 'pending')  # no approval is fabricated

    def test_unchecked_stale_old_and_unresolved_checks_are_excluded(self):
        write(self.root / CHECKS_PATH, {})
        self.assertIn('registration_not_checked', qualification(self.e, self.root, REF)[0])
        confirm(self.root, checked_at='2026-11-20T00:00:00Z')
        self.assertIn('registration_check_too_old', qualification(self.e, self.root, REF)[0])
        confirm(self.root)
        changed = dict(self.e, start_datetime='2026-12-01T13:00:00-06:00')
        self.assertIn('registration_check_stale_for_current_facts', qualification(changed, self.root, REF)[0])
        for kind in ['registration_unreachable', 'cancel_or_closed_signal', 'event_details_unconfirmed', 'registration_not_found']:
            confirm(self.root, classification=kind)
            with self.subTest(kind=kind):
                self.assertIn('registration_check:' + kind, qualification(self.e, self.root, REF)[0])

    def test_live_page_classification_never_treats_blocked_page_as_canceled(self):
        def fake(status, body=''):
            return lambda url: dict(status=status, final_url=url, body=body, error=None if status == 200 else f'HTTP {status}')
        page = f'<html><title>{self.e["title"]}</title><p>Example Association online webinar December 1, 2026 12:00 PM CST</p></html>'
        self.assertEqual(classify_page(fake(403)(''), self.e)['classification'], 'inaccessible_bot_or_auth')
        self.assertEqual(classify_page(fake(429)(''), self.e)['classification'], 'inaccessible_bot_or_auth')
        self.assertEqual(classify_page(fake(200, '<title>Just a moment...</title> cf-chl')(''), self.e)['classification'], 'inaccessible_bot_or_auth')
        self.assertEqual(classify_page(fake(404)(''), self.e)['classification'], 'not_found')
        self.assertEqual(classify_page(dict(status=None, final_url='', body='', error='URLError'), self.e)['classification'], 'inaccessible')
        confirmed = classify_page(fake(200, page)(''), self.e)
        self.assertEqual(confirmed['classification'], 'confirmed')
        self.assertTrue(confirmed['date_match'])
        self.assertEqual(classify_page(fake(200, page + ' This event has been cancelled.')(''), self.e)['classification'], 'cancel_or_closed_signal')
        self.assertEqual(check_event(self.e, fake(403))['classification'], 'registration_unreachable')
        self.assertEqual(check_event(self.e, fake(200, page))['classification'], 'confirmed')

    def test_material_conflicts_excluded_description_variants_warned(self):
        events = read(self.root / 'data/canonical-events.json')
        events[0]['conflict_flags'] = ['start_datetime']
        events = self.set_events(events)
        self.assertIn('unresolved_conflict:start_datetime', qualification(events[0], self.root, REF)[0])
        events[0]['conflict_flags'] = ['summary']
        events = self.set_events(events)
        confirm(self.root, events)
        problems, warnings = qualification(events[0], self.root, REF)
        self.assertEqual(problems, [])
        self.assertTrue(any('description_variants' in w for w in warnings))

    def test_owner_deferred_relevance_and_primary_evidence_rules(self):
        config = read(self.root / 'config/qualification.yml')
        config['deferred_events'] = {self.e['event_id']: 'test deferral'}
        self.assertIn('owner_deferred: test deferral', qualification(self.e, self.root, REF, config=config)[0])
        unrelated = dict(self.e, title='Quarterly tax filing for restaurants', summary='Tax forms.', topics=['taxes'], audience=['accountants'])
        self.assertIn('not_professionally_relevant', qualification(unrelated, self.root, REF)[0])
        third_party = dict(self.e, evidence=[dict(claim='datetime', source_url='https://aggregator.example.net/x', excerpt='listing')])
        self.assertIn('no_primary_source_evidence', qualification(third_party, self.root, REF)[0])

    def test_pricing_is_never_inferred(self):
        free_evidence = [dict(claim='price', source_url=self.e['event_url'], excerpt='Registration is free.')]
        self.assertEqual(pricing_label(dict(self.e, price_type='free', evidence=free_evidence)), 'Free')
        self.assertEqual(pricing_label(dict(self.e, price_type='free')), 'Pricing not listed')  # no explicit evidence
        paid = [dict(claim='price', source_url=self.e['event_url'], excerpt='Members $49; registration open.')]
        self.assertEqual(pricing_label(dict(self.e, price_type='paid', cost=49, evidence=paid)), 'Paid: $49')
        self.assertEqual(pricing_label(dict(self.e, price_type='paid')), 'Paid (price on registration page)')
        self.assertEqual(pricing_label(dict(self.e, price_type='unknown')), 'Pricing not listed')
        text = (self.gen() / 'linkedin-post.md').read_text()
        self.assertIn('| Pricing not listed', text)
        self.assertNotIn('| Free', text)

    def test_post_contains_description_host_time_price_and_link(self):
        text = (self.gen() / 'linkedin-post.md').read_text()
        for part in [self.e['title'], 'Hosted by ' + self.e['organizer'], 'Tue, Dec 1, 2026 | 12:00 PM CST', self.e['summary'], self.raw['registration_url']]:
            self.assertIn(part, text)

    def test_future_week_is_excluded_and_remains_available(self):
        events = read(self.root / 'data/canonical-events.json')
        future = copy.deepcopy(events[0])
        future.update(event_id='future-test', start_datetime='2026-12-08T12:00:00-06:00', title='Synthetic future learning event',
                      registration_url='https://example.org/future')
        events = self.set_events(events + [future])
        confirm(self.root, events)
        report = read(self.gen() / 'editorial-report.json')
        self.assertEqual(len(report['events_included']), 1)
        self.assertIn('outside_target_week', [x['reason'] for x in report['events_excluded']])
        self.assertEqual(len(read(self.root / 'data/future-events.json')), 1)
        confirm(self.root, events, checked_at='2026-12-02T13:00:00Z')  # checks expire; Wednesday re-checks
        later = self.gen(date(2026, 12, 1), '2026-12-02T13:05:00Z')
        self.assertIn('Synthetic future learning event', (later / 'linkedin-post.md').read_text())

    def test_above_target_does_not_silently_cap_collection(self):
        baseline = read(self.root / 'data/canonical-events.json')[0]
        events = []
        for index in range(13):
            e = copy.deepcopy(baseline)
            e.update(event_id=f'event-{index}', title=f'Learning transfer clinic {index}', registration_url=f'https://example.org/{index}', summary='Short.')
            events.append(e)
        events = self.set_events(events)
        confirm(self.root, events)
        report = read(self.gen() / 'editorial-report.json')
        self.assertEqual(len(report['events_included']), 12)
        self.assertEqual(report['total_qualified_candidates'], 13)

    def test_overflow_writes_explicit_exception_and_preserves_all_events(self):
        rules = read(self.root / 'config/editorial-rules.yml')
        rules['linkedin_max_characters'] = 50
        rules['linkedin_target_characters'] = 40
        write(self.root / 'config/editorial-rules.yml', rules)
        with self.assertRaises(ValueError):
            self.gen()
        folder = self.root / 'weeks/2026/RW49_2026-11-29_to_2026-12-05'
        report = read(folder / 'editorial-report.json')
        self.assertEqual(len(report['events_included']), 1)
        self.assertFalse(report['within_character_limit'])
        self.assertEqual(report['readiness_status'], 'not_ready_action_required')
        self.assertIn(self.raw['title'], (folder / 'linkedin-post.md').read_text())

    def test_shorten_optional_text_before_dropping_essential_details(self):
        brand = read(self.root / 'config/branding.yml')
        brand['introduction'] = 'Long introductory text ' * 150
        write(self.root / 'config/branding.yml', brand)
        report = read(self.gen() / 'editorial-report.json')
        self.assertTrue(report['within_character_limit'])
        self.assertEqual(report['caption_strategy'], 'shortened_introduction')
        self.assertTrue(report['descriptions_included'])
        self.assertLessEqual(report['character_counts']['full'], 2800)

    def test_repeat_execution_stable_and_validator_passes(self):
        folder = self.gen(generated_at=GENERATED_AT)
        full = (folder / 'linkedin-post.md').read_bytes()
        first = read(folder / 'editorial-report.json')
        self.gen(generated_at='2026-11-25T13:06:00Z')
        second = read(folder / 'editorial-report.json')
        self.assertEqual(full, (folder / 'linkedin-post.md').read_bytes())
        self.assertNotEqual(first.pop('generated_at'), second.pop('generated_at'))
        self.assertEqual(first, second)
        validate_output(self.root, AS_OF)

    def test_validator_rejects_changed_data_after_generation(self):
        self.gen()
        events = read(self.root / 'data/canonical-events.json')
        events[0]['summary'] = 'Changed after generation'
        write(self.root / 'data/canonical-events.json', events)
        with self.assertRaises(ValueError):
            validate_output(self.root, AS_OF)

    def test_handoff_readiness_states(self):
        self.gen()
        handoff = read(self.root / 'weeks/current-handoff.json')
        self.assertEqual(handoff['readiness_status'], 'ready_with_warnings')  # below target + pricing not listed
        self.assertEqual(handoff['event_count'], 1)
        self.assertTrue(handoff['post_url'].endswith('weeks/2026/RW49_2026-11-29_to_2026-12-05/linkedin-post.md'))
        self.assertEqual(handoff['publication_approval_status'], 'awaiting_final_human_review')
        self.assertIn("READY WITH WARNINGS", (self.root / 'weeks/current-handoff.md').read_text())
        write(self.root / CHECKS_PATH, {})
        self.gen()
        self.assertEqual(read(self.root / 'weeks/current-handoff.json')['readiness_status'], 'not_ready_action_required')
        rules = read(self.root / 'config/editorial-rules.yml')
        rules['target_min'] = 1
        write(self.root / 'config/editorial-rules.yml', rules)
        events = read(self.root / 'data/canonical-events.json')
        events[0]['evidence'].append(dict(claim='price', source_url=self.e['event_url'], excerpt='Free webinar.'))
        events = self.set_events(events)
        confirm(self.root, events)
        self.gen()
        self.assertEqual(read(self.root / 'weeks/current-handoff.json')['readiness_status'], 'ready_for_review')

    def test_prepare_runs_checks_with_injected_fetcher(self):
        page = f'<h1>{self.e["title"]}</h1> Example Association online webinar December 1, 2026 12:00 PM CST'
        folder = prepare(self.root, AS_OF, True, lambda url: dict(status=200, final_url=url, body=page, error=None), GENERATED_AT)
        self.assertEqual(read(self.root / CHECKS_PATH)[self.e['event_id']]['classification'], 'confirmed')
        self.assertEqual(len(read(folder / 'editorial-report.json')['events_included']), 1)
        prepare(self.root, AS_OF, True, lambda url: dict(status=403, final_url=url, body='', error='HTTP 403'), GENERATED_AT)
        self.assertEqual(len(read(folder / 'editorial-report.json')['events_included']), 0)

    def test_wednesday_guards_handle_dst_and_run_once(self):
        for timestamp, expected in [('2026-11-25T13:00:00+00:00', True), ('2026-07-01T12:00:00+00:00', True), ('2026-11-25T12:00:00+00:00', False),
                                    ('2026-07-01T13:00:00+00:00', False), ('2026-11-24T13:00:00+00:00', False)]:
            with self.subTest(timestamp=timestamp):
                self.assertEqual(is_wednesday_slot(datetime.fromisoformat(timestamp)), expected)
        empty = self.root / 'empty'
        self.assertTrue(should_run_scheduled(datetime.fromisoformat('2026-11-25T13:00:00+00:00'), empty))   # 07:00 CST
        self.assertTrue(should_run_scheduled(datetime.fromisoformat('2026-11-25T14:30:00+00:00'), empty))   # delayed 08:30 CST
        self.assertFalse(should_run_scheduled(datetime.fromisoformat('2026-11-25T12:00:00+00:00'), empty))  # 06:00 CST
        self.assertTrue(should_run_scheduled(datetime.fromisoformat('2026-07-01T12:00:00+00:00'), empty))   # 07:00 CDT
        write(empty / 'weeks/current-handoff.json', dict(generated_on_local_date='2026-11-25', roundup_identifier='2026/RW49_2026-11-29_to_2026-12-05'))
        self.assertFalse(should_run_scheduled(datetime.fromisoformat('2026-11-25T14:00:00+00:00'), empty))  # already ran today

    def test_jarvis_rejects_stale_or_tampered_packet_without_editing_it(self):
        from jarvis_handoff import inspect
        self.gen()
        before=(self.root/'weeks/current-handoff.json').read_bytes()
        result=inspect(self.root, date(2026,11,25))
        self.assertEqual(result['readiness_status'],'ready_with_warnings')
        self.assertEqual(before,(self.root/'weeks/current-handoff.json').read_bytes())
        self.assertEqual(inspect(self.root,date(2026,11,26))['reason'],'stale_or_wrong_week_handoff')
        path=self.root/'weeks/current-handoff.json'
        marker=read(path);marker['event_count']+=1;write(path,marker)
        self.assertEqual(inspect(self.root,date(2026,11,25))['readiness_status'],'not_ready_action_required')

    def test_cdt_and_cst_display(self):
        for timestamp, as_of, expected in [('2026-12-01T12:00:00-06:00', AS_OF, '12:00 PM CST'), ('2026-07-01T12:00:00-05:00', date(2026, 6, 24), '12:00 PM CDT')]:
            events = read(self.root / 'data/canonical-events.json')
            events[0]['start_datetime'] = timestamp
            write(self.root / 'data/canonical-events.json', events)
            events = assign(self.root, as_of)
            confirm(self.root, events, checked_at=('2026-06-25T13:00:00Z' if as_of.month == 6 else CHECKED_AT))
            folder = self.gen(as_of, '2026-06-25T13:05:00Z' if as_of.month == 6 else GENERATED_AT)
            self.assertIn(expected, (folder / 'linkedin-post.md').read_text())


if __name__ == '__main__':
    unittest.main()
