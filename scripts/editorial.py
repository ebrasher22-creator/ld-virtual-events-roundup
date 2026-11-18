"""Deterministic text preparation; reports never authorize publication."""
from datetime import datetime, timezone
import hashlib
import os
import subprocess
from pathlib import Path
from pipeline import (ROOT, CENTRAL, read, write, dt, week, target, fingerprint,
                      approval_problem, confirmed_price_label, editorial_registration_url)


def source_commit(root):
    result=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True)
    return result.stdout.strip() if result.returncode==0 else None


def render_events(events, reviews, include_descriptions):
    blocks=[]
    for e in events:
        start=dt(e['start_datetime']).astimezone(CENTRAL)
        # Explicit English names make output stable across OS locales.
        weekdays=('Mon','Tue','Wed','Thu','Fri','Sat','Sun')
        months=('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec')
        hour=start.hour%12 or 12
        time=f'{weekdays[start.weekday()]}, {months[start.month-1]} {start.day}, {start.year} | {hour}:{start.minute:02d} {"AM" if start.hour<12 else "PM"} {start.tzname()}'
        label=confirmed_price_label(e,reviews[e['event_id']])
        lines=[e['title'],e['organizer'],time+(f' | {label}' if label else '')]
        if e['event_format']=='hybrid': lines[-1]+=' | Hybrid (virtual access)'
        if include_descriptions: lines.append(e['summary'])
        lines.append(editorial_registration_url(e))
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks)


def build_caption(root, brand, label, body, intro, hashtags=True):
    period=label.split('_',1)[1].replace('_to_',' to ')
    template=(root/'templates/linkedin-roundup.md').read_text()
    # Python format cannot silently drop or truncate required event details.
    return template.format(brand=brand['name'],period=period,introduction=intro,
                           events=body,cta=brand['cta'],
                           hashtags=' '.join(brand.get('hashtags',[])) if hashtags else '').strip()+'\n'


