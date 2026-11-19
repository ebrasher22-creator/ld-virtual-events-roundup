"""Persist trusted data outputs through a validated PR; never bypass main's branch rules."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ALLOWED = {
    'intake': ('intake/chatgpt/', 'intake/antigravity/', 'data/canonical-events.json', 'data/future-events.json', 'reports/intake-processing/', 'quarantine/'),
    'editorial': ('weeks/', 'data/canonical-events.json', 'data/future-events.json', 'data/registration-checks.json'),
}


def allowed_output(path, kind):
    return any(path.startswith(p) if p.endswith('/') else path == p for p in ALLOWED[kind])


def command(*args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return result.stdout.strip()


def persist(kind, repo):
    paths = command('git', 'diff', '--cached', '--name-only', '-z').split('\0')
    paths = [p for p in paths if p]
    if not paths:
        return command('git', 'rev-parse', 'HEAD')
    if any(not allowed_output(p, kind) for p in paths):
        raise ValueError('Refusing to persist changes outside the trusted output paths')
    branch = f'automation/{kind}-{os.environ["GITHUB_RUN_ID"]}-{os.environ.get("GITHUB_RUN_ATTEMPT", "1")}'
    command('git', 'switch', '-c', branch)
    command('git', 'commit', '-m', f'Persist trusted {kind} output for final publication review')
    sha = command('git', 'rev-parse', 'HEAD')
    command('git', 'push', 'origin', branch)
    with tempfile.NamedTemporaryFile('w', suffix='.md') as body:
        body.write('Repository-controlled workflow output only. No discovery-supplied code was executed.\n\nValidation is explicitly dispatched before this PR can merge. No LinkedIn publication or individual event approval occurs.\n')
        body.flush()
        pr = command('gh', 'pr', 'create', '--repo', repo, '--base', 'main', '--head', branch,
                     '--title', f'Automated {kind} persistence', '--body-file', body.name)
    # GITHUB_TOKEN-created PRs do not automatically trigger PR CI. workflow_dispatch does.
    command('gh', 'workflow', 'run', 'validate.yml', '--repo', repo, '--ref', branch)
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        runs = json.loads(command('gh', 'run', 'list', '--repo', repo, '--workflow', 'validate.yml', '--branch', branch,
                                 '--event', 'workflow_dispatch', '--limit', '10', '--json', 'headSha,status,conclusion,url'))
        matching = [r for r in runs if r['headSha'] == sha]
        if matching and matching[0]['status'] == 'completed':
            if matching[0]['conclusion'] != 'success':
                raise ValueError('Trusted output validation failed; PR left open for diagnosis')
            # Publish evidence only for the exact SHA validated by the trusted workflow.
            command('gh', 'api', '--method', 'POST', f'repos/{repo}/statuses/{sha}',
                    '-f', 'state=success', '-f', 'context=validate',
                    '-f', 'description=Trusted dispatched validation passed for this exact commit',
                    '-f', 'target_url=' + matching[0]['url'])
            ready_deadline = time.monotonic() + 60
            while time.monotonic() < ready_deadline:
                state = command('gh', 'pr', 'view', pr, '--repo', repo, '--json', 'mergeStateStatus', '--jq', '.mergeStateStatus')
                if state == 'CLEAN':
                    break
                time.sleep(3)
            else:
                raise ValueError('PR policy still blocks merge after exact-commit validation; no bypass attempted')
            command('gh', 'pr', 'merge', pr, '--repo', repo, '--merge', '--match-head-commit', sha)
            return command('gh', 'pr', 'view', pr, '--repo', repo, '--json', 'mergeCommit', '--jq', '.mergeCommit.oid')
        time.sleep(5)
    raise TimeoutError('Validation did not complete in 10 minutes; PR retained, nothing merged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=ALLOWED, required=True)
    parser.add_argument('--repo', required=True)
    args = parser.parse_args()
    sha = persist(args.kind, args.repo)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('sha=' + sha + '\n')
    print('Persisted commit:', sha)
