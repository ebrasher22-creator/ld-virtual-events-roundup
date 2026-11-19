"""Wednesday preparation: assign weeks -> live registration checks -> generate -> validate -> Jarvis handoff.

Reads canonical records only; never ingests discoveries, approves events or publishes.
"""
import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from pipeline import ROOT, CENTRAL, read, write, assign, generate, target, week, dt
from validate_post import validate_output

WINDOW_START_HOUR = 7   # 07:00 America/Chicago
WINDOW_END_HOUR = 11    # tolerate GitHub schedule queue delays without running twice


def is_wednesday_slot(instant):
    """Exact 07:00 Central hour (kept for compatibility)."""
    local = instant.astimezone(CENTRAL)
    return local.weekday() == 2 and local.hour == 7


def should_run_scheduled(instant, root=ROOT):
    """Run once per Wednesday at/after 07:00 Central, DST-aware, tolerant of queue delays."""
    local = instant.astimezone(CENTRAL)
    if local.weekday() != 2 or not (WINDOW_START_HOUR <= local.hour < WINDOW_END_HOUR):
        return False
    marker = Path(root) / 'weeks/current-handoff.json'
    if marker.is_file():
        previous = read(marker)
        if previous.get('generated_on_local_date') == local.date().isoformat() and previous.get('roundup_identifier') == target(local.date()):
            return False
    return True


def prepare(root=ROOT, day=None, check_registrations=True, fetcher=None, generated_at=None):
    from qualification import run_checks, fetch
    root = Path(root)
    day = day or datetime.now(CENTRAL).date()
    events = assign(root, day)
    if check_registrations:
        label = target(day)
        run_checks(root, [e for e in events if week(dt(e['start_datetime'])) == label], fetcher or fetch, generated_at)
    folder = generate(root, day, generated_at)
    report = read(folder / 'editorial-report.json')
    if report['total_eligible_events_for_target_week']:
        validate_output(root, day)
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--as-of', type=date.fromisoformat)
    parser.add_argument('--scheduled', action='store_true')
    parser.add_argument('--skip-registration-checks', action='store_true', help='Offline/test only; events without current checks are excluded')
    args = parser.parse_args()
    if args.scheduled:
        if not read(args.root / 'config/schedule.yml').get('wednesday_preparation', {}).get('recurring_enabled', False):
            raise SystemExit('Recurring preparation is disabled; owner activation required')
        if not should_run_scheduled(datetime.now(timezone.utc), args.root):
            print('Outside the Wednesday 07:00 America/Chicago window or already generated today; skipping.')
            raise SystemExit(0)
    print(prepare(args.root, args.as_of, not args.skip_registration_checks))
