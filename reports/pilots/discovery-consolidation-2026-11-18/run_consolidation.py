"""Supervised consolidation experiment. Never writes repository intake/data/approvals/weeks.
Run: python3 reports/pilots/discovery-consolidation-2026-11-18/run_consolidation.py
"""
from collections import Counter
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from pipeline import (read,write,validate,normalized,url,dt,week,fingerprint,eligible,
                      approval_problem)
from validate_work_caption import validate_submission

DAY=date(2026,11,24)
TARGET='2026/RW49_2026-11-29_to_2026-12-05'
ORIGINALS=OUT/'originals'
FILES={'chatgpt':ORIGINALS/'chatgpt/chatgpt-2026-11-18-pilot.json',
       'antigravity':ORIGINALS/'antigravity/gemini-2026-11-18.json'}
INTAKE={'chatgpt':'intake/chatgpt/chatgpt-2026-11-18-pilot.json',
        'antigravity':'intake/gemini/gemini-2026-11-18.json'}
ALIASES={'ispring solutions':'ispring','training industry inc':'training industry'}
# Scoped comparison proposals, supported by exact shared URLs/title/time and supplied domains.
# Not a production/global alias registry and never a new verification assertion.
ALIAS_DOMAINS={'ispring':'ispringsolutions.com','training industry':'trainingindustry.com'}
commands=[]
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(args):
    result=subprocess.run([sys.executable]+[str(x) for x in args],cwd=ROOT,capture_output=True,text=True)
    commands.append(dict(command=['python3']+[str(x) for x in args],exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
    return result

def organizer(e):
    name=normalized(e['organizer'])
    mapped=ALIASES.get(name,name)
    domain=ALIAS_DOMAINS.get(mapped)
    if domain and any((urlsplit(e.get(key) or '').hostname or '').removeprefix('www.')==domain for key in ['event_url','registration_url','organizer_url']):
        return mapped
    return name

def identity(a,b):
    if url(a['registration_url'])==url(b['registration_url']):return 'normalized_registration_url'
    if normalized(a['title'])==normalized(b['title']) and organizer(a)==organizer(b) and dt(a['start_datetime'])==dt(b['start_datetime']):
        return 'normalized_title_scoped_organizer_alias_same_UTC_start'
    return None

def classify(field,a,b):
    if field in {'start_datetime','end_datetime'}:
        if a is not None and b is not None and dt(a)==dt(b):return 'timestamp_representation_only'
        return 'proposed_enrichment' if a is None or b is None else 'substantive_conflict'
    if field=='title' and normalized(a)==normalized(b):return 'capitalization_punctuation_only'
    if field=='organizer':
        return 'scoped_organizer_alias' if ALIASES.get(normalized(a),normalized(a))==ALIASES.get(normalized(b),normalized(b)) else 'substantive_conflict'
    if field=='registration_url':return 'tracking_slash_only' if url(a)==url(b) else 'registration_destination_proposal'
    if field=='language' and {str(a).lower(),str(b).lower()} <= {'en','english'}:return 'language_label_only'
    if a is None or b is None:return 'proposed_enrichment'
    if field=='summary':return 'unreviewed_description_variant'
    if field in {'audience','topics'}:return 'unreviewed_editorial_context_variant'
    if field=='event_url':return 'additional_source_location'
    return 'substantive_conflict'


def main():
    tracked=subprocess.check_output(['git','ls-tree','-r','--name-only','d019b05'],cwd=ROOT,text=True).splitlines()
    protected={name:digest(ROOT/name) for name in tracked if (ROOT/name).is_file()}
    approved=json.loads(subprocess.check_output(['git','show','d019b05:data/canonical-events.json'],cwd=ROOT,text=True))
    reviews=json.loads(subprocess.check_output(['git','show','d019b05:data/reviews.json'],cwd=ROOT,text=True))
    assert len(approved)==7 and all(eligible(e,reviews,ROOT) for e in approved)
    current_canonical=read(ROOT/'data/canonical-events.json')
    current_reviews=read(ROOT/'data/reviews.json')
    assert len(current_canonical)==11 and sum(eligible(e,current_reviews,ROOT) for e in current_canonical)==7
    approved_by_raw={s['sha256']:e for e in approved for s in e['submissions']}
    records=[]
    for stream,path in FILES.items():
        data=read(path)
        assert len(data)==7
        for index,raw in enumerate(data):
            validate(raw)
            records.append(dict(stream=stream,index=index+1,file=INTAKE[stream],raw_sha256=fingerprint(raw),raw=raw))
        result=run(['scripts/validate.py',path.relative_to(ROOT)])
        assert result.returncode==0,result.stderr
    # Byte preservation against exact pinned Git objects, not just a rewritten JSON parse.
    for entry in read(ORIGINALS/'manifest.json'):
        content=subprocess.check_output(['git','show',entry['ref']+':'+entry['repository_path']],cwd=ROOT)
        assert content==(ORIGINALS/entry['preserved_path']).read_bytes()
        assert hashlib.sha256(content).hexdigest()==entry['sha256']

    with tempfile.TemporaryDirectory(prefix='ld-consolidation-') as temporary:
        tmp=Path(temporary)
        def sandbox(name,seed=False,reverse=False):
            root=tmp/name
            root.mkdir()
            for folder in ['config','templates','approvals']:shutil.copytree(ROOT/folder,root/folder)
            write(root/'data/canonical-events.json',approved if seed else [])
            write(root/'data/reviews.json',reviews if seed else {})
            for stream in FILES:
                dest=root/INTAKE[stream];dest.parent.mkdir(parents=True,exist_ok=True)
                if reverse:write(dest,list(reversed(read(FILES[stream]))))
                else:shutil.copy(FILES[stream],dest)
            return root
        def ingest_assign(root):
            for script in ['validate','ingest','assign_weeks']:
                result=run([f'scripts/{script}.py','--root',root,'--as-of',DAY.isoformat()])
                assert result.returncode==0,result.stderr
        fresh=sandbox('native-fresh')
        ingest_assign(fresh)
        native=read(fresh/'data/canonical-events.json')
        native_future=read(fresh/'data/future-events.json')
        assert len(native)==11 and len(native_future)==5
        native_hashes={name:digest(fresh/'data'/name) for name in ['canonical-events.json','future-events.json']}
        ingest_assign(fresh)
        assert native_hashes=={name:digest(fresh/'data'/name) for name in native_hashes}
        assert all(e['verification_status']=='pending' and e['last_verified_at'] is None for e in native)
        assert run(['scripts/generate_post.py','--root',fresh,'--as-of',DAY.isoformat()]).returncode==0
        assert read(fresh/'weeks'/TARGET/'review.json')['selected_ids']==[]
        write(OUT/'native-fresh/canonical-preview.json',native)
        write(OUT/'native-fresh/future-preview.json',native_future)
        # A reverse-order characterization, not an assumption of order independence.
        reversed_root=sandbox('native-reversed',reverse=True)
        ingest_assign(reversed_root)
        reversed_events=read(reversed_root/'data/canonical-events.json')
        reverse_same=native==reversed_events
        seeded=sandbox('native-seeded-with-approved',seed=True)
        ingest_assign(seeded)
        mutated=read(seeded/'data/canonical-events.json')
        seeded_reviews=read(seeded/'data/reviews.json')
        assert len(mutated)==11 and sum(eligible(e,seeded_reviews,seeded) for e in mutated)==7
        mutated_by_id={e['event_id']:e for e in mutated}
        affected=[]
        for old in approved:
            new=mutated_by_id[old['event_id']]
            if fingerprint(old)!=fingerprint(new):
                latest=max([dt(old['updated_at'])]+[dt(s['raw']['discovered_at']) for s in new['submissions']])
                affected.append(dict(event_id=old['event_id'],title=old['title'],before_sha256=fingerprint(old),after_sha256=fingerprint(new),approval_problem=approval_problem(new,seeded_reviews,seeded),native_conflict_flags=new['conflict_flags'],updated_at_chronologically_current=dt(new['updated_at'])==latest,migration=seeded_reviews[old['event_id']].get('migration')))
        assert len(affected)==3 and all(a['approval_problem'] is None and a['updated_at_chronologically_current'] and a['migration'] for a in affected)
        work_input=ROOT/'weeks'/TARGET/'editorial-input.json'
        work_draft=ROOT/'editorial-drafts/RW49_2026-11-29_to_2026-12-05/work-submission.json'
        seeded_validation=validate_submission(seeded,work_input,work_draft,tmp/'seeded-work-validation')
        assert seeded_validation['mechanical_validation_passed']
        write(OUT/'native-seeded/approval-impact.json',dict(changed_approved_records=affected,total_native_records=len(mutated),still_eligible_approved=sum(eligible(e,seeded_reviews,seeded) for e in mutated),work_input_validation=seeded_validation))
        write(OUT/'native-seeded/canonical-preview-NOT-APPROVED.json',mutated)

        # An isolated review projection groups identities with narrowly supported name aliases.
        groups=[]
        match_reasons=[]
        for submission in records:
            matches=[g for g in groups if any(identity(submission['raw'],member['raw']) for member in g)]
            assert len(matches)<=1,'Ambiguous identity must be quarantined rather than guessed'
            if matches:
                group=matches[0]
                reason=next(identity(submission['raw'],m['raw']) for m in group if identity(submission['raw'],m['raw']))
                match_reasons.append(dict(left=group[0]['file']+':'+str(group[0]['index']),right=submission['file']+':'+str(submission['index']),reason=reason))
                group.append(submission)
            else:groups.append([submission])
        projections=[]
        differences=[]
        skipped={'event_id','discovered_by','source_urls','discovered_at','evidence','verification_status','last_verified_at','editorial_status','editorial_score','roundup_week','conflict_flags','updated_at'}
        factual_fields=set(read(ROOT/'schemas/event-discovery.schema.json')['items']['properties'])-skipped
        for group in groups:
            known=[approved_by_raw[m['raw_sha256']] for m in group if m['raw_sha256'] in approved_by_raw]
            if known:
                event=copy.deepcopy(known[0])
                assert all(e['event_id']==event['event_id'] for e in known)
            else:
                event=copy.deepcopy(next(e for e in native if url(e['registration_url'])==url(group[0]['raw']['registration_url'])))
            event_differences=[]
            if len(group)>1:
                old=group[0]['raw']
                for member in group[1:]:
                    for field in sorted(factual_fields):
                        a,b=old.get(field),member['raw'].get(field)
                        if a==b:continue
                        kind=classify(field,a,b)
                        event_differences.append(dict(field=field,chatgpt_value=a,antigravity_value=b,classification=kind,adopted=False,review_needed_if_adopted=kind not in {'capitalization_punctuation_only','scoped_organizer_alias','tracking_slash_only','language_label_only','timestamp_representation_only'}))
            projection=dict(event_id=event['event_id'],title=event['title'],roundup_week=event['roundup_week'],approved_version=bool(known),approved_version_eligible=bool(known) and eligible(event,reviews,ROOT),
                            preserved_event_version=event,discovery_streams=sorted({m['stream'] for m in group}),organizer_names_preserved=sorted({m['raw']['organizer'] for m in group}),source_urls=sorted(set(event['source_urls']).union(*(set(m['raw']['source_urls']) for m in group))),
                            raw_submissions=sorted(group,key=lambda m:(m['stream'],m['raw_sha256'])),unreviewed_differences=event_differences,new_discovery_details_approved=False)
            projections.append(projection)
            if event_differences:differences.append(dict(event_id=event['event_id'],title=event['title'],differences=event_differences))
        projections.sort(key=lambda p:(dt(p['preserved_event_version']['start_datetime']),p['event_id']))
        assert len(projections)==11
        assert sum(p['approved_version'] for p in projections)==7
        assert sum(not p['approved_version'] for p in projections)==4
        assert all(fingerprint(p['preserved_event_version'])==fingerprint(next(e for e in approved if e['event_id']==p['event_id'])) for p in projections if p['approved_version'])
        assert sum(len(p['raw_submissions']) for p in projections)==14
        assert all(all(m['raw_sha256']==fingerprint(m['raw']) for m in p['raw_submissions']) for p in projections)
        future=[p for p in projections if dt(p['preserved_event_version']['start_datetime']).date()>date(2026,12,5)]
        assert len(future)==5
        week_counts=[]
        for label in sorted({p['roundup_week'] for p in projections}):
            members=[p for p in projections if p['roundup_week']==label]
            week_counts.append(dict(roundup_week=label,distinct_discovery_candidates=len(members),already_approved_eligible=sum(p['approved_version_eligible'] for p in members),new_pending=sum(not p['approved_version'] for p in members),chatgpt=sum('chatgpt' in p['discovery_streams'] for p in members),antigravity=sum('antigravity' in p['discovery_streams'] for p in members),both=sum(len(p['discovery_streams'])==2 for p in members)))
        write(OUT/'reconciled-review-groups.json',projections)
        write(OUT/'reconciled-future-groups.json',future)
        write(OUT/'cross-stream-differences.json',dict(match_reasons=match_reasons,groups=differences,policy='Frozen approved versions retained; all other proposed facts remain unreviewed. No production alias/config/data mutation.'))
        # No mutation of the root approved input/draft; prove it is still mechanically valid.
        root_validation=validate_submission(ROOT,work_input,work_draft,tmp/'original-work-validation')
        assert root_validation['mechanical_validation_passed']
        write(OUT/'preserved-work-validation.json',root_validation)
        summary=dict(result='PASS',as_of=DAY.isoformat(),target_week=TARGET,chatgpt_records=7,antigravity_records=7,total_submissions=14,
                     shared_intake_events=3,unique_to_chatgpt_intake=4,unique_to_antigravity_intake=4,distinct_reconciled_candidates=11,already_approved_eligible=7,new_pending=4,unique_future_events=5,by_week=week_counts,
                     native_current_pipeline=dict(fresh_events=len(native),fresh_future_events=len(native_future),conflict_records=sum(bool(e['conflict_flags']) for e in native),all_pending_without_reviews=True,exact_rerun_idempotent=True,reversed_input_records_byte_equal=reverse_same,missed_cross_stream_duplicate=None,description_variants_flagged=all('summary' in e['conflict_flags'] for e in native if len(e['submissions'])>1),conflicting_evidence_preserved=all(len(e['evidence'])>1 for e in native if len(e['submissions'])>1)),
                     seeded_native_approval_migrations=affected,work_input_would_be_stale_with_native_integration=False,preserved_work_submission_still_passes=True,
                     alias_policy='Two scoped organizer equivalences backed by supplied shared URLs/domains, matching title and instant; original names/evidence all retained.',
                     verification_claim='No new event verification performed; discovery evidence remains agent-supplied. Existing unchanged owner approvals retained via audited approval-fingerprint migration.',source_commits=dict(chatgpt='d019b05',antigravity='93f8715'),production_data_modified=True,approvals_refreshed=False,audited_approval_migrations=len(affected),new_events_selected=False)
        write(OUT/'acceptance-results.json',summary)
    assert protected=={name:digest(ROOT/name) for name in protected}
    write(OUT/'preservation-proof.json',dict(all_preexisting_tracked_files_unchanged=True,baseline='d019b05',before=protected,after=protected))
    write(OUT/'command-results.json',commands)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
