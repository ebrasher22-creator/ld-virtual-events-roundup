"""Deterministic, offline intake and human-reviewed editorial pipeline (Python 3.11+)."""
import argparse
import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ZoneInfo('America/Chicago')
SCHEMA = json.loads((ROOT/'schemas/event-discovery.schema.json').read_text())
REQUIRED = set(SCHEMA['items']['required'])

def read(path):
    return json.loads(Path(path).read_text())

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n')

def url(value):
    if not isinstance(value, str) or re.search(r'\s', value):
        raise ValueError('URL must be a string without whitespace')
    p = urlsplit(value)
    if p.scheme not in {'https','http'} or not p.hostname or '.' not in p.hostname or p.username or p.password:
        raise ValueError('absolute HTTP(S) URL required')
    if p.port and p.port not in {80,443}:
        raise ValueError('nonstandard URL port')
    query = sorted((k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'})
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/') or '/',urlencode(query),''))

def dt(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',value):
        raise ValueError('RFC3339 timestamp with explicit offset required')
    result = datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('timezone-aware timestamp required')
    return result

def schema_validate(value, spec, location='intake'):
    """Validate the documented subset used by our schema, not arbitrary JSON Schema."""
    types = spec.get('type', [])
    if isinstance(types,str): types=[types]
    matches = {
        'null': value is None,
        'string': isinstance(value,str),
        'number': isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value),
        'object': isinstance(value,dict),
        'array': isinstance(value,list),
    }
    if types and not any(matches.get(kind,False) for kind in types):
        raise ValueError(f'{location}: expected {types}')
    if 'enum' in spec and value not in spec['enum']:
        raise ValueError(f'{location}: expected one of {spec["enum"]}')
    if value is None: return
    if isinstance(value,dict):
        if set(spec.get('required',[]))-value.keys():
            raise ValueError(f'{location}: missing {sorted(set(spec["required"])-value.keys())}')
        properties=spec.get('properties',{})
        if spec.get('additionalProperties') is False and value.keys()-properties.keys():
            raise ValueError(f'{location}: unknown fields {sorted(value.keys()-properties.keys())}')
        for key,item in value.items():
            if key in properties: schema_validate(item,properties[key],f'{location}.{key}')
    if isinstance(value,list):
        if len(value)<spec.get('minItems',0): raise ValueError(f'{location}: array is empty')
        if spec.get('uniqueItems') and len({json.dumps(x,sort_keys=True) for x in value})!=len(value):
            raise ValueError(f'{location}: duplicate array members')
        for index,item in enumerate(value): schema_validate(item,spec.get('items',{}),f'{location}[{index}]')
    if isinstance(value,str):
        if len(value)<spec.get('minLength',0) or ('pattern' in spec and not re.search(spec['pattern'],value)):
            raise ValueError(f'{location}: empty text or invalid pattern')
        if spec.get('format')=='uri': url(value)
        if spec.get('format')=='date-time': dt(value)
    if isinstance(value,(float,int)) and not isinstance(value,bool) and 'minimum' in spec and value<spec['minimum']:
        raise ValueError(f'{location}: below minimum')


def validate(e):
    schema_validate(e,SCHEMA['items'])
    start=dt(e['start_datetime'])
    zone=ZoneInfo(e['timezone'])
    # UTC is a portable instant. Explicit non-UTC local offsets must agree with the zone.
    for field in ('start_datetime','end_datetime'):
        if e.get(field):
            timestamp=dt(e[field])
            if timestamp.utcoffset()!=timedelta(0) and timestamp.astimezone(zone).utcoffset()!=timestamp.utcoffset():
                raise ValueError(field + ': local offset disagrees with timezone (including DST)')
    if e.get('end_datetime') and dt(e['end_datetime'])<=start:
        raise ValueError('end must follow start')
    return e

def normalized(value):
    return re.sub(r'\W+', ' ',value.casefold()).strip()

def fingerprint(e):
    return hashlib.sha256(json.dumps(e,sort_keys=True).encode()).hexdigest()

def week(value):
    day = value.astimezone(CENTRAL).date() if isinstance(value,datetime) else value
    sunday = day - timedelta(days=(day.weekday()+1)%7)
    monday = sunday + timedelta(days=1)
    return f'{monday.isocalendar().year}/RW{monday.isocalendar().week:02d}_{sunday}_to_{sunday+timedelta(days=6)}'

def target(day):
    return week(day + timedelta(days=7-(day.weekday()+1)%7))

def ingest(root=ROOT):
    events = read(root/'data/canonical-events.json')
    for path in sorted((root/'intake').glob('*/*.json')):
        batch = read(path)
        if not isinstance(batch,list): raise ValueError('intake file must contain an array')
        for e in batch: validate(e)
    # Validate the entire intake before mutating persisted output.
    for path in sorted((root/'intake').glob('*/*.json')):
        for raw in read(path):
            e = json.loads(json.dumps(raw))
            e['registration_url'] = url(e['registration_url'])
            digest = fingerprint(raw)
            match = next((x for x in events if e['registration_url'] in x.get('registration_aliases',[x['registration_url']]) or (normalized(x['title']) == normalized(e['title']) and normalized(x['organizer']) == normalized(e['organizer']) and dt(x['start_datetime']) == dt(e['start_datetime']))),None)
            if match is None:
                match = {k:v for k,v in e.items() if k not in {'event_id','verification_status','last_verified_at','editorial_status','editorial_score','roundup_week','conflict_flags','updated_at'}}
                match.update(event_id='evt_'+hashlib.sha256(e['registration_url'].encode()).hexdigest()[:16],verification_status='pending',last_verified_at=None,editorial_status='pending',editorial_score=0,roundup_week=None,conflict_flags=[],updated_at=e['discovered_at'],submissions=[],registration_aliases=[e['registration_url']])
                events.append(match)
            if any(x['sha256']==digest for x in match['submissions']): continue
            for field in ('title','organizer','start_datetime','end_datetime','timezone','event_format','price_type','registration_url'):
                if (dt(match[field]) if field in {'start_datetime','end_datetime'} and match.get(field) else match.get(field)) != (dt(e[field]) if field in {'start_datetime','end_datetime'} and e.get(field) else e.get(field)):
                    match['conflict_flags'] = sorted(set(match['conflict_flags']+[field]))
            for field in ('discovered_by','source_urls'):
                match[field] = sorted(set(match[field]+e[field]))
            match['registration_aliases'] = sorted(set(match['registration_aliases']+[e['registration_url']]))
            match['submissions'].append({'sha256':digest,'file':str(path.relative_to(root)),'raw':raw})
            match['submissions'].sort(key=lambda x:x['sha256'])
            match['updated_at'] = max(match['updated_at'], e['discovered_at'])
            # Any new submission invalidates previous review, even if apparently corroborating.
            match['verification_status']='pending'
            match['last_verified_at']=None
            match['editorial_status']='pending'
    write(root/'data/canonical-events.json', sorted(events,key=lambda x:x['event_id']))
    return events

CLAIMS = {'relevance','virtual_availability','datetime','registration_url','organizer','status','price'}

def approval_problem(e, reviews, root=ROOT):
    """Return an exclusion reason; trust only current, separately persisted human reviews."""
    review = reviews.get(e.get('event_id'), {})
    if not isinstance(review,dict): return 'invalid_review'
    if review.get('record_sha256') != fingerprint(e): return 'missing_or_stale_approval'
    if review.get('decision') != 'verified': return 'not_human_approved'
    if review.get('editorial_decision') != 'selected': return 'not_editorially_selected'
    if e.get('conflict_flags'): return 'unresolved_conflicts'
    if e.get('event_format') not in {'virtual','hybrid'}: return 'not_live_virtual_or_hybrid'
    if e.get('price_type') not in {'free','paid','unknown'}: return 'invalid_price_type'
    try:
        # Canonical enrichment is outside the discovery schema; validate its discovery fields.
        validate({k:v for k,v in e.items() if k in SCHEMA['items']['properties']})
        if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():
            return 'missing_human_reviewer'
        attestation=review.get('attestation')
        if attestation is not None:
            if not isinstance(attestation,dict): return 'invalid_attestation'
            if attestation.get('type')!='explicit_owner_approval' or attestation.get('authority')!='repository_owner':
                return 'invalid_attestation'
            if not (CLAIMS-{'price'}) <= set(attestation['covered_claims']): return 'incomplete_attestation_scope'
            dt(attestation['recorded_at'])
            source=(Path(root)/attestation['source_path']).resolve()
            source.relative_to((Path(root)/'approvals').resolve())
            content=source.read_bytes()
            if hashlib.sha256(content).hexdigest()!=attestation['source_sha256']: return 'changed_attestation_source'
            statement=attestation['statement']
            if not isinstance(statement,str) or not statement.strip() or statement not in content.decode('utf-8'):
                return 'unsubstantiated_attestation'
        else:
            dt(review['verified_at'])
            for key in CLAIMS-{'price'}:
                item=review['claims'][key]
                url(item['primary_url'])
                if not isinstance(item['observation'],str) or not item['observation'].strip():
                    return 'incomplete_human_observations'
    except (KeyError,ValueError,TypeError,AttributeError,OSError):
        return 'invalid_human_review_or_event'
    return None


def eligible(e, reviews, root=ROOT):
    return approval_problem(e,reviews,root) is None


def confirmed_price_label(e, review):
    """Preserve raw price_type; display a label only with explicit price support."""
    if e.get('price_type') not in {'free','paid'}: return None
    claims=review.get('claims') or {}
    price=claims.get('price',{}) if isinstance(claims,dict) else {}
    try:
        url(price['primary_url'])
        if isinstance(price['observation'],str) and price['observation'].strip():
            return e['price_type'].title()
    except (KeyError,TypeError,ValueError): pass
    # An owner may explicitly attest pricing separately; general approval does not infer it.
    if isinstance(review.get('attestation'),dict) and review['attestation'].get('pricing_confirmed') is True:
        return e['price_type'].title()
    return None

def assign(root=ROOT, day=None):
    day = day or datetime.now(CENTRAL).date()
    events = read(root/'data/canonical-events.json')
    for e in events: e['roundup_week'] = week(dt(e['start_datetime']))
    write(root/'data/canonical-events.json',events)
    write(root/'data/future-events.json',[e for e in events if dt(e['start_datetime']).astimezone(CENTRAL).date() > date.fromisoformat(target(day).split('_to_')[1])])
    return events

def generate(root=ROOT, day=None, generated_at=None):
    from editorial import generate_week
    return generate_week(Path(root), day, generated_at)

def main(command):
    parser=argparse.ArgumentParser()
    parser.add_argument('--as-of',type=date.fromisoformat,help='Discovery date; Tuesday 2026-11-24 targets Nov 29–Dec 5')
    parser.add_argument('--root',type=Path,default=ROOT,help='Repository-shaped data root for isolated manual demonstrations')
    parser.add_argument('files',nargs='*')
    args=parser.parse_args()
    if command=='validate':
        for path in args.files or sorted((args.root/'intake').glob('*/*.json')):
            batch=read(path)
            if not isinstance(batch,list): raise ValueError('expected array')
            for e in batch: validate(e)
    elif command=='ingest': ingest(args.root)
    elif command=='assign_weeks': assign(args.root,day=args.as_of)
    elif command=='generate_post': print(generate(args.root,day=args.as_of))
