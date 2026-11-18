"""Validate generated captions against the current canonical/approval collection."""
import argparse
from pathlib import Path
import hashlib
from datetime import date, datetime
from pipeline import ROOT, CENTRAL, read, target, week, dt, eligible


def validate_output(root=ROOT, day=None):
    root=Path(root)
    label=target(day or datetime.now(CENTRAL).date())
    folder=root/'weeks'/label
    report=read(folder/'editorial-report.json')
    reviews=read(root/'data/reviews.json')
    events=read(root/'data/canonical-events.json')
    expected=[e for e in events if week(dt(e['start_datetime']))==label and e.get('roundup_week')==label and eligible(e,reviews,root)]
    if {e['event_id'] for e in expected}!={e['event_id'] for e in report['events_included']}:
        raise ValueError('Generated membership differs from all eligible target-week events')
    if report['roundup_identifier']!=label or report['publication_approval_status']!='awaiting_final_human_review':
        raise ValueError('Incorrect week or publication approval status')
    for filename,key in [('canonical-events.json','canonical_sha256'),('reviews.json','reviews_sha256')]:
        if hashlib.sha256((root/'data'/filename).read_bytes()).hexdigest()!=report[key]:
            raise ValueError('Source data changed after generation')
    if report['editorial_exceptions'] or not report['within_character_limit']:
        raise ValueError('Unresolved editorial exception')
    for filename,key in [('linkedin-post.md','full'),('linkedin-post-compact.md','compact')]:
        text=(folder/filename).read_text()
        if len(text)!=report['character_counts'][key] or len(text)>report['character_counts']['limit']:
            raise ValueError('Character count or limit mismatch')
        for e in expected:
            if any(part not in text for part in (e['title'],e['organizer'],e['registration_url'])):
                raise ValueError('Essential event detail missing')
            if dt(e['start_datetime']).astimezone(CENTRAL).tzname() not in text:
                raise ValueError('Central timezone notation missing')
    return folder


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--as-of',type=date.fromisoformat)
    args=parser.parse_args()
    print(validate_output(args.root,args.as_of))
