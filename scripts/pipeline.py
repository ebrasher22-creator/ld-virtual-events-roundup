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

def editorial_registration_url(e):
    """Preserve an approved original spelling; never undo a resolved destination change."""
    submissions=sorted(e.get('submissions',[]),key=lambda s:(s.get('raw',{}).get('discovered_at',''),s.get('file',''),s.get('sha256','')))
    for submission in submissions:
        original=submission.get('raw',{}).get('registration_url')
        if original and url(original)==url(e['registration_url']): return original
    return e['registration_url']


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

SCOPED_ORGANIZER_ALIASES = {
    'ispring solutions': 'ispring',
    'training industry inc': 'training industry',
}
SCOPED_ALIAS_DOMAINS = {
    'ispring': 'ispringsolutions.com',
    'training industry': 'trainingindustry.com',
}
APPROVED_FACT_FIELDS = (
    'title', 'organizer', 'organizer_url', 'event_url', 'registration_url',
    'start_datetime', 'end_datetime', 'timezone', 'event_format', 'language',
    'price_type', 'cost', 'summary', 'audience', 'topics',
)
CORE_CONFLICT_FIELDS = {
    'title', 'organizer', 'start_datetime', 'end_datetime',
    'timezone', 'event_format', 'price_type', 'ambiguous_identity',
}
ACKNOWLEDGABLE_PROPOSAL_CONFLICTS = {'summary', 'registration_url'}

def record_domains(e):
    domains = set()
    for key in ('event_url', 'registration_url', 'organizer_url'):
        value = e.get(key)
        if isinstance(value, str) and value.strip():
            host = (urlsplit(value).hostname or '').lower().removeprefix('www.')
            if host:
                domains.add(host)
    for key in ('source_urls', 'registration_aliases'):
        for value in (e.get(key) or []):
            if isinstance(value, str) and value.strip():
                host = (urlsplit(value).hostname or '').lower().removeprefix('www.')
                if host:
                    domains.add(host)
    return domains

def has_alias_domain(e, canonical_organizer):
    domain = SCOPED_ALIAS_DOMAINS.get(canonical_organizer)
    if not domain:
        return False
    return any(d == domain or d.endswith('.' + domain) for d in record_domains(e))

def scoped_organizer(e):
    name = normalized(e.get('organizer', ''))
    mapped = SCOPED_ORGANIZER_ALIASES.get(name, name)
    if mapped in SCOPED_ALIAS_DOMAINS:
        return mapped if has_alias_domain(e, mapped) else name
    return name

def same_organizer(a, b):
    na = normalized(a.get('organizer', ''))
    nb = normalized(b.get('organizer', ''))
    if na == nb:
        return True
    ma = SCOPED_ORGANIZER_ALIASES.get(na, na)
    mb = SCOPED_ORGANIZER_ALIASES.get(nb, nb)
    return ma == mb and has_alias_domain(a, ma) and has_alias_domain(b, mb)

def same_event(existing, candidate):
    cand_reg = url(candidate['registration_url'])
    existing_reg = url(existing['registration_url'])
    if cand_reg == existing_reg:
        return True
    if cand_reg in set(existing.get('registration_aliases') or []):
        if (normalized(existing['title']) == normalized(candidate['title'])
                or dt(existing['start_datetime']) == dt(candidate['start_datetime'])):
            return True
    if (normalized(existing['title']) == normalized(candidate['title'])
            and same_organizer(existing, candidate)
            and dt(existing['start_datetime']) == dt(candidate['start_datetime'])):
        return True
    return False

def detect_conflicts(match, e):
    conflicts = []
    if normalized(match.get('title') or '') != normalized(e.get('title') or ''):
        conflicts.append('title')
    if not same_organizer(match, e):
        conflicts.append('organizer')
    if dt(match['start_datetime']) != dt(e['start_datetime']):
        conflicts.append('start_datetime')
    if match.get('end_datetime') and e.get('end_datetime') and dt(match['end_datetime']) != dt(e['end_datetime']):
        conflicts.append('end_datetime')
    if match.get('timezone') != e.get('timezone'):
        conflicts.append('timezone')
    if match.get('event_format') != e.get('event_format'):
        conflicts.append('event_format')
    if match.get('price_type') != e.get('price_type'):
        conflicts.append('price_type')
    if url(match['registration_url']) != url(e['registration_url']):
        conflicts.append('registration_url')
    if normalized(match.get('summary') or '') != normalized(e.get('summary') or ''):
        conflicts.append('summary')
    return conflicts

