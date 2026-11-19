"""Deterministic Wednesday LinkedIn preparation. Reports never authorize publication.

Eligibility is automated (scripts/qualification.py); there is no per-event human approval gate.
Eddie's only recurring checkpoint is the final caption review and manual LinkedIn publication.
"""
from datetime import datetime, timezone, time as clock
import hashlib
import os
import subprocess
from pathlib import Path
from pipeline import (ROOT, CENTRAL, read, write, dt, week, target, fingerprint, editorial_registration_url)
from qualification import qualification, load_checks, load_config, pricing_label, CHECKS_PATH

REPOSITORY = 'ebrasher22-creator/ld-virtual-events-roundup'
WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def source_commit(root):
    result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def sha_file(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def central_time(e):
    start = dt(e['start_datetime']).astimezone(CENTRAL)
    hour = start.hour % 12 or 12
    return f'{WEEKDAYS[start.weekday()]}, {MONTHS[start.month-1]} {start.day}, {start.year} | {hour}:{start.minute:02d} {"AM" if start.hour < 12 else "PM"} {start.tzname()}'


def shorten(text, limit):
    text = ' '.join(text.split())
    if limit is None or len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(' ', 1)[0].rstrip(',;:—-')
    return cut + '…'


def render_event(e, description_limit=220, include_description=True):
    """Immutable fact block: title, host, Central date/time, pricing status, description, registration URL."""
    detail = central_time(e) + ' | ' + pricing_label(e)
    if e['event_format'] == 'hybrid':
        detail += ' | Hybrid (virtual access)'
    lines = [e['title'], 'Hosted by ' + e['organizer'], detail]
    if include_description:
        lines.append(shorten(e['summary'], description_limit))
    lines.append(editorial_registration_url(e))
    return '\n'.join(lines)


def render_events(events, description_limit=220, include_description=True):
    return '\n\n'.join(render_event(e, description_limit, include_description) for e in events)


def build_caption(root, brand, label, body, intro, hashtags=True):
    period = label.split('_', 1)[1].replace('_to_', ' to ')
    template = (Path(root) / 'templates/linkedin-roundup.md').read_text()
    # Python format cannot silently drop or truncate required event details.
    return template.format(brand=brand['name'], period=period, introduction=intro, events=body, cta=brand['cta'],
                           hashtags=' '.join(brand.get('hashtags', [])) if hashtags else '').strip() + '\n'


def evaluate_week(root, label, reference, expiry_reference):
    """Split all canonical records into included/excluded with deterministic reasons."""
    events = read(Path(root) / 'data/canonical-events.json')
    checks = load_checks(root)
    config = load_config(root)
    included, excluded, outcomes = [], [], []
    for e in events:
        actual_week = week(dt(e['start_datetime']))
        if actual_week != label:
            excluded.append(dict(event_id=e['event_id'], title=e['title'], reason='outside_target_week', assigned_week=e.get('roundup_week')))
            continue
        if e.get('roundup_week') != actual_week:
            problems, warnings = ['incorrect_week_assignment'], []
        else:
            problems, warnings = qualification(e, root, reference, checks, config)
            if dt(e['start_datetime']) <= expiry_reference and 'event_started_or_past' not in problems:
                problems.append('event_started_or_past')
        check = checks.get(e['event_id'], {})
        outcomes.append(dict(event_id=e['event_id'], title=e['title'], eligible=not problems, problems=problems, warnings=warnings,
                             registration_check=check.get('classification', 'not_checked'), registration_checked_at=check.get('checked_at'),
                             pricing_label=pricing_label(e), discovered_by=e.get('discovered_by')))
        if problems:
            excluded.append(dict(event_id=e['event_id'], title=e['title'], reason=problems[0], all_reasons=problems, assigned_week=e.get('roundup_week')))
        else:
            included.append(e)
    included.sort(key=lambda e: (dt(e['start_datetime']), e['event_id']))
    rules = read(Path(root) / 'config/editorial-rules.yml')
    brand = read(Path(root) / 'config/branding.yml')
    candidates = list(included)
    included = included[:rules['target_max']]
    while len(included) > 1:
        chosen, compact = compose(root, brand, rules, label, included)
        if len(chosen[1]) <= rules['linkedin_max_characters'] and len(compact) <= rules['linkedin_max_characters']:
            break
        included.pop()
    selected = {e['event_id'] for e in included}
    for e in candidates:
        if e['event_id'] not in selected:
            excluded.append(dict(event_id=e['event_id'], title=e['title'], reason='qualified_not_selected_capacity', assigned_week=label))
    return included, excluded, outcomes


def compose(root, brand, rules, label, included):
    """Fit the working budget, then the hard limit, shortening optional text before facts."""
    hard = rules['linkedin_max_characters']
    budget = rules.get('linkedin_target_characters', hard)
    long_desc = rules.get('description_max_characters', 220)
    intro, short = brand['introduction'], brand.get('compact_introduction', 'Learning opportunities for the week ahead.')
    attempts = [
        ('full', intro, long_desc, True, True),
        ('shortened_introduction', short, long_desc, True, True),
        ('condensed_descriptions', short, 140, True, True),
        ('condensed_descriptions_without_hashtags', short, 140, True, False),
        ('brief_descriptions_without_hashtags', short, 90, True, False),
    ]
    within_hard = None
    candidate = None
    for strategy, introduction, limit, describe, tags in attempts:
        caption = build_caption(root, brand, label, render_events(included, limit, describe), introduction, tags)
        candidate = (strategy, caption, limit, describe)
        if len(caption) <= budget:
            within_hard = candidate
            break
        if within_hard is None and len(caption) <= hard:
            within_hard = candidate
    chosen = within_hard or candidate
    compact = build_caption(root, brand, label, render_events(included, 90, True), short, False)
    return chosen, compact


def readiness(included, exceptions, warnings_present):
    if exceptions or not included:
        return 'not_ready_action_required'
    if warnings_present:
        return 'ready_with_warnings'
    return 'ready_for_review'


def generate_week(root=ROOT, day=None, generated_at=None):
    root = Path(root)
    day = day or datetime.now(CENTRAL).date()
    generated_at = generated_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    reference = dt(generated_at)
    expiry_reference = datetime.combine(day, clock(0, 0), tzinfo=CENTRAL)
    label = target(day)
    rules = read(root / 'config/editorial-rules.yml')
    brand = read(root / 'config/branding.yml')
    included, excluded, outcomes = evaluate_week(root, label, reference, expiry_reference)
    (strategy, full, _limit, described), compact = compose(root, brand, rules, label, included)
    hard = rules['linkedin_max_characters']
    budget = rules.get('linkedin_target_characters', hard)
    within_limit = len(full) <= hard and len(compact) <= hard
    exceptions, warnings = [], []
    if not within_limit:
        exceptions.append('CHARACTER_LIMIT: all eligible events retained; split or otherwise resolve before publication. Do not publish this over-limit draft.')
    if not included:
        exceptions.append('NO_ELIGIBLE_EVENTS: no event passed automated qualification for this week.')
    if included and not described:
        warnings.append('DESCRIPTIONS_OMITTED: descriptions removed to stay within the hard character limit.')
    if within_limit and len(full) > budget:
        warnings.append(f'OVER_WORKING_BUDGET: {len(full)} characters exceeds the {budget}-character working budget (hard limit {hard}).')
    below_target = len(included) < rules['target_min']
    if below_target:
        warnings.append(f'BELOW_TARGET: {len(included)} eligible events (target {rules["target_min"]}–{rules["target_max"]}); no events were added from other weeks.')
    event_warnings = [dict(event_id=o['event_id'], title=o['title'], warnings=o['warnings']) for o in outcomes if o['eligible'] and o['warnings']]
    unresolved = [dict(event_id=o['event_id'], title=o['title'], reasons=o['problems'], registration_check=o['registration_check'])
                  for o in outcomes if not o['eligible']]
    status = readiness(included, exceptions, bool(warnings or event_warnings))
    run_url = None
    if os.environ.get('GITHUB_RUN_ID') and os.environ.get('GITHUB_REPOSITORY'):
        run_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    folder = root / 'weeks' / label
    report = dict(roundup_identifier=label, as_of=day.isoformat(), generated_at=generated_at,
                  qualification_mode='automated_no_per_event_human_approval',
                  total_eligible_events_for_target_week=len(included), total_qualified_candidates=sum(o['eligible'] for o in outcomes),
                  events_included=[dict(event_id=e['event_id'], title=e['title'], record_sha256=fingerprint(e), pricing_label=pricing_label(e)) for e in included],
                  events_excluded=excluded, qualification_outcomes=outcomes, unresolved_events=unresolved, event_warnings=event_warnings,
                  missing_optional_pricing=[dict(event_id=e['event_id'], title=e['title'], original_price_type=e['price_type'])
                                            for e in included if pricing_label(e) == 'Pricing not listed'],
                  character_counts=dict(full=len(full), compact=len(compact), limit=hard, working_budget=budget), within_character_limit=within_limit,
                  caption_strategy=strategy, descriptions_included=described,
                  below_target=below_target, above_target=len(included) > rules['target_max'], target_min=rules['target_min'], target_max=rules['target_max'],
                  advisories=warnings, editorial_exceptions=exceptions, readiness_status=status,
                  source_commit=source_commit(root), canonical_sha256=sha_file(root / 'data/canonical-events.json'),
                  registration_checks_sha256=sha_file(root / CHECKS_PATH),
                  publication_approval_status='awaiting_final_human_review', workflow_run_url=run_url,
                  artifact_relative_path='weeks/' + label)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'linkedin-post.md').write_text(full)
    (folder / 'linkedin-post-compact.md').write_text(compact)
    write(folder / 'editorial-report.json', report)
    (folder / 'publication-checklist.md').write_text(CHECKLIST)
    write_handoff(root, folder, label, report)
    # Backward-compatible filenames/review summary for existing consumers.
    (folder / 'linkedin-roundup.md').write_text(full)
    (folder / 'linkedin-compact.md').write_text(compact)
    write(folder / 'review.json', dict(publication_status='human_review_required', selected_ids=[e['event_id'] for e in included],
                                        below_target=below_target, full_length=len(full), compact_length=len(compact)))
    if exceptions and included:
        raise ValueError('Editorial exception; review generated editorial-report.json: ' + '; '.join(exceptions))
    return folder


