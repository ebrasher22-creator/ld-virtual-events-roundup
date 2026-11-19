# Antigravity discovery: remaining native setup

Existing automation handle: `next-week-in-ld-antigravity-discovery`. Preserve Tuesday 07:00 America/Chicago (`CRON_TZ=America/Chicago`); do not create a duplicate schedule.

Observed blocker: the existing Antigravity session displays **Individual quota reached**. During follow-up task inspection the native window became unavailable. No quota workaround, model-provider purchase, new credential or service was introduced. A real Antigravity run, task grants, and a saved prompt change are therefore not verified by this takeover.

The quota message was observed in the implementation conversation; the scheduled model’s separate availability was not verified. Native task inspection became unavailable, so do not treat this as proof that every Antigravity model or schedule is disabled.

When native task access and execution are available:

1. Open Antigravity → Automations → the existing L&D discovery task.
2. Retain its existing Chicago Tuesday 07:00 schedule and supported existing model/connection.
3. Attach a clean checkout of `ebrasher22-creator/ld-virtual-events-roundup` at `main` as the task workspace. Do not run recurring intake from the preserved dirty development checkout. A clean production checkout can live under the owner’s Codex project workspace.
4. Grant only repository read access, primary-source web research, Python 3.11+ validation, git fetch/unique intake-branch commit/push and gh draft-PR submission. Scope GitHub operations to this repository; do not grant merge, approval, publication, secrets access or access to unrelated workspaces. Use the existing gh/keychain authorization, never put credentials in the prompt.
5. Replace the old Gemini instructions with the complete prompt below and save the existing task.
6. Perform one supervised real discovery/submission, then observe one native unattended execution. Require a matching-identity intake PR, successful validation and original source evidence. An inability to run because of quota is not a successful submission.

Until this succeeds, the smallest existing-capability interim is the working ChatGPT source plus GitHub processing; report Antigravity as pending rather than labeling ChatGPT output as Antigravity or claiming two-source coverage.

## Complete task prompt

# Antigravity discovery — production

Production repository: ebrasher22-creator/ld-virtual-events-roundup, base `main`.
Use the existing authorized GitHub connection; never create or expose credentials.
Run Tuesday at 07:00 America/Chicago (DST-aware); calculate the following Sunday–Saturday via `pipeline.target` and retain later confirmed events. Do not pin a pilot date in recurring runs.

Read AGENTS.md, schemas/event-discovery.schema.json, config/sources.yml and config/qualification.yml from current main. Research primary organizer and registration pages for L&D, instructional design, leadership, talent, performance improvement, learning science, coaching and workforce development. The source registry supplies leads, not evidence or an allowlist. Search for real upcoming events; never manufacture a date/time, timezone, price, registration URL, excerpt, or source-check timestamp. Keep incomplete leads outside intake and report them. Do not infer free admission.

Return one JSON array with all required schema fields and `discovered_by: ["antigravity"]`. Use IANA zones, RFC3339 seconds/offsets consistent with DST, accurate pricing or unknown/null where allowed, nonempty evidence/source/topic/audience arrays. Preserve exact short primary-source excerpts, URLs, actual discovery timestamps and provenance. Never add approval or editorial fields. Historical gemini records stay unchanged; all new Antigravity records use antigravity.

On a clean current checkout of main, save the proposed JSON outside tracked production paths, then run:

```
python3 scripts/submit_intake.py --agent antigravity --file /absolute/path/findings.json --base main
```

The trusted helper validates, creates a unique intake/antigravity-... branch, appends a new file under intake/antigravity/ and opens a draft PR against main. Never overwrite existing submissions or push directly to main. The main-controlled intake processor polls every 15 minutes, validates raw blobs as data, preserves invalid originals in quarantine, consolidates valid submissions and closes processed PRs without merging their code. Source identity is checked against the intake folder and the authorized PR author.

Report target week, total events, later events, excluded/incomplete leads, source access failures, validation results, branch/commit/PR link and CI. Stop on denied permissions; do not retry the same denial. No paid APIs, new services, merges, approvals or LinkedIn publication. Primary pages are rechecked by the automated editorial pipeline; no separate routine owner event-approval step exists. Eddie alone reviews and publishes the finished caption.