def generate_week(root=ROOT, day=None, generated_at=None):
    day=day or datetime.now(CENTRAL).date()
    generated_at=generated_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    dt(generated_at)
    label=target(day)
    rules=read(root/'config/editorial-rules.yml')
    brand=read(root/'config/branding.yml')
    reviews=read(root/'data/reviews.json')
    events=read(root/'data/canonical-events.json')
    included=[]
    excluded=[]
    blockers=[]
    for e in events:
        actual_week=week(dt(e['start_datetime']))
        if actual_week!=label:
            reason='outside_target_week'
        elif e.get('roundup_week')!=actual_week:
            reason='incorrect_week_assignment'
        else:
            reason=approval_problem(e,reviews,root)
        if reason:
            excluded.append(dict(event_id=e['event_id'],title=e['title'],reason=reason,assigned_week=e.get('roundup_week')))
            review=reviews.get(e['event_id'],{})
            if actual_week==label and review.get('decision')=='verified' and review.get('editorial_decision')=='selected':
                blockers.append(dict(event_id=e['event_id'],reason=reason))
        else: included.append(e)
    # All eligible target-week events are retained; target_max is advisory, never a silent cap.
    included.sort(key=lambda e:(dt(e['start_datetime']),e['event_id']))
    body=render_events(included,reviews,rules.get('include_descriptions',False))
    essential=render_events(included,reviews,False)
    intro=brand['introduction']
    short=brand.get('compact_introduction','Learning opportunities for the week ahead.')
    limit=rules['linkedin_max_characters']
    full=build_caption(root,brand,label,body,intro)
    strategy='full'
    if len(full)>limit:
        full=build_caption(root,brand,label,body,short)
        strategy='shortened_introduction'
    if len(full)>limit:
        full=build_caption(root,brand,label,essential,short)
        strategy='essential_event_details'
    if len(full)>limit:
        full=build_caption(root,brand,label,essential,short,False)
        strategy='essential_details_without_hashtags'
    compact=build_caption(root,brand,label,essential,short,False)
    within_limit=len(full)<=limit and len(compact)<=limit
    exceptions=[]
    if not within_limit: exceptions.append('CHARACTER_LIMIT: all events retained; split or otherwise resolve with human approval. Do not publish this over-limit draft.')
    if blockers: exceptions.append('CURRENT_APPROVALS: target-week selected records have invalid/stale approvals; review required.')
    # Human approval and current-record validity are separate report fields.
    total_approved=0
    for e in events:
        if week(dt(e['start_datetime']))!=label: continue
        review=reviews.get(e['event_id'],{})
        # Count valid fact approvals even if editorial selection is separately withheld.
        fact_reviews={e['event_id']:dict(review,editorial_decision='selected')}
        if approval_problem(e,fact_reviews,root) is None: total_approved+=1
    run_url=None
    if os.environ.get('GITHUB_RUN_ID') and os.environ.get('GITHUB_REPOSITORY'):
        run_url=f"{os.environ.get('GITHUB_SERVER_URL','https://github.com')}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    report=dict(roundup_identifier=label,as_of=day.isoformat(),generated_at=generated_at,
                total_approved_events_for_target_week=total_approved,events_included=[dict(event_id=e['event_id'],title=e['title'],record_sha256=fingerprint(e)) for e in included],
                events_excluded=excluded,missing_optional_pricing=[dict(event_id=e['event_id'],title=e['title'],original_price_type=e['price_type'],reason='unknown_or_not_separately_confirmed') for e in included if confirmed_price_label(e,reviews[e['event_id']]) is None],
                character_counts=dict(full=len(full),compact=len(compact),limit=limit),within_character_limit=within_limit,
                below_target=len(included)<rules['target_min'],above_target=len(included)>rules['target_max'],target_min=rules['target_min'],target_max=rules['target_max'],
                advisories=['BELOW_TARGET: shorter roundup permitted; do not fill from other weeks.'] if len(included)<rules['target_min'] else [],
                source_commit=source_commit(root),canonical_sha256=hashlib.sha256((root/'data/canonical-events.json').read_bytes()).hexdigest(),reviews_sha256=hashlib.sha256((root/'data/reviews.json').read_bytes()).hexdigest(),
                publication_approval_status='awaiting_final_human_review',workflow_run_url=run_url,artifact_relative_path='weeks/'+label,editorial_exceptions=exceptions,approval_blockers=blockers,caption_strategy=strategy)
    folder=root/'weeks'/label
    folder.mkdir(parents=True,exist_ok=True)
    from editorial_input import export_input
    export_input(root,day)
    (folder/'linkedin-post.md').write_text(full)
    (folder/'linkedin-post-compact.md').write_text(compact)
    write(folder/'editorial-report.json',report)
    checklist='''# Final manual publication review

Publication approval: **awaiting final human review**. Event approval does not approve this caption.

- [ ] Confirm this is the intended Sunday–Saturday period and all events have current human approval.
- [ ] Review complete titles, organizer names, readability, spacing and date order.
- [ ] Confirm dates/times display Central Time as CST/CDT and registration links are intact.
- [ ] Confirm price labels have explicit support; omitted prices make no free-admission claim.
- [ ] Review the full and compact captions, character counts and any editorial exceptions.
- [ ] Accept the below-target advisory if applicable; do not add future or unapproved events.
- [ ] Recheck current event status/links as appropriate before manual publication.
- [ ] Explicitly approve the chosen final caption, then manually publish to LinkedIn.

Final reviewer: ______  Decision (approve / hold / reject): ______  Time: ______
'''
    (folder/'publication-checklist.md').write_text(checklist)
    handoff=f'''# Jarvis — Wednesday 8:00 AM briefing handoff

Roundup: {label}
Included event count: {len(included)}
Final publication approval: awaiting final human review
Preparation status: {'EDITORIAL EXCEPTION — HOLD' if exceptions else 'draft generated; human review required'}

Artifacts: [Full caption](linkedin-post.md), [compact caption](linkedin-post-compact.md), [editorial report](editorial-report.json), [publication checklist](publication-checklist.md).
Workflow run / artifact access: {run_url or "Local preparation; transfer this folder manually or use the separately reported Actions run link."}
Unresolved issues: {'; '.join(exceptions+report['advisories']) or 'No mechanical blockers; final editorial review remains required.'}
Optional pricing omitted for {len(report['missing_optional_pricing'])} events.

## Supported manual handoff

Download the Wednesday Actions artifact, or open this repository folder. Attach this file, the selected draft and editorial report to the intended Jarvis briefing/chat. Paste the exact caption below if attachment access is unavailable. Include the workflow run/artifact link when available; repository paths alone do not grant Jarvis access. No automatic Jarvis connection or duplicate briefing task was created. Final posting remains manual.

## Primary Work editorial handoff

Use editorial-input.json with agents/linkedin-editor-work.md for community-centered editorial writing. The caption below is the deterministic fallback, not a completed ChatGPT Work draft. Validate returned work-submission.json before sharing it as a mechanically validated candidate. No Work task was scheduled.

## Deterministic fallback draft

{full}'''
    (folder/'jarvis-handoff.md').write_text(handoff)
    # Backward-compatible filenames/review summary for existing consumers and historical smoke tests.
    (folder/'linkedin-roundup.md').write_text(full)
    (folder/'linkedin-compact.md').write_text(compact)
    write(folder/'review.json',dict(publication_status='human_review_required',selected_ids=[e['event_id'] for e in included],below_target=report['below_target'],full_length=len(full),compact_length=len(compact)))
    if exceptions: raise ValueError('Editorial exception; review generated editorial-report.json: '+'; '.join(exceptions))
    return folder
