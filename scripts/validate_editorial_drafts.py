"""Owner-mediated JSON draft intake; safe for read-only CI, never executes returned content."""
import argparse
from datetime import date
from pathlib import Path
import re
from pipeline import ROOT, read, write, target
from validate_work_caption import validate_submission


def validate_files(root=ROOT, files=None, expected_as_of=None):
    root=Path(root).resolve()
    files=files or sorted((root/'editorial-drafts').rglob('*.json'))
    passed=True
    for filename in files:
        path=Path(filename)
        if not path.is_absolute(): path=root/path
        # Drafts must be explicit JSON files in this dedicated intake directory.
        relative=path.resolve().relative_to((root/'editorial-drafts').resolve())
        output=root/'reports/work-editorial'/relative.with_suffix('')
        try:
            if path.suffix!='.json': raise ValueError('Only JSON draft submissions are supported')
            draft=read(path)
            label=draft['roundup_identifier']
            if not isinstance(label,str) or not re.fullmatch(r'\d{4}/RW\d{2}_\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}',label):
                raise ValueError('Invalid roundup identifier')
            if expected_as_of and label!=target(expected_as_of): raise ValueError('Submission week does not match the requested preparation date')
            result=validate_submission(root,root/'weeks'/label/'editorial-input.json',path,output)
        except (ValueError,KeyError,TypeError,OSError) as exc:
            result=dict(result='fail',mechanical_validation_passed=False,errors=[str(exc)],semantic_review_required=True,publication_approval_status='awaiting_final_human_review')
            write(output/'validation-report.json',result)
            for name in ['linkedin-work-post.md','linkedin-work-post-compact.md','jarvis-handoff.md']:
                (output/name).unlink(missing_ok=True)
        passed=passed and result['mechanical_validation_passed']
        print(result['result'].upper()+': '+str(output))
    return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--as-of',type=date.fromisoformat)
    parser.add_argument('files',nargs='*')
    args=parser.parse_args()
    raise SystemExit(0 if validate_files(args.root,args.files,args.as_of) else 1)
