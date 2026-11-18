"""Manual pilot entry point. Recurring mode requires explicit configuration activation."""
import argparse
from datetime import date, datetime
from pathlib import Path
from pipeline import ROOT, CENTRAL, read, assign, generate
from validate_post import validate_output


def is_wednesday_slot(instant):
    local=instant.astimezone(CENTRAL)
    return local.weekday()==2 and local.hour==7


def prepare(root=ROOT, day=None):
    # Read persisted approvals only. Never ingest new discoveries or create human approvals here.
    assign(root,day)
    folder=generate(root,day)
    validate_output(root,day)
    return folder


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--as-of',type=date.fromisoformat)
    parser.add_argument('--scheduled',action='store_true')
    args=parser.parse_args()
    if args.scheduled:
        if not read(args.root/'config/schedule.yml').get('wednesday_preparation',{}).get('recurring_enabled',False):
            raise SystemExit('Recurring preparation is disabled; owner activation required')
        if not is_wednesday_slot(datetime.now(CENTRAL)):
            raise SystemExit('Outside the Wednesday 07:00 America/Chicago preparation window')
    print(prepare(args.root,args.as_of))
