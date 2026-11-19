"""Isolated synthetic acceptance demonstration; never writes production data.

Exercises both production discovery streams (chatgpt + antigravity), cross-agent overlap, conflict
exclusion, future retention, rerun stability, automated qualification with a synthetic (test-only)
registration check, and Markdown generation. Output in tests/smoke-output/ is labelled SYNTHETIC.
"""
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

from pipeline import ROOT, read, write, ingest, assign, generate

sys.path.insert(0, str(ROOT / 'tests'))
from helpers import confirm, GENERATED_AT  # noqa: E402


def run():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        shutil.copytree(ROOT / 'config', root / 'config')
        shutil.copytree(ROOT / 'templates', root / 'templates')
        write(root / 'data/canonical-events.json', [])
        for agent in ['chatgpt', 'antigravity']:
            (root / 'intake' / agent).mkdir(parents=True)
            shutil.copy(ROOT / f'tests/fixtures/{agent}.json', root / f'intake/{agent}/sample.json')
        sample = read(ROOT / 'tests/fixtures/chatgpt.json')[0]
        sample.update(title='Fixture: Qualified learning session', registration_url='https://example.org/register/qualified')
        write(root / 'intake/chatgpt/qualified.json', [sample])
        ingest(root)
        events = assign(root, date(2026, 11, 24))
        unchecked = generate(root, date(2026, 11, 24), generated_at=GENERATED_AT)
        assert read(unchecked / 'review.json')['selected_ids'] == []
        unverified = read(unchecked / 'review.json')
        before = (root / 'data/canonical-events.json').read_bytes()
        ingest(root)
        assign(root, date(2026, 11, 24))
        assert before == (root / 'data/canonical-events.json').read_bytes()
        overlap = next(e for e in events if len(e['submissions']) == 3)
        assert overlap['discovered_by'] == ['antigravity', 'chatgpt'] and 'start_datetime' in overlap['conflict_flags']
        confirm(root, events)  # SYNTHETIC test-only registration checks
        folder = generate(root, date(2026, 11, 24), generated_at=GENERATED_AT)
        report = read(folder / 'editorial-report.json')
        assert len(events) == 3 and len(read(root / 'data/future-events.json')) == 1
        assert [e['title'] for e in report['events_included']] == [sample['title']]  # conflicted overlap excluded
        output = ROOT / 'tests/smoke-output'
        shutil.rmtree(output, ignore_errors=True)
        shutil.copytree(folder, output)
        write(output / 'canonical-events-SYNTHETIC.json', events)
        write(output / 'future-events-SYNTHETIC.json', read(root / 'data/future-events.json'))
        write(output / 'unchecked-review-SYNTHETIC.json', unverified)
        write(output / 'registration-checks-SYNTHETIC.json', read(root / 'data/registration-checks.json'))
        print('PASS: chatgpt + antigravity intake, overlap, conflict exclusion, future retention, rerun stability, automated qualification and Markdown generation')
        print(output)


if __name__ == '__main__':
    run()