def classify_field_difference(field, approved_event, candidate_raw):
    a, b = approved_event.get(field), candidate_raw.get(field)
    if field in {'start_datetime', 'end_datetime'}:
        if a is not None and b is not None and dt(a) == dt(b):
            return 'timestamp_representation_only'
        return 'proposed_enrichment' if a is None or b is None else 'substantive_conflict'
    if field == 'title' and normalized(a or '') == normalized(b or ''):
        return 'capitalization_punctuation_only'
    if field == 'organizer':
        return 'scoped_organizer_alias' if same_organizer(approved_event, candidate_raw) else 'substantive_conflict'
    if field == 'registration_url':
        return 'tracking_slash_only' if url(a) == url(b) else 'registration_destination_proposal'
    if field == 'language' and {str(a).lower(), str(b).lower()} <= {'en', 'english'}:
        return 'language_label_only'
    if a is None or b is None:
        return 'proposed_enrichment'
    if field == 'summary':
        return 'capitalization_punctuation_only' if normalized(a or '') == normalized(b or '') else 'unreviewed_description_variant'
    if field in {'audience', 'topics'}:
        return 'unreviewed_editorial_context_variant'
    if field == 'event_url':
        return 'additional_source_location'
    return 'substantive_conflict'

def build_unadopted_proposals(old_event, new_submissions):
    proposals = []
    for sub in new_submissions:
        raw = sub.get('raw', {})
        for field in APPROVED_FACT_FIELDS:
            a, b = old_event.get(field), raw.get(field)
            if a == b:
                continue
            kind = classify_field_difference(field, old_event, raw)
            proposals.append({
                'field': field,
                'preserved_approved_value': a,
                'proposed_value': b,
                'classification': kind,
                'adopted': False,
                'review_needed_if_adopted': kind not in {
                    'capitalization_punctuation_only',
                    'scoped_organizer_alias',
                    'tracking_slash_only',
                    'language_label_only',
                    'timestamp_representation_only',
                },
                'source_file': sub.get('file'),
                'submission_sha256': sub.get('sha256'),
            })
    return proposals

def week(value):
    day = value.astimezone(CENTRAL).date() if isinstance(value,datetime) else value
    sunday = day - timedelta(days=(day.weekday()+1)%7)
    monday = sunday + timedelta(days=1)
    return f'{monday.isocalendar().year}/RW{monday.isocalendar().week:02d}_{sunday}_to_{sunday+timedelta(days=6)}'

def target(day):
    return week(day + timedelta(days=7-(day.weekday()+1)%7))

