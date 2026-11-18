"""Record an explicitly authorized owner decision, never synthesize individual observations.

Use only after the owner supplies the source approval. This is a local reviewed mutation,
not part of scheduled generation. Source files live under approvals/ and are hash-bound.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from pipeline import ROOT, CLAIMS, read, write, fingerprint, dt, approval_problem


def record(root, event_ids, reviewer, source_path, statement, recorded_at=None, select=False):
    root=Path(root)
    source=(root/source_path).resolve()
    source.relative_to((root/'approvals').resolve())
    content=source.read_bytes()
    if not statement.strip() or statement not in content.decode('utf-8'):
        raise ValueError('Approval statement must appear verbatim in the owner-supplied source')
    if not reviewer.strip(): raise ValueError('Human reviewer identity required')
    recorded_at=recorded_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    dt(recorded_at)
    events=read(root/'data/canonical-events.json')
    reviews=read(root/'data/reviews.json')
    if not event_ids or set(event_ids)-{e['event_id'] for e in events}:
        raise ValueError('Select explicit existing event IDs')
    for e in events:
        if e['event_id'] not in event_ids: continue
        if e['conflict_flags']: raise ValueError('Resolve conflicts before recording approval')
        e['updated_at']=recorded_at
        e['verification_status']='verified'
        # The user did not supply the historical time they checked sources. Do not invent it.
        e['last_verified_at']=None
        e['editorial_status']='selected' if select else 'pending'
        review=dict(record_sha256=fingerprint(e),decision='verified',editorial_decision='selected' if select else 'pending',reviewer=reviewer,verified_at=None,score=0,claims={},
                    attestation=dict(type='explicit_owner_approval',authority='repository_owner',recorded_at=recorded_at,source_path=source.relative_to(root.resolve()).as_posix(),source_sha256=hashlib.sha256(content).hexdigest(),statement=statement,covered_claims=sorted(CLAIMS-{'price'}),pricing_confirmed=False))
        reviews[e['event_id']]=review
        # Check full contract with selection forced only for validation; no approval inferred.
        validation_reviews=dict(reviews)
        validation_reviews[e['event_id']]=dict(review,editorial_decision='selected')
        issue=approval_problem(e,validation_reviews,root)
        if issue: raise ValueError(f'Cannot record {e["event_id"]}: {issue}')
    write(root/'data/canonical-events.json',events)
    write(root/'data/reviews.json',reviews)
    return reviews


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--event-ids',nargs='+',required=True)
    parser.add_argument('--reviewer',required=True)
    parser.add_argument('--source',required=True)
    parser.add_argument('--statement',required=True)
    parser.add_argument('--recorded-at')
    parser.add_argument('--select',action='store_true',help='Use only when owner also authorizes editorial inclusion')
    args=parser.parse_args()
    record(args.root,args.event_ids,args.reviewer,args.source,args.statement,args.recorded_at,args.select)
