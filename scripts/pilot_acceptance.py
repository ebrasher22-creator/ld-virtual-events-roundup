"""Supervised approved-seven-record acceptance check; operates in a temporary copy."""
from pathlib import Path
from datetime import date
import hashlib
import shutil
import tempfile
from pipeline import ROOT, read, write, eligible, assign, generate, ingest
from validate_post import validate_output


def run():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        for directory in ['config','templates','data','intake','approvals']:
            shutil.copytree(ROOT/directory,root/directory)
        events=read(root/'data/canonical-events.json')
        reviews=read(root/'data/reviews.json')
        assert len(events)==7 and all(eligible(e,reviews,root) for e in events)
        assert all(not r['claims'] and r['verified_at'] is None for r in reviews.values())
        assert all(r['attestation']['type']=='explicit_owner_approval' for r in reviews.values())
        assert len({r['attestation']['source_sha256'] for r in reviews.values()})==1
        initial=(root/'data/canonical-events.json').read_bytes()
        ingest(root)
        assert (root/'data/canonical-events.json').read_bytes()==initial
        assign(root,date(2026,11,24))
        assert len(read(root/'data/future-events.json'))==2
        assert (root/'data/canonical-events.json').read_bytes()==initial
        folder=generate(root,date(2026,11,24),generated_at='2026-11-18T20:00:00Z')
        validate_output(root,date(2026,11,24))
        report=read(folder/'editorial-report.json')
        assert report['total_approved_events_for_target_week']==5
        assert len(report['events_included'])==5
        assert len(report['events_excluded'])==2
        assert all(x['reason']=='outside_target_week' for x in report['events_excluded'])
        assert report['below_target'] and not report['editorial_exceptions']
        full=(folder/'linkedin-post.md').read_text()
        compact=(folder/'linkedin-post-compact.md').read_text()
        for text in [full,compact]:
            assert len(text)<=3000
            for expected in ['Tue, Dec 1, 2026 | 12:00 PM CST','Wed, Dec 2, 2026 | 9:00 AM CST','Wed, Dec 2, 2026 | 10:00 AM CST','Wed, Dec 2, 2026 | 11:00 AM CST','Thu, Dec 3, 2026 | 10:00 AM CST']:
                assert expected in text,expected
            assert 'AI in the Flow of Work' not in text and 'Intro to Facilitating Groups' not in text
        assert len(report['missing_optional_pricing'])==5
        assert '| Free' not in full and '| Paid' not in full
        # Labels are absent because price was not separately attested; raw price values stay intact.
        assert all(e['price_type']=='free' for e in events)
        generate(root,date(2026,11,24),generated_at='2026-11-18T20:00:01Z')
        second=read(folder/'editorial-report.json')
        assert full==(folder/'linkedin-post.md').read_text()
        assert compact==(folder/'linkedin-post-compact.md').read_text()
        assert report.pop('generated_at')!=second.pop('generated_at')
        assert report==second
        futurefolder=generate(root,date(2026,12,1),generated_at='2026-11-18T20:00:00Z')
        assert len(read(futurefolder/'editorial-report.json')['events_included'])==2
        result=dict(result='PASS',approved_events=7,rw49_eligible_and_included=5,rw50_retained_and_eligible=2,owner_approval_source_preserved=True,individual_observations_fabricated=False,price_values_preserved=True,unconfirmed_price_labels_omitted=5,unknown_price_eligibility='covered by regression test_unknown_pricing_stays_eligible_without_price_claim',all_five_expected_cst_times=True,full_characters=len(full),compact_characters=len(compact),limit=3000,captions_stable_on_rerun=True,report_only_generation_timestamp_changed=True,intake_rerun_preserves_approvals=True,publication_approval_status='awaiting_final_human_review',publication_performed=False,merge_performed=False)
        write(ROOT/'reports/pilots/chatgpt-2026-11-18/wednesday/acceptance-results.json',result)
        print(result)


if __name__=='__main__':run()
