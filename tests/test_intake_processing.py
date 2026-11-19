import json
from datetime import date, datetime, timezone
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pipeline import ROOT, read, write
from process_intake import process, BRANCH_RE
from submit_intake import submit

REPO = 'owner/repo'
NOW = datetime(2026, 11, 24, 14, 0, tzinfo=timezone.utc)


class FakeSource:
    """Stands in for GitHub: PR metadata plus file blobs (bytes are data only)."""

    test_only = True

    def __init__(self, prs):
        self.prs = prs

    def pull_requests(self, numbers=None):
        return [p['meta'] for p in self.prs]

    def files(self, pr):
        return next(p['files'] for p in self.prs if p['meta']['number'] == pr['number'])

    def blob(self, pr, path):
        return next(p['blobs'][path] for p in self.prs if p['meta']['number'] == pr['number'])


def pr(number, branch, files, repo=REPO):
    return dict(meta=dict(number=number, user={'login': REPO.split('/')[0]}, base={'ref':'main'}, head=dict(ref=branch, sha=f'sha{number}', repo=dict(full_name=repo))),
                files=[dict(filename=path, status=status) for path, status, _ in files],
                blobs={path: content for path, _, content in files})


def as_bytes(value):
    return json.dumps(value, indent=2).encode()


class IntakeProcessingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for folder in ['config', 'templates']:
            shutil.copytree(ROOT / folder, self.root / folder)
        write(self.root / 'data/canonical-events.json', [])
        self.chatgpt = read(ROOT / 'tests/fixtures/chatgpt.json')
        self.antigravity = read(ROOT / 'tests/fixtures/antigravity.json')

    def run_prs(self, *prs):
        return process(self.root, REPO, FakeSource(list(prs)), day=date(2026, 11, 24), now=NOW)

    def test_both_agents_accepted_consolidated_with_provenance_and_weeks(self):
        report = self.run_prs(
            pr(1, 'intake/chatgpt-2026-11-24-070500', [('intake/chatgpt/chatgpt-2026-11-24.json', 'added', as_bytes(self.chatgpt))]),
            pr(2, 'intake/antigravity-2026-11-24-071000', [('intake/antigravity/antigravity-2026-11-24.json', 'added', as_bytes(self.antigravity))]))
        self.assertEqual([p['outcome'] for p in report['pull_requests']], ['accepted', 'accepted'])
        self.assertTrue(report['ingestion_run'])
        events = read(self.root / 'data/canonical-events.json')
        self.assertEqual(len(events), 2)
        overlap = next(e for e in events if len(e['submissions']) == 3)
        self.assertEqual(overlap['discovered_by'], ['antigravity', 'chatgpt'])
        self.assertIn('start_datetime', overlap['conflict_flags'])  # material conflict flagged, later excluded
        self.assertEqual({s['file'] for s in overlap['submissions']}, {'intake/chatgpt/chatgpt-2026-11-24.json', 'intake/antigravity/antigravity-2026-11-24.json'})
        self.assertEqual(report['consolidation']['cross_agent_consolidated'], [overlap['event_id']])
        self.assertEqual(report['consolidation']['future_events'], 1)
        self.assertTrue(all(e['roundup_week'] for e in events))
        self.assertTrue((self.root / 'reports/intake-processing/latest.json').is_file())
        # The original bytes are preserved exactly.
        self.assertEqual((self.root / 'intake/chatgpt/chatgpt-2026-11-24.json').read_bytes(), as_bytes(self.chatgpt))

    def test_invalid_or_mislabelled_submission_is_quarantined_not_discarded(self):
        bad = as_bytes([dict(self.chatgpt[0], start_datetime='2026-12-01T12:00:00')])
        mislabelled = as_bytes(self.chatgpt)  # chatgpt identity inside antigravity intake
        report = self.run_prs(
            pr(3, 'intake/chatgpt-bad', [('intake/chatgpt/chatgpt-bad.json', 'added', bad)]),
            pr(4, 'intake/antigravity-mislabel', [('intake/antigravity/antigravity-x.json', 'added', mislabelled)]),
            pr(5, 'intake/chatgpt-notjson', [('intake/chatgpt/chatgpt-y.json', 'added', b'import os; os.system("x")')]))
        self.assertEqual([p['outcome'] for p in report['pull_requests']], ['quarantined'] * 3)
        self.assertFalse(report['ingestion_run'])
        self.assertEqual((self.root / 'quarantine/chatgpt/pr3-chatgpt-bad.json').read_bytes(), bad)
        self.assertIn('does not match', read(self.root / 'quarantine/antigravity/pr4-antigravity-x.json.errors.json')['reason'])
        self.assertFalse((self.root / 'intake/chatgpt/chatgpt-bad.json').exists())
        self.assertEqual(read(self.root / 'data/canonical-events.json'), [])

    def test_pull_requests_touching_other_paths_or_forks_are_rejected(self):
        report = self.run_prs(
            pr(6, 'intake/chatgpt-evil', [('intake/chatgpt/a.json', 'added', as_bytes(self.chatgpt)), ('scripts/pipeline.py', 'modified', b'x')]),
            pr(7, 'intake/antigravity-wrongdir', [('intake/chatgpt/a.json', 'added', as_bytes(self.chatgpt))]),
            pr(8, 'intake/chatgpt-fork', [('intake/chatgpt/b.json', 'added', as_bytes(self.chatgpt))], repo='attacker/repo'),
            pr(9, 'intake/chatgpt-overwrite', [('intake/chatgpt/c.json', 'modified', as_bytes(self.chatgpt))]))
        self.assertEqual([p['outcome'] for p in report['pull_requests']], ['rejected'] * 4)
        self.assertFalse(any((self.root / 'intake').rglob('*.json')))

    def test_append_only_and_idempotent_reprocessing(self):
        first = pr(10, 'intake/chatgpt-1', [('intake/chatgpt/chatgpt-2026-11-24.json', 'added', as_bytes(self.chatgpt))])
        self.run_prs(first)
        before = (self.root / 'data/canonical-events.json').read_bytes()
        self.assertEqual(self.run_prs(first)['pull_requests'][0]['outcome'], 'already_processed')
        self.assertEqual(before, (self.root / 'data/canonical-events.json').read_bytes())
        altered = as_bytes([dict(self.chatgpt[0], summary='Different content at the same path')])
        report = self.run_prs(pr(11, 'intake/chatgpt-2', [('intake/chatgpt/chatgpt-2026-11-24.json', 'added', altered)]))
        self.assertEqual(report['pull_requests'][0]['files'][0]['outcome'], 'quarantined')
        self.assertEqual((self.root / 'intake/chatgpt/chatgpt-2026-11-24.json').read_bytes(), as_bytes(self.chatgpt))

    def test_branch_naming_and_submit_dry_run(self):
        self.assertTrue(BRANCH_RE.match('intake/antigravity-2026-11-24-070512'))
        self.assertFalse(BRANCH_RE.match('intake/gemini-2026-11-24'))
        source = self.root / 'findings.json'
        write(source, self.antigravity)
        result = submit('antigravity', source, ROOT, dry_run=True)
        self.assertTrue(result['branch'].startswith('intake/antigravity-'))
        self.assertTrue(result['file'].startswith('intake/antigravity/antigravity-'))
        self.assertEqual(result['records'], 3)
        with self.assertRaises(ValueError):
            submit('chatgpt', source, ROOT, dry_run=True)  # identity mismatch rejected before any git action


if __name__ == '__main__':
    unittest.main()