def ingest(root=ROOT):
    root = Path(root)
    events = read(root/'data/canonical-events.json')
    reviews_path = root/'data/reviews.json'
    reviews = read(reviews_path) if reviews_path.is_file() else {}
    for path in sorted((root/'intake').glob('*/*.json')):
        batch = read(path)
        if not isinstance(batch,list): raise ValueError('intake file must contain an array')
        for e in batch: validate(e)
    pre_approved = {}
    for existing in events:
        eid = existing.get('event_id')
        rev = reviews.get(eid)
        if isinstance(rev, dict) and rev.get('decision') == 'verified':
            check_rev = {eid: dict(rev, editorial_decision='selected')}
            if approval_problem(existing, check_rev, root) is None:
                pre_approved[eid] = (json.loads(json.dumps(existing)), fingerprint(existing))
    # Validate the entire intake before mutating persisted output.
    for path in sorted((root/'intake').glob('*/*.json')):
        for raw in read(path):
            e = json.loads(json.dumps(raw))
            e['registration_url'] = url(e['registration_url'])
            digest = fingerprint(raw)
            matches = [x for x in events if same_event(x, e)]
            if len(matches) > 1:
                for candidate_match in matches:
                    candidate_match['conflict_flags'] = sorted(set(candidate_match.get('conflict_flags', []) + ['ambiguous_identity']))
                    candidate_match['verification_status'] = 'pending'
                    candidate_match['last_verified_at'] = None
                    candidate_match['editorial_status'] = 'pending'
                continue
            match = matches[0] if matches else None
            if match is None:
                match = {k:v for k,v in e.items() if k not in {'event_id','verification_status','last_verified_at','editorial_status','editorial_score','roundup_week','conflict_flags','updated_at'}}
                match.update(event_id='evt_'+hashlib.sha256(e['registration_url'].encode()).hexdigest()[:16],verification_status='pending',last_verified_at=None,editorial_status='pending',editorial_score=0,roundup_week=None,conflict_flags=[],updated_at=e['discovered_at'],submissions=[],registration_aliases=[e['registration_url']])
                events.append(match)
            if any(x['sha256']==digest for x in match['submissions']): continue
            if match['submissions']:
                match['conflict_flags'] = sorted(set(match['conflict_flags'] + detect_conflicts(match, e)))
            for field in ('discovered_by','source_urls'):
                match[field] = sorted(set(match[field]+e[field]))
            seen_evidence = {json.dumps(item, sort_keys=True) for item in match.get('evidence', [])}
            for item in sorted(e.get('evidence', []), key=lambda x: (x.get('claim', ''), x.get('source_url', ''), x.get('excerpt', ''))):
                serialized = json.dumps(item, sort_keys=True)
                if serialized not in seen_evidence:
                    match['evidence'].append(item)
                    seen_evidence.add(serialized)
            match['registration_aliases'] = sorted(set(match['registration_aliases']+[e['registration_url']]))
            match['submissions'].append({'sha256':digest,'file':str(path.relative_to(root)),'raw':raw})
            match['submissions'].sort(key=lambda x:x['sha256'])
            if dt(e['discovered_at']) > dt(match['updated_at']):
                match['updated_at'] = e['discovered_at']
            # Any new submission invalidates previous review unless audited migration proves approved facts are unchanged.
            match['verification_status']='pending'
            match['last_verified_at']=None
            match['editorial_status']='pending'
    reviews_changed = False
    for match in events:
        eid = match.get('event_id')
        if eid not in pre_approved:
            continue
        old_event, old_sha = pre_approved[eid]
        if fingerprint(match) == old_sha:
            continue
        if not all(old_event.get(field) == match.get(field) for field in APPROVED_FACT_FIELDS):
            continue
        flags = set(match.get('conflict_flags') or [])
        if flags & CORE_CONFLICT_FIELDS or not (flags <= ACKNOWLEDGABLE_PROPOSAL_CONFLICTS):
            continue
        if 'registration_url' in flags:
            approved_urls = {url(old_event['event_url']), url(old_event['registration_url'])}
            if not all(url(s['raw']['event_url']) in approved_urls or url(s['raw']['registration_url']) in approved_urls for s in match.get('submissions', [])):
                continue
        match['verification_status'] = old_event['verification_status']
        match['last_verified_at'] = old_event.get('last_verified_at')
        match['editorial_status'] = old_event['editorial_status']
        match['editorial_score'] = old_event.get('editorial_score', 0)
        new_sha = fingerprint(match)
        old_sub_shas = {s['sha256'] for s in old_event.get('submissions', [])}
        added_subs = [s for s in match.get('submissions', []) if s['sha256'] not in old_sub_shas]
        proposals = build_unadopted_proposals(old_event, added_subs)
        review = reviews[eid]
        prior_history = list((review.get('migration') or {}).get('history') or [])
        if isinstance(review.get('migration'), dict):
            prior_entry = {k: v for k, v in review['migration'].items() if k != 'history'}
            prior_history.append(prior_entry)
        migration_entry = {
            'type': 'audited_approval_fingerprint_migration',
            'from_record_sha256': old_sha,
            'to_record_sha256': new_sha,
            'migrated_at': match['updated_at'],
            'reason': 'corroborating_submission_provenance_only',
            'approved_facts_unchanged': True,
            'verified_unchanged_fields': list(APPROVED_FACT_FIELDS),
            'acknowledged_conflict_flags': sorted(flags),
            'unadopted_proposals': proposals,
        }
        if prior_history:
            migration_entry['history'] = prior_history
        review['record_sha256'] = new_sha
        review['migration'] = migration_entry
        reviews_changed = True
    write(root/'data/canonical-events.json', sorted(events,key=lambda x:x['event_id']))
    if reviews_changed and reviews_path.is_file():
        write(reviews_path, reviews)
    return events

