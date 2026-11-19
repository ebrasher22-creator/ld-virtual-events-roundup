import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from persist_outputs import persist

class PersistenceTests(unittest.TestCase):
    def execute(self, conclusion, state='CLEAN'):
        calls=[]
        sha='a'*40
        def command(*args):
            calls.append(args)
            if args[:3]==('git','diff','--cached'):return 'data/canonical-events.json'
            if args[:2]==('git','rev-parse'):return sha
            if args[:3]==('gh','pr','create'):return 'https://github.com/owner/repo/pull/1'
            if args[:3]==('gh','run','list'):
                return json.dumps([dict(headSha=sha,status='completed',conclusion=conclusion,url='https://github.com/owner/repo/actions/runs/1')])
            if args[:3]==('gh','pr','view'):
                return state if '.mergeStateStatus' in args else 'merged-sha'
            return ''
        with patch('persist_outputs.command',side_effect=command),patch.dict('os.environ',GITHUB_RUN_ID='123'):
            if conclusion=='success':self.assertEqual(persist('intake','owner/repo'),'merged-sha')
            else:
                with self.assertRaises(ValueError):persist('intake','owner/repo')
        return calls,sha

    def test_status_is_written_only_after_actual_matching_commit_validation(self):
        calls,sha=self.execute('success')
        status=next(i for i,c in enumerate(calls) if c[:3]==('gh','api','--method'))
        self.assertIn('repos/owner/repo/statuses/'+sha,calls[status])
        self.assertLess(next(i for i,c in enumerate(calls) if c[:3]==('gh','run','list')),status)
        self.assertLess(status,next(i for i,c in enumerate(calls) if c[:3]==('gh','pr','merge')))

    def test_failed_validation_never_attests_success_or_merges(self):
        calls,_=self.execute('failure')
        self.assertFalse(any(c[:2]==('gh','api') or c[:3]==('gh','pr','merge') for c in calls))

    def test_optional_check_state_still_uses_normal_protected_merge(self):
        calls,_=self.execute('success','UNSTABLE')
        merge=next(c for c in calls if c[:3]==('gh','pr','merge'))
        self.assertNotIn('--admin',merge)
        self.assertIn('--match-head-commit',merge)
