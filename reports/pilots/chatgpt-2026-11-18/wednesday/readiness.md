# Wednesday LinkedIn preparation — supervised pilot

**RW49 draft ready for final human caption review.** The owner-approved collection contains five RW49 events and two RW50 events. No new event research or repeated source verification was performed. Nothing has been published, merged or deployed; recurrence remains disabled.

## Approval and canonical transition

The exact owner request is preserved in `approvals/2026-11-18-owner-wednesday-authorization.md`. Seven current canonical records and seven review entries bind the original approval source and final record fingerprints. The compatible attestation route represents the owner's explicit verification/inclusion decision without fabricated individual observations or historical check timestamps. `recorded_at` records decision capture only. The original intake and each raw submission remain unchanged. The previously user-supplied Intro registration correction is applied with stable identity, old alias and resolution notes.

All seven original price_type values remain free. There was no separately captured per-event pricing confirmation; pricing is optional and labels are omitted from this caption, rather than inferred. Explicitly confirmed Free/Paid labels and otherwise-approved unknown pricing are covered by regression tests. Price omissions do not block the pilot.

## Results

- Complete regression suite: **29 passed; 0 failed**.
- Original synthetic smoke and supervised approved-seven end-to-end acceptance: passed.
- Exactly **5 approved RW49 events**, all included; **2 RW50 events retained**, approved and usable in their own week.
- CST starts: Dec 1 noon; Dec 2 at 9 AM, 10 AM and 11 AM; Dec 3 at 10 AM.
- Full caption **1,367 characters**; compact **1,244**, both within 3,000.
- Below-target advisory only: five events is an accepted short pilot, not a generation failure.
- No silent event cap or length-driven omission; impossible lengths create retained drafts and an explicit editorial exception.
- Captions stable across repeated execution; only explicit generation metadata changed. Exact intake reruns preserve approvals. Substantive record changes or approval-source changes invalidate approval.
- Current source hashes/commit and approval/publication statuses appear in `editorial-report.json`.

See `acceptance-results.json` and `test-results.txt`. The generated files reside in `weeks/2026/RW49_2026-11-29_to_2026-12-05/`.

## Implementation files

- `scripts/pipeline.py`: compatible owner attestation and optional pricing eligibility/display support.
- `scripts/record_attestation.py`: explicit local owner-decision recording, never invoked by generation/automation.
- `scripts/editorial.py` and existing `generate_post.py`: all-event target-week captions, compact fallback, reports/checklist/Jarvis packet.
- `scripts/prepare_wednesday.py`, `validate_post.py`, `pilot_acceptance.py`: read-only approval preparation, output validation and isolated acceptance.
- Branding/rules/schedule/template/editor instructions: shared deterministic voice, optional pricing, advisory counts and inactive Wednesday schedule.
- `weekly-publishing.yml`: manual preparation, current-approval checks, caption validation and review-artifact upload; no intake ingestion or publication.
- Regression tests and updated manual workflow documentation.

## Jarvis and activation recommendation

Use `jarvis-handoff.md` for the intended Wednesday 8 AM briefing. Download/attach the artifact and editorial report, or paste the exact draft to the existing Jarvis briefing. Repository/artifact access is not assumed; no duplicate briefing task or automatic message delivery was created.

Keep recurring preparation disabled until the owner approves activation and the intended Jarvis delivery path is agreed. The target is Wednesday 07:00 America/Chicago with an 08:00 briefing; dual UTC cron planning plus a Chicago/DST guard is implemented but inactive. Hosted execution times may queue. Schedule activation also needs a separately approved default-branch promotion; this review branch is not merged. Branch protections and final-caption approval remain owner integration steps.

Final publication status: **awaiting_final_human_review**. Event approval does not approve the caption. Review formatting, event order, links and Central times, choose a caption, then manually publish only after final approval.