CLAIMS = {'relevance','virtual_availability','datetime','registration_url','organizer','status','price'}

def approval_problem(e, reviews, root=ROOT):
    """Return an exclusion reason; trust only current, separately persisted human reviews."""
    review = reviews.get(e.get('event_id'), {})
    if not isinstance(review,dict): return 'invalid_review'
    if review.get('record_sha256') != fingerprint(e): return 'missing_or_stale_approval'
    if review.get('decision') != 'verified': return 'not_human_approved'
    if review.get('editorial_decision') != 'selected': return 'not_editorially_selected'
    migration = review.get('migration')
    acknowledged = set()
    if migration is not None:
        if not isinstance(migration, dict):
            return 'invalid_approval_migration'
        if (migration.get('type') != 'audited_approval_fingerprint_migration'
                or migration.get('approved_facts_unchanged') is not True
                or migration.get('to_record_sha256') != fingerprint(e)
                or not isinstance(migration.get('from_record_sha256'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', migration['from_record_sha256'])
                or migration['from_record_sha256'] == migration['to_record_sha256']):
            return 'invalid_approval_migration'
        try:
            dt(migration['migrated_at'])
        except ValueError:
            return 'invalid_approval_migration'
        ack_list = migration.get('acknowledged_conflict_flags')
        if not isinstance(ack_list, list) or not set(ack_list) <= ACKNOWLEDGABLE_PROPOSAL_CONFLICTS:
            return 'invalid_approval_migration'
        acknowledged = set(ack_list)
    if set(e.get('conflict_flags') or []) - acknowledged: return 'unresolved_conflicts'
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

EDITORIAL_EVENT_SUBSTANTIVE_FIELDS = (
    'event_id', 'title', 'organizer', 'organizer_url', 'event_url',
    'start_datetime', 'end_datetime', 'timezone', 'start_central', 'central_timezone',
    'event_format', 'language', 'registration_url', 'canonical_registration_url',
    'summary', 'summary_grounding', 'topics', 'audience',
    'price_type_original', 'cost_original', 'price_label', 'required_fact_block', 'human_approval',
)

def migrate_editorial_package(root=ROOT, day=None):
    """Audited package-version migration when canonical/review hashes change without substantive RW fact changes."""
    from editorial_input import build_input, export_input
    from validate_work_caption import check_caption
    from validate_editorial_drafts import validate_files
    from validate_post import validate_output
    root = Path(root)
    day = day or datetime.now(CENTRAL).date()
    label = target(day)
    folder = root/'weeks'/label
    input_path = folder/'editorial-input.json'
    report_path = folder/'editorial-report.json'
    if not input_path.is_file() or not report_path.is_file():
        raise ValueError('Existing editorial package required for audited migration')
    old_input = read(input_path)
    old_report = read(report_path)
    old_full = (folder/'linkedin-post.md').read_bytes()
    old_compact = (folder/'linkedin-post-compact.md').read_bytes()
    new_input = build_input(root, day)
    if new_input['export_status'] != 'ready' or len(old_input.get('events', [])) != len(new_input.get('events', [])):
        raise ValueError('Eligible target-week event membership changed; cannot auto-migrate editorial package')
    reviews = read(root/'data/reviews.json')
    for old_ev, new_ev in zip(old_input['events'], new_input['events']):
        for field in EDITORIAL_EVENT_SUBSTANTIVE_FIELDS:
            if old_ev.get(field) != new_ev.get(field):
                raise ValueError(f'Substantive editorial field changed on {old_ev.get("event_id")}: {field}')
        if old_ev.get('record_sha256') != new_ev.get('record_sha256'):
            mig = (reviews.get(new_ev['event_id']) or {}).get('migration') or {}
            if mig.get('from_record_sha256') != old_ev.get('record_sha256') or mig.get('to_record_sha256') != new_ev.get('record_sha256'):
                raise ValueError(f'Unmigrated record fingerprint difference on {new_ev["event_id"]}')
    events = read(root/'data/canonical-events.json')
    included = [e for e in events if week(dt(e['start_datetime'])) == label and e.get('roundup_week') == label and eligible(e, reviews, root)]
    included.sort(key=lambda e: (dt(e['start_datetime']), e['event_id']))
    excluded = []
    for e in events:
        actual_week = week(dt(e['start_datetime']))
        reason = 'outside_target_week' if actual_week != label else ('incorrect_week_assignment' if e.get('roundup_week') != actual_week else approval_problem(e, reviews, root))
        if reason:
            excluded.append(dict(event_id=e['event_id'], title=e['title'], reason=reason, assigned_week=e.get('roundup_week')))
    updated_report = dict(old_report)
    updated_report['canonical_sha256'] = new_input['source_versions']['canonical_sha256']
    updated_report['reviews_sha256'] = new_input['source_versions']['reviews_sha256']
    updated_report['events_included'] = [dict(event_id=e['event_id'], title=e['title'], record_sha256=fingerprint(e)) for e in included]
    updated_report['events_excluded'] = excluded
    write(report_path, updated_report)
    export_input(root, day)
    assert (folder/'linkedin-post.md').read_bytes() == old_full
    assert (folder/'linkedin-post-compact.md').read_bytes() == old_compact
    validate_output(root, day)
    old_input_sha = old_input['editorial_input_sha256']
    new_input_sha = new_input['editorial_input_sha256']
    rebound_drafts = []
    if (root/'editorial-drafts').is_dir():
        for draft_path in sorted((root/'editorial-drafts').rglob('*.json')):
            draft = read(draft_path)
            if not isinstance(draft, dict) or draft.get('roundup_identifier') != label:
                continue
            if draft.get('editorial_input_sha256') not in {old_input_sha, new_input_sha}:
                continue
            full_bytes = draft.get('full_caption', '').encode('utf-8')
            compact_bytes = draft.get('compact_caption', '').encode('utf-8')
            for field in ('full_caption', 'compact_caption'):
                errs = check_caption(draft[field], new_input)
                if errs:
                    raise ValueError(f'{draft_path}: {field} failed validation: {errs}')
            draft['editorial_input_sha256'] = new_input_sha
            write(draft_path, draft)
            assert draft['full_caption'].encode('utf-8') == full_bytes
            assert draft['compact_caption'].encode('utf-8') == compact_bytes
            rebound_drafts.append(dict(
                draft_path=draft_path.relative_to(root).as_posix(),
                from_editorial_input_sha256=old_input_sha,
                to_editorial_input_sha256=new_input_sha,
                full_caption_sha256=hashlib.sha256(full_bytes).hexdigest(),
                compact_caption_sha256=hashlib.sha256(compact_bytes).hexdigest(),
                caption_bytes_unchanged=True,
            ))
        if rebound_drafts and not validate_files(root, expected_as_of=day):
            raise ValueError('Work editorial draft validation failed after package migration')
    return dict(
        roundup_identifier=label,
        from_editorial_input_sha256=old_input_sha,
        to_editorial_input_sha256=new_input_sha,
        from_canonical_sha256=old_report['canonical_sha256'],
        to_canonical_sha256=updated_report['canonical_sha256'],
        from_reviews_sha256=old_report['reviews_sha256'],
        to_reviews_sha256=updated_report['reviews_sha256'],
        deterministic_post_bytes_unchanged=True,
        rebound_drafts=rebound_drafts,
    )

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
