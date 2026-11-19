"""Automated event qualification and live registration checks (Python 3.11+ stdlib only).

Owner decision (2026-11-18): there is no per-event human approval gate. An event becomes
publication-eligible only when deterministic rules below pass, including a *current* check of
its primary organizer/registration pages. AI discovery evidence alone never substitutes for a
live primary-source check: unreachable, bot-protected or mismatched pages leave the event
unresolved (excluded and reported), never "verified" and never presumed canceled.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import socket
import html
import json
from pathlib import Path
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from pipeline import (ROOT, CENTRAL, CORE_CONFLICT_FIELDS, SCHEMA, read, write, dt, url,
                      normalized, validate, editorial_registration_url)

CONFIG_PATH = 'config/qualification.yml'
CHECKS_PATH = 'data/registration-checks.json'
USER_AGENT = 'NextWeekInLD-RegistrationCheck/1.0 (+https://github.com/ebrasher22-creator/ld-virtual-events-roundup)'
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
          'september', 'october', 'november', 'december']
STOPWORDS = {'the', 'and', 'for', 'with', 'your', 'from', 'into', 'that', 'this', 'what', 'how',
             'are', 'how', 'leader', 'talk', 'webinar', 'session'}
BOT_MARKERS = ('cf-chl', 'just a moment', 'attention required', 'verify you are human',
               'checking your browser', 'captcha', 'vercel security checkpoint', 'access denied')
CANCEL_PATTERN = re.compile(r'\b(event (?:has been |is )?cancel+ed|this (?:event|webinar|session) (?:has been |is )?(?:cancel+ed|postponed)|'
                            r'registration (?:is )?(?:now )?closed|event has ended|no longer available)\b', re.I)
FREE_PATTERN = re.compile(r'\b(free|complimentary|no cost|no charge)\b', re.I)
PRICE_PATTERN = re.compile(r'(US\$|USD\s?|CA\$|\$|€|£)\s?(\d[\d,]*(?:\.\d{2})?)', re.I)


def load_config(root=ROOT):
    path = Path(root) / CONFIG_PATH
    return read(path) if path.is_file() else {}


def load_checks(root=ROOT):
    path = Path(root) / CHECKS_PATH
    return read(path) if path.is_file() else {}


def host(value):
    try:
        return (urlsplit(value).hostname or '').lower().removeprefix('www.')
    except (TypeError, ValueError):
        return ''


def check_key(e):
    """Binds a registration check to the exact facts it confirmed; any change makes it stale."""
    material = {key: e.get(key) for key in SCHEMA['items']['properties']}
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def primary_hosts(e):
    hosts = {host(e.get(k)) for k in ('event_url', 'registration_url', 'organizer_url') if e.get(k)}
    hosts |= {host(v) for v in e.get('registration_aliases') or []}
    return {h for h in hosts if h}


def primary_evidence(e):
    hosts = primary_hosts(e)
    return [item for item in e.get('evidence') or []
            if any(host(item.get('source_url')) == h or host(item.get('source_url')).endswith('.' + h) for h in hosts)]


def relevance_ok(e, config):
    keywords = [k.casefold() for k in config.get('relevance_keywords', [])]
    if not keywords:
        return True
    text = ' '.join([e.get('title', ''), e.get('summary', ''), *e.get('topics', []), *e.get('audience', [])]).casefold()
    return any(k in text for k in keywords)


def pricing_label(e):
    """Never infer free. Free/Paid only with explicit primary-source evidence; otherwise 'Pricing not listed'."""
    excerpts = ' '.join(item.get('excerpt', '') for item in primary_evidence(e))
    if e.get('price_type') == 'free' and FREE_PATTERN.search(excerpts):
        return 'Free'
    if e.get('price_type') == 'paid':
        match = PRICE_PATTERN.search(excerpts)
        if match:
            return f'Paid: {match.group(1).strip()}{match.group(2)}'
        return 'Paid (price on registration page)'
    return 'Pricing not listed'


# ---------------------------------------------------------------- live page checks

def page_text(raw):
    raw = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', raw)
    return html.unescape(re.sub(r'(?s)<[^>]+>', ' ', raw))


def public_target(target):
    parsed = urlsplit(target)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError('Only public HTTP(S) destinations allowed')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80))
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Nonpublic destination blocked')
    return target


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_target(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(target, timeout=20):
    try:
        public_target(target)
        request = urllib.request.Request(target, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml'})
        with urllib.request.build_opener(PublicRedirect()).open(request, timeout=timeout) as response:
            body = response.read(3_000_000).decode(response.headers.get_content_charset() or 'utf-8', 'replace')
            return dict(status=response.status, final_url=response.geturl(), body=body, error=None)
    except urllib.error.HTTPError as exc:
        return dict(status=exc.code, final_url=target, body='', error=f'HTTP {exc.code}')
    except Exception as exc:
        return dict(status=None, final_url=target, body='', error=type(exc).__name__)


def current_claims(e, text):
    """Conservative page-based checks; discovery excerpts cannot supply missing live facts."""
    from zoneinfo import ZoneInfo
    moment = dt(e['start_datetime']).astimezone(ZoneInfo(e['timezone']))
    clean = ' '.join(html.unescape(text).casefold().split())
    day = moment.day
    month = MONTHS[moment.month - 1]
    date_ok = moment.date().isoformat() in clean or bool(re.search(
        rf'\b(?:{month}|{month[:3]})\.?\s+0?{day}(?:st|nd|rd|th)?[,]?\s+{moment.year}\b', clean))
    hour = moment.hour % 12 or 12
    ampm = 'am' if moment.hour < 12 else 'pm'
    time_ok = bool(re.search(rf'(?<!\d){hour}(?::|\.){moment.minute:02d}\s*{ampm[0]}\.?m\.?\b', clean))
    if moment.minute == 0:
        time_ok |= bool(re.search(rf'(?<![\d:]){hour}\s*{ampm[0]}\.?m\.?\b', clean))
    abbreviation = moment.tzname().casefold()
    generic = {'America/New_York': 'et', 'America/Chicago': 'ct', 'America/Denver': 'mt', 'America/Los_Angeles': 'pt'}.get(e['timezone'])
    zone_ok = any(re.search(r'\b' + re.escape(z) + r'\b', clean) for z in [abbreviation, generic, e['timezone'].casefold()] if z)
    iso = moment.isoformat().casefold()
    if iso in clean:
        date_ok = time_ok = zone_ok = True
    return dict(date=bool(date_ok), time=bool(time_ok), timezone=bool(zone_ok),
                virtual=bool(re.search(r'\b(webinar|virtual|online|zoom|webcast)\b', clean)),
                organizer=normalized(e['organizer']) in normalized(text))


def title_matches(title, text):
    tokens = [t for t in normalized(title).split() if len(t) > 3 and t not in STOPWORDS]
    if not tokens:
        return False
    haystack = ' ' + normalized(text) + ' '
    found = sum((' ' + t + ' ') in haystack for t in tokens)
    return found / len(tokens) >= 0.6


def date_matches(start, text):
    local = dt(start).astimezone(CENTRAL)
    source = dt(start)
    lowered = ' ' + re.sub(r'\s+', ' ', text.casefold()) + ' '
    for moment in {local.date(), source.date()}:
        month = MONTHS[moment.month - 1]
        for name in (month, month[:3]):
            if re.search(rf'\b{name}\.?\s+0?{moment.day}\b', lowered) or re.search(rf'\b0?{moment.day}\s+{name}\b', lowered):
                return True
        if moment.isoformat() in lowered:
            return True
    return False


def classify_page(result, e):
    body = result['body'] or ''
    lowered = body[:200_000].casefold()
    status = result['status']
    page = dict(status=status, final_url=result['final_url'], error=result['error'])
    if status in (401, 403, 429, 503) or (status == 200 and any(m in lowered for m in BOT_MARKERS) and not title_matches(e['title'], page_text(body))):
        page['classification'] = 'inaccessible_bot_or_auth'
    elif status in (404, 410):
        page['classification'] = 'not_found'
    elif status is None or not (200 <= status < 300):
        page['classification'] = 'inaccessible'
    else:
        text = page_text(body)
        page.update(title_match=title_matches(e['title'], text), date_match=current_claims(e, text)['date'], claims=current_claims(e, text),
                    cancel_signal=bool(CANCEL_PATTERN.search(text)))
        if page['cancel_signal']:
            page['classification'] = 'cancel_or_closed_signal'
        else:
            page['classification'] = 'confirmed' if page['title_match'] and all(page['claims'].values()) else 'reachable_unconfirmed'
            page['page_sha256'] = hashlib.sha256(body.encode()).hexdigest()
            page['observed_text'] = ' '.join(text.split())[:100000]
    return page


def check_event(e, fetcher=fetch, checked_at=None):
    checked_at = checked_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    registration = editorial_registration_url(e)
    targets = [('registration', registration)]
    if url(e['event_url']) != url(registration):
        targets.append(('event', e['event_url']))
    pages = []
    for role, target in targets:
        page = classify_page(fetcher(target), e)
        page.update(role=role, url=target)
        pages.append(page)
    kinds = {p['role']: p['classification'] for p in pages}
    if any(p['classification'] == 'cancel_or_closed_signal' for p in pages):
        result = 'cancel_or_closed_signal'
    elif kinds.get('registration') == 'not_found':
        result = 'registration_not_found'
    elif kinds.get('registration') not in ('confirmed', 'reachable_unconfirmed'):
        result = 'registration_unreachable'
    elif all(p['classification'] == 'confirmed' for p in pages):
        result = 'confirmed'
    else:
        result = 'event_details_unconfirmed'
    return dict(event_id=e['event_id'], record_key=check_key(e), checked_at=checked_at, classification=result,
                date_confirmed_on_page=any(p.get('date_match') for p in pages), pages=pages)


def run_checks(root=ROOT, events=None, fetcher=fetch, checked_at=None):
    root = Path(root)
    checks = load_checks(root)
    for e in events or []:
        checks[e['event_id']] = check_event(e, fetcher, checked_at)
    write(root / CHECKS_PATH, dict(sorted(checks.items())))
    return checks


# ---------------------------------------------------------------- eligibility

def qualification(e, root=ROOT, reference=None, checks=None, config=None):
    """Return (problems, warnings). An event is eligible only when problems is empty."""
    root = Path(root)
    config = load_config(root) if config is None else config
    checks = load_checks(root) if checks is None else checks
    reference = reference or datetime.now(timezone.utc)
    problems, warnings = [], []
    deferred = config.get('deferred_events', {})
    if e.get('event_id') in deferred:
        problems.append('owner_deferred: ' + deferred[e['event_id']])
    try:
        validate({k: v for k, v in e.items() if k in SCHEMA['items']['properties']})
    except (ValueError, KeyError, TypeError) as exc:
        problems.append('invalid_record: ' + str(exc)[:160])
        return problems, warnings
    if e.get('event_format') not in ('virtual', 'hybrid'):
        problems.append('not_live_virtual_or_hybrid')
    if dt(e['start_datetime']) <= reference:
        problems.append('event_started_or_past')
    flags = set(e.get('conflict_flags') or [])
    for flag in sorted(flags & CORE_CONFLICT_FIELDS):
        problems.append('unresolved_conflict:' + flag)
    if 'summary' in flags:
        warnings.append('description_variants_between_agents (canonical description used)')
    if not relevance_ok(e, config):
        problems.append('not_professionally_relevant')
    if not primary_evidence(e):
        problems.append('no_primary_source_evidence')
    check = checks.get(e['event_id'])
    max_age = timedelta(hours=config.get('registration_check_max_age_hours', 36))
    if not check:
        problems.append('registration_not_checked')
    elif check.get('record_key') != check_key(e):
        problems.append('registration_check_stale_for_current_facts')
    elif dt(check['checked_at']) > reference + timedelta(minutes=5):
        problems.append('registration_check_in_future')
    elif dt(check['checked_at']) < reference - max_age:
        problems.append('registration_check_too_old')
    elif check.get('classification') != 'confirmed':
        problems.append('registration_check:' + check.get('classification', 'unknown'))
    else:
        if 'registration_url' in flags:
            warnings.append('alternate_registration_destination_reported (canonical destination confirmed live)')
        if not check.get('date_confirmed_on_page'):
            problems.append('date_not_confirmed_on_current_page')
    if check and check.get('classification') == 'confirmed':
        live_text = ' '.join(p.get('observed_text', '') for p in check.get('pages', []))
        label = pricing_label(e)
        if label == 'Free' and not FREE_PATTERN.search(live_text):
            problems.append('free_price_not_confirmed_on_current_page')
        if label.startswith('Paid:'):
            original = PRICE_PATTERN.search(' '.join(i.get('excerpt', '') for i in primary_evidence(e)))
            if original and original.group(0).casefold() not in live_text.casefold():
                problems.append('published_price_not_confirmed_on_current_page')
    if pricing_label(e) == 'Pricing not listed':
        warnings.append('pricing_not_listed')
    return problems, warnings


def eligibility_problem(e, root=ROOT, reference=None, checks=None, config=None):
    problems, _ = qualification(e, root, reference, checks, config)
    return problems[0] if problems else None


def is_eligible(e, root=ROOT, reference=None, checks=None, config=None):
    return eligibility_problem(e, root, reference, checks, config) is None


if __name__ == '__main__':
    import argparse
    from datetime import date
    from pipeline import week, target
    parser = argparse.ArgumentParser(description='Run live registration checks for one roundup week')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    args = parser.parse_args()
    label = target(args.as_of)
    events = [e for e in read(args.root / 'data/canonical-events.json') if week(dt(e['start_datetime'])) == label]
    results = run_checks(args.root, events)
    for e in events:
        print(results[e['event_id']]['classification'], '-', e['title'])
