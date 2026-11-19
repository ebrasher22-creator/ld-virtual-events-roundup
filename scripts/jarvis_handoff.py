"""Read-only validation of the current weekly packet before presenting it to Eddie."""
import argparse
from datetime import date, datetime
from pathlib import Path
from pipeline import ROOT, CENTRAL, read, target, dt
from validate_post import validate_output


def inspect(root=ROOT, today=None):
    root = Path(root)
    today = today or datetime.now(CENTRAL).date()
    label = target(today)
    marker = root / 'weeks/current-handoff.json'
    if not marker.is_file():
        return dict(readiness_status='not_ready_action_required', reason='missing_current_handoff', roundup_identifier=label)
    handoff = read(marker)
    if handoff.get('roundup_identifier') != label or handoff.get('generated_on_local_date') != today.isoformat():
        return dict(readiness_status='not_ready_action_required', reason='stale_or_wrong_week_handoff', roundup_identifier=label)
    try:
        folder = validate_output(root, today)
        report = read(folder / 'editorial-report.json')
        if dt(report['generated_at']).astimezone(CENTRAL).date() != today:
            raise ValueError('report_not_generated_today_chicago')
        text = (folder / 'linkedin-post.md').read_text()
        if handoff['event_count'] != len(report['events_included']) or handoff['character_counts'] != report['character_counts']:
            raise ValueError('handoff_report_count_mismatch')
        if handoff['generated_at'] != report['generated_at'] or handoff['readiness_status'] != report['readiness_status']:
            raise ValueError('handoff_report_status_mismatch')
        if report['qualification_mode'] != 'automated_no_per_event_human_approval':
            raise ValueError('unexpected_qualification_mode')
        return dict(handoff, actual_characters=len(text), message='Eddie reviews and decides publication; nothing published.')
    except (ValueError, KeyError, OSError, TypeError) as exc:
        return dict(readiness_status='not_ready_action_required', reason=str(exc), roundup_identifier=label)


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--date', type=date.fromisoformat)
    args = parser.parse_args()
    result = inspect(args.root, args.date)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result['readiness_status'] == 'not_ready_action_required' else 0)
