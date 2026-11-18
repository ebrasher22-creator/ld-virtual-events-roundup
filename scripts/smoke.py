"""Isolated synthetic acceptance demonstration; never writes production data."""
import shutil
import tempfile
from datetime import date
from pathlib import Path
from pipeline import ROOT, read, write, ingest, assign, generate, fingerprint, CLAIMS

def run():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        shutil.copytree(ROOT/'config',root/'config')
        shutil.copytree(ROOT/'templates',root/'templates')
        for agent in ['chatgpt','gemini']: (root/'intake'/agent).mkdir(parents=True)
        write(root/'data/canonical-events.json',[])
        write(root/'data/reviews.json',{})
        for agent in ['chatgpt','gemini']:
            shutil.copy(ROOT/f'tests/fixtures/{agent}.json',root/f'intake/{agent}/sample.json')
        # A separate nonconflicting synthetic record exercises reviewed draft rendering.
        sample=read(ROOT/'tests/fixtures/chatgpt.json')[0]
        sample.update(title='Fixture: Reviewed learning session',registration_url='https://example.org/register/reviewed')
        write(root/'intake/chatgpt/reviewed.json',[sample])
        ingest(root);events=assign(root,date(2026,11,24))
        empty_folder=generate(root,date(2026,11,24),generated_at='2026-11-24T20:00:00Z')
        assert read(empty_folder/'review.json')['selected_ids']==[]
        unverified=read(empty_folder/'review.json')
        before=(root/'data/canonical-events.json').read_bytes()
        ingest(root);assign(root,date(2026,11,24))
        assert before==(root/'data/canonical-events.json').read_bytes()
        chosen=next(e for e in events if e['title']==sample['title'])
        review=dict(record_sha256=fingerprint(chosen),decision='verified',editorial_decision='selected',reviewer='SYNTHETIC TEST REVIEW',verified_at='2026-11-24T20:00:00Z',claims={k:dict(primary_url=chosen['event_url'],observation='SIMULATED primary-source check for smoke test only') for k in CLAIMS})
        write(root/'data/reviews.json',{chosen['event_id']:review})
        folder=generate(root,date(2026,11,24),generated_at='2026-11-24T20:00:00Z')
        assert len(events)==3 and len(read(root/'data/future-events.json'))==1
        assert len(read(folder/'review.json')['selected_ids'])==1
        output=ROOT/'tests/smoke-output'
        shutil.copytree(folder,output,dirs_exist_ok=True)
        write(output/'canonical-events.json',events)
        write(output/'future-events.json',read(root/'data/future-events.json'))
        write(output/'unverified-review.json',unverified)
        write(output/'reviews-SYNTHETIC.json',{chosen['event_id']:review})
        print('PASS: both agents, overlap, conflict, future retention, rerun stability, review gate and Markdown generation')
        print(output)

if __name__=='__main__':run()