def write_handoff(root, folder, label, report):
    """Stable public paths Jarvis reads every Wednesday: weeks/current-handoff.{json,md}."""
    base = f'https://github.com/{REPOSITORY}/blob/main/'
    raw = f'https://raw.githubusercontent.com/{REPOSITORY}/main/'
    relative = (folder / 'linkedin-post.md').relative_to(root).as_posix()
    labels = {'ready_for_review': "READY FOR EDDIE'S REVIEW", 'ready_with_warnings': 'READY WITH WARNINGS',
              'not_ready_action_required': 'NOT READY — ACTION REQUIRED'}
    check_counts = {}
    for outcome in report['qualification_outcomes']:
        check_counts[outcome['registration_check']] = check_counts.get(outcome['registration_check'], 0) + 1
    handoff = dict(roundup_identifier=label, generated_at=report['generated_at'], as_of=report['as_of'],
                   generated_on_local_date=dt(report['generated_at']).astimezone(CENTRAL).date().isoformat(),
                   readiness_status=report['readiness_status'], readiness_label=labels[report['readiness_status']],
                   event_count=report['total_eligible_events_for_target_week'], character_counts=report['character_counts'],
                   within_character_limit=report['within_character_limit'], qualification_mode=report['qualification_mode'],
                   registration_check_results=check_counts,
                   advisories=report['advisories'], editorial_exceptions=report['editorial_exceptions'],
                   unresolved_events=report['unresolved_events'], event_warnings=report['event_warnings'],
                   post_url=base + relative, post_raw_url=raw + relative,
                   compact_post_url=base + (folder / 'linkedin-post-compact.md').relative_to(root).as_posix(),
                   report_url=base + (folder / 'editorial-report.json').relative_to(root).as_posix(),
                   workflow_run_url=report['workflow_run_url'], source_commit=report['source_commit'],
                   publication_approval_status='awaiting_final_human_review',
                   notice='Mechanical validation is not publication approval. Eddie reviews and publishes manually.')
    write(root / 'weeks/current-handoff.json', handoff)
    issues = '\n'.join(f'- {u["title"]}: {", ".join(u["reasons"])}' for u in report['unresolved_events']) or '- None'
    advisories = '\n'.join('- ' + a for a in report['advisories'] + report['editorial_exceptions']) or '- None'
    (root / 'weeks/current-handoff.md').write_text(f'''# Next Week in L&D — Wednesday handoff

**Status:** {handoff['readiness_label']}
**Roundup:** {label}
**Events included:** {handoff['event_count']}
**Characters:** {report['character_counts']['full']} full / {report['character_counts']['compact']} compact (limit {report['character_counts']['limit']}, working budget {report['character_counts']['working_budget']})
**Qualification:** automated (no per-event human approval); live registration checks in `data/registration-checks.json`
**Publication approval:** awaiting Eddie's final review — nothing has been published.

- LinkedIn post: {handoff['post_url']}
- Compact alternative: {handoff['compact_post_url']}
- Editorial report: {handoff['report_url']}
- Workflow run: {handoff['workflow_run_url'] or 'local run'}

## Advisories and exceptions
{advisories}

## Events excluded as unresolved this week
{issues}
''')


CHECKLIST = '''# Final manual publication review

Publication approval: **awaiting Eddie's final review**. Automated qualification and mechanical validation are not publication approval.

- [ ] Confirm this is the intended Sunday–Saturday period.
- [ ] Read titles, hosts, descriptions, dates/times (Central, CST/CDT) and pricing labels.
- [ ] Spot-check registration links; the editorial report lists the live check result for each event.
- [ ] Review advisories (below target, pricing not listed, unresolved events).
- [ ] Choose the full or compact caption and publish manually on LinkedIn.

Decision (publish / hold / revise): ______  Time: ______
'''
