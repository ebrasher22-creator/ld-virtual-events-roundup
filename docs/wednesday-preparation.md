# Wednesday LinkedIn preparation and Jarvis handoff

## Current pilot

The repository owner explicitly approved all seven events in the attached implementation request. The exact request is preserved in `approvals/2026-11-18-owner-wednesday-authorization.md`. Each event's review binds the source-file SHA-256, the verbatim approval statement and the final canonical record SHA-256. No per-event observations or historic verification time were invented: `claims` is empty and `verified_at` / `last_verified_at` are null. `attestation.recorded_at` is when the decision was recorded, not when source pages were checked. All seven are fact-approved and editorially selected for their own assigned weeks, but the final caption is not publication-approved.

The session-specific Intro to Facilitating Groups registration URL was applied through a documented canonical resolution, using the user-provided URL and prior organizer-link evidence. Its stable event ID, original raw submission and old URL alias were preserved. Existing pilot reports and checklists remain historical snapshots; the current canonical/review files supersede their pending status.

## Run the pilot manually

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 scripts/smoke.py
python3 scripts/pilot_acceptance.py
python3 scripts/prepare_wednesday.py --as-of 2026-11-24
python3 scripts/validate_post.py --as-of 2026-11-24
```

This prepares RW49, November 29–December 5, with exactly five approved events. Two RW50 events stay available in canonical/future storage. `prepare_wednesday.py` reads persisted approvals, assigns weeks, generates and validates drafts; it never ingests new discoveries or grants approvals. A stale selected record causes an editorial exception and failed preparation, with reports retained. The 8–12 target is advisory; it never borrows from another week, silently truncates at 12, or blocks a short roundup.

Manual Actions:

```sh
gh workflow run weekly-publishing.yml --ref review/chatgpt-2026-11-18-pilot -f as_of=2026-11-24
```

The existing registered workflow file is reused so it can be dispatched on this review branch without merging a new workflow into the default branch. Its pilot implementation is manual-only and read-only. Select the review branch, not the temporary default branch's older implementation. Download the `wednesday-linkedin-review` artifact. Failed editorial preparation still attempts to upload review files; inspect the report before using any draft.

## Artifacts

`weeks/2026/RW49_2026-11-29_to_2026-12-05/` contains:

- `linkedin-post.md`: full copy-and-paste caption.
- `linkedin-post-compact.md`: shorter caption with all essential details.
- `editorial-report.json`: target, timestamp, approved/included/excluded events, reasons, optional price gaps, counts, source commit and exact data hashes, publication status and exceptions.
- `publication-checklist.md`: final human review and decision.
- `jarvis-handoff.md`: briefing summary and the draft, suitable for manual transfer.

Legacy filenames remain as aliases. The captions are deterministic. Only declared report generation metadata changes between otherwise identical executions; changes to the repository commit are reflected in source metadata. All event titles, organizers, Central times and original-length canonical registration URLs are preserved. The generator uses the repository template and branding. It shortens optional prose/hashtags before declaring an explicit over-limit exception; it never silently drops an approved event. It counts Unicode code points including newlines; final human preview in LinkedIn remains necessary, especially if future captions use unusual Unicode/emoji.

## Human review contract and optional prices

The detailed-claims review format still works. Six nonprice claims are mandatory for that format; price is optional. A second compatible route is `attestation.type=explicit_owner_approval`, `authority=repository_owner`, reviewer identity, the source path under approvals/, source hash, verbatim statement, recorded_at, and the six nonprice covered_claims. Both routes require `decision=verified`, separate `editorial_decision=selected`, matching `record_sha256`, no conflicts and valid live virtual/hybrid event data.

`record_attestation.py` is a reviewed local mutation tool, not an unattended approval service. Use it only with explicit owner authorization and explicit event IDs. Never author a supposed human statement on the owner's behalf. Any substantive event change invalidates the exact hash; provenance/metadata changes also invalidate it conservatively. A changed attestation source invalidates all approvals bound to it. Intake-supplied approvals cannot qualify an event. Protect approval sources and review/canonical writes through repository rulesets and human review; hash integrity alone is not authentication against someone who can edit all trusted files.

Pricing: retain original price_type/cost. `unknown` is eligible without price evidence. Known but not separately confirmed pricing is also omitted from the caption. Display Free/Paid only with a nonempty price observation + primary URL, or an explicit separate pricing attestation. General owner approval does not invent a price check. This pilot keeps all seven original `price_type=free` values but omits labels because individual pricing confirmation was not recorded. The report exposes that gap without disqualifying the events. No paid amount is inferred and no event research is repeated.

## Wednesday activation plan — INACTIVE

Desired preparation: Wednesday 07:00 America/Chicago. Desired Jarvis briefing: Wednesday 08:00 America/Chicago.

No active Actions `schedule` exists, and `config/schedule.yml` has `recurring_enabled=false`. Do not activate until the owner approves after the supervised pilot. GitHub hosted jobs can queue; the desired local time is a target, not an exact delivery guarantee.

On explicit activation approval:

1. Approve the branch/promotion strategy separately; scheduled workflows execute the default branch, which must first contain the approved code and data. Nothing in this implementation merges or changes the default.
2. Remove the fixed pilot as_of default so real Wednesdays target their immediately upcoming Sunday. Keep the manual override available.
3. Enable recurring configuration and add these two UTC cron entries to the workflow:

   ```yaml
   schedule:
     - cron: '0 12 * * 3'
     - cron: '0 13 * * 3'
   ```

   The existing Chicago gate permits only the 07:00 local occurrence, handling CST/CDT and skipping the other trigger without creating duplicate artifacts. The standalone `--scheduled` flag also checks activation/time; it refuses an inactive schedule.
4. Confirm review protections, output delivery, current approvals and failure handling. No LinkedIn publication step is added.

## Jarvis 08:00 handoff

There is no assumed Jarvis account, API, repository access or artifact connection. No briefing task or automation was created. Supported path now: owner downloads the Actions artifact (or copies files from this checkout), then attaches `jarvis-handoff.md`, the chosen draft and `editorial-report.json` to the intended Jarvis briefing/chat. If Jarvis cannot access attachments, paste the handoff and exact caption. Share the run/artifact URL as context; access still depends on Jarvis/user permissions. Jarvis should state event count, target week, advisory/exception status and that final publication approval is pending.

Before any automated delivery, identify the existing intended Jarvis briefing and review its schedule/access with the owner; do not create a duplicate 08:00 briefing. Secure delivery integration, repository permissions and the final human caption decision remain manual integration steps.
