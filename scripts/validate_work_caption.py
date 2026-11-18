"""Validate submitted AI prose around immutable event fact blocks. Never executes draft data."""
import argparse
from datetime import date, datetime, timezone
from pathlib import Path
import re
from pipeline import ROOT, read, write, fingerprint, schema_validate
from editorial_input import build_input

DRAFT_SCHEMA=read(ROOT/'schemas/editorial-submission.schema.json')


def check_caption(text, payload):
    errors=[]
    if '\r' in text: errors.append('Use LF line endings')
    if '```' in text: errors.append('Caption must be plain text, without Markdown fences')
    if len(text)>payload['constraints']['character_limit']: errors.append('Character limit exceeded')
    heading=payload['required_heading']
    if text.count(heading)!=1: errors.append('Exact roundup heading required once')
    remaining=text.replace(heading,'',1)
    previous=-1
    for e in payload['events']:
        block=e['required_fact_block']
        count=text.count(block)
        if count!=1:
            errors.append(f'{e["event_id"]}: required title/organizer/date/time/zone/URL/price block must occur exactly once (found {count})')
        position=text.find(block)
        if position>=0:
            if position<previous: errors.append('Event order differs from approved chronological input')
            previous=position
            # Require complete paragraphs, preventing facts hidden in longer false statements.
            before=text[:position]
            after=text[position+len(block):]
            if before and not before.endswith('\n\n'): errors.append(f'{e["event_id"]}: separate fact block with a blank line')
            if after and after!='\n' and not after.startswith('\n\n'): errors.append(f'{e["event_id"]}: extra or attached event facts')
        remaining=remaining.replace(block,'',1)
    # Required blocks already contain every approved URL and factual date/time. Reject extra
    # event assertions/links in creative prose; this is deliberately a strict, documented contract.
    if re.search(r'(?:https?://|www\.)\S+',remaining,re.I): errors.append('Extra/changed registration or other URL outside approved fact blocks')
    if re.search(r'\d',remaining): errors.append('Numeric/date/time claim outside immutable heading/fact blocks')
    if re.search(r'\b(?:CST|CDT|EST|EDT|ET|CT|PT|PST|PDT|UTC|GMT|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',remaining,re.I):
        errors.append('Date/timezone claim outside approved fact blocks')
    if re.search(r'\b(?:free|paid|complimentary|no.cost)\b|[$€£]',remaining,re.I): errors.append('Price claim outside approved fact blocks')
    if len(re.findall(r'(?<!\w)#[\w]+',text))>payload['constraints']['maximum_hashtags']:
        errors.append('Too many hashtags')
    if not remaining.strip(): errors.append('Add audience-centered framing and an authentic CTA, not only facts')
    return errors


def validate_submission(root, input_path, draft_path, output_dir):
    root=Path(root)
    output_dir=Path(output_dir)
    errors=[]
    payload={}
    draft={}
    try:
        payload=read(input_path)
        draft=read(draft_path)
    except (ValueError,OSError) as exc:
        errors.append('Cannot load exchange JSON: '+str(exc))
    if not isinstance(payload,dict):
        errors.append('Editorial input must be an object')
        payload={}
    if not isinstance(draft,dict):
        errors.append('Work submission must be an object')
        draft={}
    # Recreate the authority from current canonical data and trusted reviews, not from the AI.
    try:
        day=date.fromisoformat(payload['as_of'])
        expected=build_input(root,day)
        if payload!=expected: errors.append('Editorial input is stale, changed, or inconsistent with current approvals/configuration')
        unsigned={k:v for k,v in payload.items() if k!='editorial_input_sha256'}
        if fingerprint(unsigned)!=payload['editorial_input_sha256']: errors.append('Editorial input checksum mismatch')
        if expected['export_status']!='ready': errors.append('Approved editorial input is not ready')
        schema_validate(draft,DRAFT_SCHEMA,'work_submission')
        if draft['editorial_input_sha256']!=payload['editorial_input_sha256']: errors.append('Draft binds to a different editorial input')
        if draft['roundup_identifier']!=payload['roundup_identifier']: errors.append('Draft roundup week mismatch')
        for field in ['full_caption','compact_caption']:
            errors += [field+': '+reason for reason in check_caption(draft[field],expected)]
    except (ValueError,KeyError,TypeError,AttributeError) as exc:
        errors.append('Invalid exchange contract: '+str(exc))
    result=dict(result='pass' if not errors else 'fail',mechanical_validation_passed=not errors,errors=errors,
                validated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                editorial_input_sha256=payload.get('editorial_input_sha256'),submission_sha256=fingerprint(draft),
                character_counts={key:len(draft[key]) for key in ['full_caption','compact_caption'] if isinstance(draft.get(key),str)},
                semantic_review_required=True,publication_approval_status='awaiting_final_human_review',
                limitations=['Exact event facts and coverage are checked. Prose truthfulness, interpretation, audience sensitivity and editorial quality require human review.'])
    output_dir.mkdir(parents=True,exist_ok=True)
    write(output_dir/'validation-report.json',result)
    if not errors:
        (output_dir/'linkedin-work-post.md').write_text(draft['full_caption'])
        (output_dir/'linkedin-work-post-compact.md').write_text(draft['compact_caption'])
        (output_dir/'jarvis-handoff.md').write_text(f'''# Work editorial review handoff

Roundup: {payload['roundup_identifier']}
Event count: {len(payload['events'])}
Mechanical validation: PASS
Semantic review and final publication approval: PENDING

[Full Work draft](linkedin-work-post.md) · [Compact Work draft](linkedin-work-post-compact.md) · [Validation report](validation-report.json)

Check the creative framing for unsupported claims and brand/audience fit. No publication is authorized. Share this folder manually with the existing Jarvis briefing or the owner; do not assume automatic repository access.
''')
    else:
        # A failed resubmission must not leave old passing captions looking current.
        for name in ['linkedin-work-post.md','linkedin-work-post-compact.md','jarvis-handoff.md']:
            (output_dir/name).unlink(missing_ok=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--draft',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    result=validate_submission(args.root,args.input,args.draft,args.output_dir)
    print(result['result'].upper()+': '+str(args.output_dir/'validation-report.json'))
    raise SystemExit(0 if result['mechanical_validation_passed'] else 1)
