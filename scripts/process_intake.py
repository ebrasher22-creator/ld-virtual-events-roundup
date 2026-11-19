"""Automated discovery intake processing (P6). Submissions are data only; nothing they contain is executed.

Flow: agent opens a draft PR from intake/<agent>-<id> adding only intake/<agent>/<file>.json ->
this trusted main-branch code fetches the added blobs, validates schema + source identity, copies valid
files append-only into intake/, quarantines invalid ones (original bytes preserved), runs ingestion /
consolidation / week assignment, and writes a machine-readable report. The workflow then commits to
main and closes the PR with a link to the processing commit. PR branches are retained for audit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

from pipeline import ROOT, CENTRAL, read, write, ingest, assign, validate_intake_batch, canonical_streams, dt, target

BRANCH_RE = re.compile(r'^intake/(chatgpt|antigravity)-[A-Za-z0-9._-]{1,80}$')
FILE_RE = re.compile(r'^intake/(chatgpt|antigravity)/[A-Za-z0-9._-]{1,100}\.json$')
MAX_BYTES = 2_000_000


class GitHubSource:
    """Reads open intake PRs through the GitHub CLI using the workflow token."""

    def __init__(self, repo, root):
        self.repo, self.root = repo, Path(root)

    def _gh(self, *args):
        return json.loads(subprocess.run(['gh', *args], capture_output=True, text=True, check=True).stdout or 'null')

    def pull_requests(self, numbers=None):
        prs = self._gh('api', '--paginate', '--slurp', f'repos/{self.repo}/pulls?state=open&per_page=100')
        prs = [p for page in prs for p in page]
        return [p for p in prs if BRANCH_RE.match(p['head']['ref']) and (not numbers or p['number'] in numbers)]

    def files(self, pr):
        pages = self._gh('api', '--paginate', '--slurp', f'repos/{self.repo}/pulls/{pr["number"]}/files?per_page=100')
        return [dict(filename=f['filename'], status=f['status']) for page in pages for f in page]

    def blob(self, pr, path):
        sha = pr['head']['sha']
        subprocess.run(['git', '-C', str(self.root), 'fetch', '--no-tags', 'origin', f'refs/pull/{pr["number"]}/head'], check=True, capture_output=True)
        return subprocess.run(['git', '-C', str(self.root), 'show', f'{sha}:{path}'], check=True, capture_output=True).stdout


def quarantine(root, agent, pr_number, name, content, reason):
    folder = Path(root) / 'quarantine' / agent
    folder.mkdir(parents=True, exist_ok=True)
    stem = f'pr{pr_number}-{name}'
    data_path = folder / stem
    if data_path.exists() and data_path.read_bytes() != content:
        stem = f'{stem}-{hashlib.sha256(content).hexdigest()[:16]}'
        data_path = folder / stem
    if not data_path.exists():
        data_path.write_bytes(content)
    write(folder / (stem + '.errors.json'), dict(pr=pr_number, file=name, reason=reason, sha256=hashlib.sha256(content).hexdigest(),
                                                  quarantined_at=datetime.now(timezone.utc).isoformat(timespec='seconds')))
    return data_path.relative_to(root).as_posix()


def stage_file(root, agent, path, content, pr_number, test_only=False):
    root = Path(root)
    name = Path(path).name
    digest = hashlib.sha256(content).hexdigest()
    if len(content) > MAX_BYTES:
        return dict(file=path, sha256=digest, outcome='quarantined', reason='file_too_large', location=quarantine(root, agent, pr_number, name, content, 'file_too_large'))
    destination = root / path
    if destination.exists():
        if destination.read_bytes() == content:
            return dict(file=path, sha256=digest, outcome='already_processed')
        reason = 'append_only_violation: a different submission already exists at this path'
        return dict(file=path, sha256=digest, outcome='quarantined', reason=reason, location=quarantine(root, agent, pr_number, name, content, reason))
    try:
        batch = json.loads(content.decode('utf-8'))
        validate_intake_batch(destination, batch)
        if not test_only:
            from urllib.parse import urlsplit
            for record in batch:
                domain = (urlsplit(record['event_url']).hostname or '').lower()
                if domain in {'example.org', 'example.com', 'example.net', 'localhost'} or domain.endswith(('.example', '.invalid', '.test')):
                    raise ValueError('synthetic_or_reserved_event_source')
    except (ValueError, UnicodeDecodeError) as exc:
        reason = str(exc)[:500]
        return dict(file=path, sha256=digest, outcome='quarantined', reason=reason, location=quarantine(root, agent, pr_number, name, content, reason))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return dict(file=path, sha256=digest, outcome='accepted', records=len(batch))


def review_pull_request(root, source, repo, pr):
    head = pr['head']
    result = dict(number=pr['number'], branch=head['ref'], head_sha=head['sha'], files=[])
    match = BRANCH_RE.match(head['ref'])
    if (head.get('repo') or {}).get('full_name') != repo:
        return dict(result, outcome='rejected', reason='cross_repository_pull_request')
    if not match:
        return dict(result, outcome='rejected', reason='invalid_branch')
    if pr.get('base', {}).get('ref') != 'main':
        return dict(result, outcome='rejected', reason='incorrect_base')
    if pr.get('user', {}).get('login') != repo.split('/')[0]:
        return dict(result, outcome='rejected', reason='unauthorized_submitter')
    agent = match.group(1)
    result['agent'] = agent
    files = source.files(pr)
    invalid = [f for f in files if f['status'] != 'added' or not FILE_RE.match(f['filename']) or f['filename'].split('/')[1] != agent]
    if not files or len(files) > 50 or invalid:
        return dict(result, outcome='rejected', reason='pull request must only add intake/' + agent + '/<file>.json',
                    offending_files=[f['filename'] for f in invalid])
    for f in files:
        result['files'].append(stage_file(root, agent, f['filename'], source.blob(pr, f['filename']), pr['number'], getattr(source, 'test_only', False)))
    outcomes = {f['outcome'] for f in result['files']}
    result['outcome'] = 'quarantined' if 'quarantined' in outcomes else ('accepted' if 'accepted' in outcomes else 'already_processed')
    return result


def summarize(root, before_ids, day):
    events = read(Path(root) / 'data/canonical-events.json')
    future = read(Path(root) / 'data/future-events.json')
    by_week = {}
    for e in events:
        by_week[e['roundup_week']] = by_week.get(e['roundup_week'], 0) + 1
    return dict(total_canonical_events=len(events), new_canonical_events=sorted(e['event_id'] for e in events if e['event_id'] not in before_ids),
                cross_agent_consolidated=sorted(e['event_id'] for e in events if len(canonical_streams(e['discovered_by'])) > 1),
                events_with_conflict_flags={e['event_id']: e['conflict_flags'] for e in events if e.get('conflict_flags')},
                events_by_week=dict(sorted(by_week.items())), future_events=len(future), target_week=target(day))


def process(root=ROOT, repo=None, source=None, numbers=None, day=None, now=None):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    day = day or now.astimezone(CENTRAL).date()
    source = source or GitHubSource(repo, root)
    before_ids = {e['event_id'] for e in read(root / 'data/canonical-events.json')}
    reviewed = [review_pull_request(root, source, repo, pr) for pr in source.pull_requests(numbers)]
    accepted = any(f.get('outcome') == 'accepted' for r in reviewed for f in r.get('files', []))
    report = dict(processed_at=now.isoformat(timespec='seconds'), repository=repo, pull_requests=reviewed, ingestion_run=accepted)
    if accepted:
        ingest(root, migrate_reviews=False)
        assign(root, day)
        report['consolidation'] = summarize(root, before_ids, day)
    folder = root / 'reports/intake-processing'
    if reviewed:
        stamp = now.strftime('%Y%m%dT%H%M%SZ')
        write(folder / f'{stamp}.json', report)
        write(folder / 'latest.json', report)
    return report


def notify(repo, report, commit_sha):
    """Comment on and close processed intake PRs; branches remain for audit."""
    for pr in report.get('pull_requests', []):
        lines = [f'Automated intake processing: **{pr["outcome"]}**.']
        if pr.get('reason'):
            lines.append('Reason: ' + pr['reason'])
        for f in pr.get('files', []):
            lines.append(f'- `{f["file"]}` → {f["outcome"]}' + (f' ({f.get("reason")})' if f.get('reason') else ''))
        if commit_sha and pr['outcome'] in ('accepted', 'quarantined'):
            lines.append(f'Processing commit on main: https://github.com/{repo}/commit/{commit_sha}')
        lines.append('This PR is closed by automation, not merged; its branch is retained as the original submission record.')
        body = '\n'.join(lines)
        subprocess.run(['gh', 'pr', 'comment', str(pr['number']), '-R', repo, '--body', body], check=False)
        if pr['outcome'] in ('accepted', 'quarantined', 'already_processed'):
            subprocess.run(['gh', 'pr', 'close', str(pr['number']), '-R', repo], check=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--phase', choices=['stage', 'notify'], required=True)
    parser.add_argument('--pr', type=int, action='append', help='Limit to specific PR numbers')
    parser.add_argument('--commit')
    parser.add_argument('--report-out', type=Path, help='Per-run report copy used by the notify phase')
    args = parser.parse_args()
    if args.phase == 'stage':
        result = process(args.root, args.repo, numbers=args.pr)
        if args.report_out:
            write(args.report_out, result)
        print(json.dumps(dict(pull_requests=[(p['number'], p['outcome']) for p in result['pull_requests']], ingestion_run=result['ingestion_run'])))
    else:
        if args.report_out and args.report_out.is_file():
            notify(args.repo, read(args.report_out), args.commit)
