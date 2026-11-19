"""Validate generated captions against current canonical records, live checks and automated qualification."""
import argparse
from datetime import date, datetime, time as clock
from pathlib import Path
from pipeline import ROOT, CENTRAL, read, target, dt, editorial_registration_url
from editorial import evaluate_week, sha_file, central_time
from qualification import CHECKS_PATH, pricing_label


def validate_output(root=ROOT, day=None):
    root = Path(root)
    day = day or datetime.now(CENTRAL).date()
    label = target(day)
    folder = root / 'weeks' / label
    report = read(folder / 'editorial-report.json')
    if report['roundup_identifier'] != label or report['publication_approval_status'] != 'awaiting_final_human_review':
        raise ValueError('Incorrect week or publication approval status')
    if sha_file(root / 'data/canonical-events.json') != report['canonical_sha256'] or sha_file(root / CHECKS_PATH) != report['registration_checks_sha256']:
        raise ValueError('Source data changed after generation')
    expected, _, _ = evaluate_week(root, label, dt(report['generated_at']), datetime.combine(date.fromisoformat(report['as_of']), clock(0, 0), tzinfo=CENTRAL))
    if [e['event_id'] for e in expected] != [e['event_id'] for e in report['events_included']]:
        raise ValueError('Generated membership differs from automatically qualified target-week events')
    if report['editorial_exceptions'] or not report['within_character_limit']:
        raise ValueError('Unresolved editorial exception')
    for filename, key in [('linkedin-post.md', 'full'), ('linkedin-post-compact.md', 'compact')]:
        text = (folder / filename).read_text()
        if len(text) != report['character_counts'][key] or len(text) > report['character_counts']['limit']:
            raise ValueError('Character count or limit mismatch')
        last = -1
        for e in expected:
            for part in (e['title'], e['organizer'], editorial_registration_url(e), central_time(e), pricing_label(e)):
                if part not in text:
                    raise ValueError(f'Essential event detail missing for {e["event_id"]}: {part}')
            position = text.find(e['title'])
            if position < last:
                raise ValueError('Events are not in chronological order')
            last = position
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--as-of', type=date.fromisoformat)
    args = parser.parse_args()
    print(validate_output(args.root, args.as_of))
