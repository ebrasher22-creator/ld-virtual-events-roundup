"""Approved, immutable editorial exchange. No model calls or eligibility delegation."""
import argparse
from datetime import date, datetime
import hashlib
from pathlib import Path
from pipeline import (ROOT, CENTRAL, read, write, dt, week, target, fingerprint,
                      eligible, approval_problem, confirmed_price_label, editorial_registration_url)


def build_input(root=ROOT, day=None, generated_at=None):
    """Optional ChatGPT Work exchange, derived from the same automated qualification as the GitHub generator."""
    from editorial import evaluate_week, render_event, sha_file
    from qualification import CHECKS_PATH, pricing_label, load_checks
    from datetime import time as clock, timezone
    root=Path(root)
    day=day or datetime.now(CENTRAL).date()
    label=target(day)
    rules=read(root/'config/editorial-rules.yml')
    brand=read(root/'config/branding.yml')
    reference=dt(generated_at) if generated_at else datetime.combine(day,clock(0,0),tzinfo=CENTRAL)
    included,_,_=evaluate_week(root,label,reference,datetime.combine(day,clock(0,0),tzinfo=CENTRAL))
    checks=load_checks(root)
    events=[]
    for e in included:
        central=dt(e['start_datetime']).astimezone(CENTRAL)
        originals=sorted({s['raw']['registration_url'] for s in e.get('submissions',[]) if s.get('raw',{}).get('registration_url')})
        events.append(dict(event_id=e['event_id'],record_sha256=fingerprint(e),title=e['title'],organizer=e['organizer'],organizer_url=e.get('organizer_url'),event_url=e['event_url'],
                           start_datetime=e['start_datetime'],end_datetime=e.get('end_datetime'),timezone=e['timezone'],
                           start_central=central.isoformat(),central_timezone=central.tzname(),event_format=e['event_format'],language=e['language'],
                           registration_url=editorial_registration_url(e),canonical_registration_url=e['registration_url'],original_registration_urls=originals,
                           summary=e['summary'],summary_grounding='Exact canonical summary; no additional outcomes inferred.',
                           topics=e['topics'],audience=e['audience'],source_urls=e['source_urls'],
                           price_type_original=e['price_type'],cost_original=e.get('cost'),price_label=pricing_label(e),
                           registration_check=checks.get(e['event_id'],{}).get('classification'),
                           required_fact_block=render_event(e,rules.get('description_max_characters',220),True),qualification='automated'))
    period=label.split('_',1)[1].replace('_to_',' to ')
    payload=dict(format_version=2,roundup_identifier=label,as_of=day.isoformat(),required_heading=f'{brand["name"]} | {period}',
                 export_status='ready' if events else 'blocked',blocking_selected_record_count=0,
                 source_versions=dict(canonical_sha256=sha_file(root/'data/canonical-events.json'),registration_checks_sha256=sha_file(root/CHECKS_PATH)),
                 brand=dict(name=brand['name'],audience='Learning and development professionals, instructional designers, learning leaders and people-development practitioners',voice=['professional and conversational','community-centered','credible','specific without sales hype'],suggested_hashtags=brand.get('hashtags',[])),
                 constraints=dict(character_limit=rules['linkedin_max_characters'],maximum_hashtags=3,required_event_count=len(events),
                                  preserve_event_order=True,required_fact_blocks='Copy each block exactly once, in order, with blank lines separating it from other prose.',
                                  original_urls='Use registration_url exactly; no shortened URLs, rewritten paths or extra links.',
                                  creative_scope=['varied audience-centered hook','themes grounded in supplied summaries and topics','brief professional reflection, never invented personal experience','authentic participation CTA'],
                                  factual_prose_rule='Do not repeat or add dates, clock times, timezone tokens, prices, numeric claims or URLs outside the required heading/fact blocks.',
                                  pricing='Pricing appears only inside fact blocks.',
                                  eligibility='Fixed by automated qualification; no additions, omissions, swaps or future-week padding.',
                                  unsupported_claims='No new speakers, guarantees, personal anecdotes, statistics, scarcity, endorsements or outcomes; semantic accuracy still requires human review.',
                                  publication='Human final approval and manual posting only; validation is not publication approval.'),
                 editorial_advisories=dict(below_target=len(events)<rules['target_min'],target_min=rules['target_min'],target_max=rules['target_max'],minimum_is_not_a_gate=True),events=events)
    payload['editorial_input_sha256']=fingerprint(payload)
    return payload


def export_input(root=ROOT, day=None):
    payload=build_input(root,day)
    folder=Path(root)/'weeks'/payload['roundup_identifier']
    write(folder/'editorial-input.json',payload)
    write(folder/'work-submission-template.json',dict(format_version=1,roundup_identifier=payload['roundup_identifier'],editorial_input_sha256=payload['editorial_input_sha256'],full_caption='',compact_caption=''))
    write(Path(root)/'weeks/editorial-current.json',dict(roundup_identifier=payload['roundup_identifier'],as_of=payload['as_of'],export_status=payload['export_status'],editorial_input_path=(folder/'editorial-input.json').relative_to(Path(root)).as_posix(),editorial_input_sha256=payload['editorial_input_sha256'],event_count=len(payload['events']),agent_instructions_path='agents/linkedin-editor-work.md',return_path='editorial-drafts/'+payload['roundup_identifier'].split('/')[1]+'/work-submission.json',publication_approval_status='awaiting_final_human_review'))
    return folder/'editorial-input.json'


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--as-of',type=date.fromisoformat)
    args=parser.parse_args()
    print(export_input(args.root,args.as_of))
