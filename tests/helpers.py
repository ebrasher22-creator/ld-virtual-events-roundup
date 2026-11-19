"""Shared test helpers. Synthetic registration checks are test-only and never written to production data."""
from pathlib import Path
from pipeline import read, write
from qualification import check_key, CHECKS_PATH

CHECKED_AT = '2026-11-24T06:00:00Z'
GENERATED_AT = '2026-11-25T13:05:00Z'


def confirm(root, events=None, checked_at=CHECKED_AT, classification='confirmed', date_on_page=True):
    root = Path(root)
    events = events if events is not None else read(root / 'data/canonical-events.json')
    path = root / CHECKS_PATH
    checks = read(path) if path.is_file() else {}
    for e in events:
        checks[e['event_id']] = dict(event_id=e['event_id'], record_key=check_key(e), checked_at=checked_at, classification=classification,
                                     date_confirmed_on_page=date_on_page, pages=[dict(role='registration', url=e['registration_url'], status=200,
                                                                                     classification=classification, observed_text=' '.join(i.get('excerpt','') for i in e.get('evidence',[])), synthetic_test_check=True)])
    write(path, checks)
    return checks
