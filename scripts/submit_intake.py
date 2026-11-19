"""Agent-side discovery submission (P2/P3): validate -> unique intake branch -> draft PR against main.

Usage (from a clone of the repository, authenticated through the existing GitHub connection/CLI):

    python3 scripts/submit_intake.py --agent antigravity --file /path/to/findings.json

The file must be a JSON array matching schemas/event-discovery.schema.json with
discovered_by == [<agent>]. The script never merges, approves, publishes, edits canonical data
or overwrites an existing intake file. Credentials are never read or printed by this script;
git/gh use the machine's existing authorized credential store.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

from pipeline import CENTRAL, validate_intake_batch, target, week, dt, canonical_streams

AGENTS = ('chatgpt', 'antigravity')


def run(*args, cwd=None, capture=True):
    return subprocess.run(list(args), cwd=cwd, check=True, capture_output=capture, text=True).stdout.strip()


def summarize(batch, today):
    label = target(today)
    in_week = [e for e in batch if week(dt(e['start_datetime'])) == label]
    later = [e for e in batch if week(dt(e['start_datetime'])) > label]
    return label, in_week, later


def submit(agent, source_file, repo_dir='.', base='main', dry_run=False, incomplete_leads=None):
    repo_dir = Path(repo_dir).resolve()
    source_file = Path(source_file).resolve()
    batch = json.loads(source_file.read_text())
    now = datetime.now(CENTRAL)
    stamp = now.strftime('%Y-%m-%d')
    name = f'{agent}-{stamp}.json'
    relative = f'intake/{agent}/{name}'
    validate_intake_batch(repo_dir / relative, batch)
    label, in_week, later = summarize(batch, now.date())
    suffix = now.strftime('%H%M%S') + '-' + uuid.uuid4().hex[:8]
    branch = f'intake/{agent}-{stamp}-{suffix}'
    if dry_run:
        return dict(branch=branch, file=relative, records=len(batch), target_week=label, target_week_records=len(in_week), later_records=len(later), pr_url=None)
    run('git', 'fetch', '--no-tags', 'origin', base, cwd=repo_dir)
    existing = run('git', 'ls-tree', '-r', '--name-only', f'origin/{base}', f'intake/{agent}/', cwd=repo_dir).splitlines()
    if relative in existing:
        name = f'{agent}-{stamp}-{suffix}.json'
        relative = f'intake/{agent}/{name}'
    workdir = Path(tempfile.mkdtemp(prefix='ld-intake-'))
    try:
        run('git', 'worktree', 'add', '-q', '-b', branch, str(workdir), f'origin/{base}', cwd=repo_dir)
        destination = workdir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, destination)
        # Validate with the production branch's own trusted validator before submitting.
        run(sys.executable, 'scripts/validate.py', relative, cwd=workdir)
        run('git', 'add', relative, cwd=workdir)
        display = 'ChatGPT' if agent == 'chatgpt' else 'Antigravity'
        run('git', '-c', f'user.name={display} Discovery', '-c', f'user.email={agent}-discovery@users.noreply.github.com',
            'commit', '-q', '-m', f'{display} discovery intake {stamp} ({len(batch)} records)', cwd=workdir)
        run('git', 'push', '-q', '-u', 'origin', branch, cwd=workdir)
        body = '\n'.join([
            f'Automated {display} discovery submission.',
            '',
            f'- File: `{relative}` ({len(batch)} records; `discovered_by: ["{agent}"]`)',
            f'- Target roundup: {label} — {len(in_week)} records',
            f'- Later weeks retained: {len(later)} records',
            f'- Incomplete leads reported separately: {incomplete_leads if incomplete_leads is not None else "see agent run report"}',
            '- Local validation: `python3 scripts/validate.py` PASS',
            '',
            'Processed automatically by the Process discovery intake workflow. Do not merge manually; automation copies the data to main and closes this PR.',
        ])
        pr_url = run('gh', 'pr', 'create', '--draft', '--base', base, '--head', branch,
                     '--title', f'[intake] {display} discovery {stamp}', '--body', body, cwd=workdir)
        return dict(branch=branch, file=relative, records=len(batch), target_week=label, target_week_records=len(in_week), later_records=len(later), pr_url=pr_url)
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', str(workdir)], cwd=repo_dir, capture_output=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--agent', choices=AGENTS, required=True)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--repo-dir', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--base', default='main')
    parser.add_argument('--incomplete-leads', type=int)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(submit(args.agent, args.file, args.repo_dir, args.base, args.dry_run, args.incomplete_leads), indent=2))
