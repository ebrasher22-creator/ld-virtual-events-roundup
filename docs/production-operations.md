# Production operations

Production branch: main. Historical branches are retained; diagnostic PRs must not merge. Preserve intake/gemini as the immutable legacy Antigravity stream. New source labels and directories are chatgpt and antigravity.

## Automated intake

Process discovery intake runs on main every 15 minutes and on workflow_dispatch. It reads only owner-authored same-repository intake/chatgpt-* or intake/antigravity-* PRs targeting main, permits added matching intake JSON paths only, validates before ingestion, quarantines invalid bytes with SHA-256/error reports, preserves raw bytes/provenance, consolidates duplicates and assigns future weeks. It never checks out or executes PR code. Production rejects reserved/synthetic sources. Successful persistence precedes PR notification/closure; original PR branches are retained. Historical review decisions are not used as qualification gates or rewritten by normal processing.

## Wednesday generation

Wednesday LinkedIn preparation runs at 07:00 America/Chicago using GitHub's IANA timezone schedule and also supports supervised workflow_dispatch. A local-date marker prevents duplicate generation; delayed runs are accepted through 10:59 Central. Both writing workflows share a concurrency group. It checks current primary pages, excludes unresolved/canceled/conflicting/deferred records, selects up to 12 qualified events chronologically, preserves remaining canonical records, shortens descriptions without removing them and respects 3000 characters (2800 working target). Pricing is never inferred. Zero eligible events produces an explicit not-ready report, never fictional filler. Reports, checks, draft and handoff are committed to main; upload artifacts preserve failure diagnostics.

The deterministic post is authoritative. Optional historical Work tooling remains available for supervised editing, but the competing recurring Work task is to be paused only after hosted replacement testing. There is no recurring event approval step. Eddie’s final caption review and manual LinkedIn publication remain mandatory.

## Source checks

Qualification is deliberately conservative: live title, full date/year, exact local time, timezone, organizer and virtual indicator must be found on current organizer/registration pages; missing facts exclude the event. This parser does not bypass CAPTCHA/authentication or prove cancellation from HTTP failure. A 403 remains unresolved. It rejects nonpublic HTTP destinations and redirects. Checks expire after 36 hours, reject future timestamps, bind to exact schema facts and retain page hashes/observed text for audit. No failed request is represented as a successful check.

## Permissions and recovery

Trusted automation needs contents:write; both persistence workflows additionally need pull-requests:write to create/merge their validated data-only PRs, and actions:write to dispatch validation. Intake processing also reports/closes the source submissions. The repository Actions PR-creation setting must allow those PRs; no automated reviews are submitted. Validation PR jobs remain read-only. main rules require a PR and validate checks and block force pushes/deletion. GitHub rejected an Actions bypass, so trusted generated data is persisted through data-only PRs with explicitly dispatched validation; no bypass is used. Restrict workflow edits to reviewed feature branches. Raw intake, quarantined bytes and processing reports support replay/recovery; do not erase history. Owner approvals/reviews are retained as historical records.
