"""One-command supervised Work return: official validation -> self-contained review packet.

No event ingestion, Git writes, task scheduling, network/model calls or message delivery.
Output is restricted to review-packets/; approved repository files remain read-only.
"""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
from pipeline import ROOT, read, target, write
from validate_work_caption import validate_submission


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected_hashes(root,input_path):
    paths=[*sorted((root/'data').glob('*.json')),*sorted((root/'approvals').glob('*')),input_path]
    return {p.relative_to(root).as_posix():sha(p) for p in paths if p.is_file()}


def receive(root, submission, as_of, output_dir=None):
    root=Path(root).resolve()
    submission=Path(submission).resolve()
    label=target(as_of)
    input_path=root/'weeks'/label/'editorial-input.json'
    # Require an existing approved snapshot; this entry point never regenerates it.
    payload=read(input_path)
    original=submission.read_bytes()
    received_at=datetime.now(timezone.utc).isoformat(timespec='microseconds')
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+hashlib.sha256(original).hexdigest()[:12]
    output=Path(output_dir) if output_dir else root/'review-packets'/label/run_id
    if not output.is_absolute():output=root/output
    output=output.resolve()
    output.relative_to(root/'review-packets')
    if output==root/'review-packets':raise ValueError('Choose a packet subdirectory')
    if output.exists():raise FileExistsError('Packet directories are immutable; choose a new output directory')
    before=protected_hashes(root,input_path)
    with tempfile.TemporaryDirectory(prefix='ld-editorial-return-') as temporary:
        staging=Path(temporary)/'packet'
        staging.mkdir()
        (staging/'work-submission.json').write_bytes(original)
        result=validate_submission(root,input_path,staging/'work-submission.json',staging)
        assert protected_hashes(root,input_path)==before,'Protected event/approval files changed during validation'
        status=dict(packet_format_version=1,roundup_identifier=label,received_at=received_at,
                    event_count=len(payload['events']),input_checksum=payload['editorial_input_sha256'],
                    submission_file_sha256=hashlib.sha256(original).hexdigest(),mechanical_validation=result['result'],
                    semantic_review_required=True,publication_approval_status='awaiting_final_human_review',
                    delivery_status='prepared_not_sent',canonical_approvals_and_input_unchanged=True,
                    automatic_steps=['checksum and current approval verification','caption fact/coverage/order/URL/length validation','review packet assembly'],
                    manual_steps=['download/export Work result if no authenticated submission tool is available','invoke this return command or upload to reviewed draft intake','transfer packet to owner/Jarvis','final caption approval and manual LinkedIn publication'])
        write(staging/'publication-status.json',status)
        write(staging/'protected-file-hashes.json',dict(before=before,after=before,unchanged=True))
        if result['mechanical_validation_passed']:
            full=(staging/'linkedin-work-post.md').read_text()
            compact=(staging/'linkedin-work-post-compact.md').read_text()
            # Clear human-facing names; existing validator-native artifacts are also retained.
            (staging/'linkedin-post.md').write_text(full)
            (staging/'linkedin-post-compact.md').write_text(compact)
            message=f'''Next Week in L&D — supervised weekly review handoff

Roundup: {label}
Approved event count: {len(payload['events'])}
Input checksum: {payload['editorial_input_sha256']}
Repository mechanical validation: PASS
Full caption: {len(full)} characters; compact: {len(compact)} characters; limit: {payload['constraints']['character_limit']}.
Semantic/editorial review and final publication approval: PENDING.

This packet is for review only. Do not publish, merge, change facts/approvals, create a task or alter any schedule. No repository access is required to read the captions below. Acknowledge the roundup, event count and pending approval status; do not describe receipt as publication approval. Scheduled automatic delivery is not established by this supervised transfer.

FULL CAPTION

{full}

COMPACT ALTERNATIVE

{compact}

VALIDATION REPORT

{json.dumps(result,indent=2)}
'''
            (staging/'jarvis-message.txt').write_text(message)
            (staging/'review-checklist.md').write_text('''# Final human caption decision

- [ ] Review the full and compact captions for voice, grounded interpretation and community value.
- [ ] Confirm the packet week, event count and input checksum match the intended run.
- [ ] Read the official validation report and confirm no mechanical failure remains.
- [ ] Choose the final caption and record approve / hold / reject separately.
- [ ] Publish manually only after explicit final approval.

Final decision: ______  Reviewer: ______  Time: ______
''')
        else:
            (staging/'REVISION-REQUIRED.md').write_text('# Editorial revision required\n\nThe submission failed official validation. No publishable caption or Jarvis delivery message was generated. See validation-report.json and revise the draft without changing approved input.\n')
        output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(staging,output)
    archive=output/'review-packet.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for path in sorted(output.iterdir()):
            if path.is_file() and path!=archive:package.write(path,path.name)
    return output,result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--submission',type=Path,required=True)
    parser.add_argument('--as-of',type=date.fromisoformat,required=True)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    folder,result=receive(args.root,args.submission,args.as_of,args.output_dir)
    print(result['result'].upper()+': '+str(folder))
    raise SystemExit(0 if result['mechanical_validation_passed'] else 1)
