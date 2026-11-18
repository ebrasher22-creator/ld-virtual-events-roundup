"""Deterministic, offline intake and human-reviewed editorial pipeline (Python 3.11+)."""
import argparse
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ZoneInfo('America/Chicago')
TOPICS = {'learning','instructional design','leadership','coaching','talent','hr technology','organizational development','performance improvement','knowledge management','evaluation','workforce enablement'}
REQUIRED = {'title','organizer','event_url','registration_url','start_datetime','timezone','event_format','language','price_type','summary','audience','topics','discovered_by','source_urls','discovered_at','evidence'}

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
    result = datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('timezone-aware timestamp required')
    return result

def validate(e):
    if not isinstance(e, dict) or REQUIRED - e.keys():
        raise ValueError('missing required fields: ' + str(REQUIRED - e.keys() if isinstance(e,dict) else REQUIRED))
    allowed = set(read(ROOT/'schemas/event-discovery.schema.json')['items']['properties'])
    if e.keys() - allowed: raise ValueError('unknown discovery fields')
    if e.get('cost') is not None and (isinstance(e['cost'],bool) or not isinstance(e['cost'],(int,float)) or e['cost'] < 0):
        raise ValueError('cost must be a nonnegative number or null')
    for field in ('title','organizer','summary','language'):
        if not isinstance(e[field],str) or not e[field].strip():
            raise ValueError(field + ' must be nonempty text')
    for field in ('audience','topics','discovered_by','source_urls','evidence'):
        if not isinstance(e[field],list):
            raise ValueError(field + ' must be an array')
    if not e['source_urls'] or not e['discovered_by'] or not set(e['discovered_by']) <= {'chatgpt','gemini'}:
        raise ValueError('source URLs and known discovery agents required')
    for field in ('event_url','registration_url','organizer_url'):
        if e.get(field) is not None: url(e[field])
    for value in e['source_urls']: url(value)
    start = dt(e['start_datetime'])
    zone = ZoneInfo(e['timezone'])
    if start.astimezone(zone).utcoffset() != start.utcoffset():
        raise ValueError('timestamp offset disagrees with timezone (including DST)')
    dt(e['discovered_at'])
    if e.get('end_datetime') and dt(e['end_datetime']) <= start:
        raise ValueError('end must follow start')
    if e['event_format'] not in {'virtual','hybrid','in_person','on_demand'} or e['price_type'] not in {'free','paid','unknown'}:
        raise ValueError('invalid format or price type')
    if not all(isinstance(x,str) for x in e['topics'] + e['audience']):
        raise ValueError('topics and audience must contain strings')
    for ev in e['evidence']:
        if not isinstance(ev,dict) or not {'claim','source_url','excerpt'} <= ev.keys():
            raise ValueError('evidence needs claim, source_url, excerpt')
        url(ev['source_url'])
        if not ev['claim'] or not ev['excerpt']: raise ValueError('empty evidence')
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
                if match.get(field) != e.get(field):
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

def eligible(e, reviews):
    review = reviews.get(e['event_id'],{})
    claims = review.get('claims',{})
    # Human review must bind to the exact current record, with independently checked evidence.
    if review.get('record_sha256') != fingerprint(e) or review.get('decision') != 'verified' or review.get('editorial_decision') != 'selected': return False
    try:
        dt(review['verified_at'])
        if not review['reviewer'].strip(): return False
        for key in CLAIMS:
            item = claims[key]
            url(item['primary_url'])
            if not item['observation'].strip(): return False
    except (KeyError,ValueError,TypeError): return False
    return not e['conflict_flags'] and e['event_format'] in {'virtual','hybrid'} and e['price_type'] in {'free','paid'} and bool(e['summary'].strip())

def assign(root=ROOT, day=None):
    day = day or datetime.now(CENTRAL).date()
    events = read(root/'data/canonical-events.json')
    for e in events: e['roundup_week'] = week(dt(e['start_datetime']))
    write(root/'data/canonical-events.json',events)
    write(root/'data/future-events.json',[e for e in events if dt(e['start_datetime']).astimezone(CENTRAL).date() > date.fromisoformat(target(day).split('_to_')[1])])
    return events

def generate(root=ROOT, day=None):
    day = day or datetime.now(CENTRAL).date()
    label = target(day)
    rules = read(root/'config/editorial-rules.yml')
    brand = read(root/'config/branding.yml')
    reviews = read(root/'data/reviews.json')
    candidates = [e for e in read(root/'data/canonical-events.json') if e['roundup_week']==label and eligible(e,reviews)]
    candidates.sort(key=lambda e:(e['price_type']!='free',e['event_format']!='virtual',-reviews[e['event_id']].get('score',0),e['start_datetime'],e['event_id']))
    selected = candidates[:rules['target_max']]
    def render(compact=False):
        lines=[brand['name']+' | '+label.split('/')[1],brand['introduction'],'']
        for e in selected:
            time=dt(e['start_datetime']).astimezone(CENTRAL).strftime('%a %b %d, %I:%M %p %Z')
            lines += [f"{e['title']} — {e['organizer']}",f"{time} | {e['price_type']} | {e['event_format']}"]
            if not compact: lines.append(e['summary'])
            lines += [e['registration_url'],'']
        return '\n'.join(lines+[brand['cta'],''])
    full, compact = render(),render(True)
    if len(compact)>rules['linkedin_max_characters']: raise ValueError('compact output exceeds configured limit; reduce selection')
    folder=root/'weeks'/label
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'linkedin-roundup.md').write_text(full if len(full)<=rules['linkedin_max_characters'] else compact)
    (folder/'linkedin-compact.md').write_text(compact)
    write(folder/'review.json',{'publication_status':'human_review_required','selected_ids':[e['event_id'] for e in selected],'below_target':len(selected)<rules['target_min'],'full_length':len(full),'compact_length':len(compact)})
    return folder

def main(command):
    parser=argparse.ArgumentParser()
    parser.add_argument('--as-of',type=date.fromisoformat)
    parser.add_argument('files',nargs='*')
    args=parser.parse_args()
    if command=='validate':
        for path in args.files or sorted((ROOT/'intake').glob('*/*.json')):
            batch=read(path)
            if not isinstance(batch,list): raise ValueError('expected array')
            for e in batch: validate(e)
    elif command=='ingest': ingest()
    elif command=='assign_weeks': assign(day=args.as_of)
    elif command=='generate_post': print(generate(day=args.as_of))
