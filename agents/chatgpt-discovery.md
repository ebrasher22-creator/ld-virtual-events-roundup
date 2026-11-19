# ChatGPT discovery — production

Production repository: ebrasher22-creator/ld-virtual-events-roundup, base `main`.
Use the existing authorized GitHub connection; never create or expose credentials.
Run Tuesday at 07:00 America/Chicago (DST-aware); calculate the following Sunday–Saturday via `pipeline.target` and retain later confirmed events. Do not pin a pilot date in recurring runs.

Read AGENTS.md, schemas/event-discovery.schema.json, config/sources.yml and config/qualification.yml from current main. Research primary organizer and registration pages for L&D, instructional design, leadership, talent, performance improvement, learning science, coaching and workforce development. The source registry supplies leads, not evidence or an allowlist. Search for real upcoming events; never manufacture a date/time, timezone, price, registration URL, excerpt, or source-check timestamp. Keep incomplete leads outside intake and report them. Do not infer free admission.

Return one JSON array with all required schema fields and `discovered_by: ["chatgpt"]`. Use IANA zones, RFC3339 seconds/offsets consistent with DST, accurate pricing or unknown/null where allowed, nonempty evidence/source/topic/audience arrays. Preserve exact short primary-source excerpts, URLs, actual discovery timestamps and provenance. Never add approval or editorial fields. Historical gemini records stay unchanged; all new Antigravity records use antigravity.

On a clean current checkout of main, save the proposed JSON outside tracked production paths, then run:

```
python3 scripts/submit_intake.py --agent chatgpt --file /absolute/path/findings.json --base main
```

The trusted helper validates, creates a unique intake/chatgpt-... branch, appends a new file under intake/chatgpt/ and opens a draft PR against main. Never overwrite existing submissions or push directly to main. The main-controlled intake processor polls every 15 minutes, validates raw blobs as data, preserves invalid originals in quarantine, consolidates valid submissions and closes processed PRs without merging their code. Source identity is checked against the intake folder and the authorized PR author.

Report target week, total events, later events, excluded/incomplete leads, source access failures, validation results, branch/commit/PR link and CI. Stop on denied permissions; do not retry the same denial. No paid APIs, new services, merges, approvals or LinkedIn publication. Primary pages are rechecked by the automated editorial pipeline; no separate routine owner event-approval step exists. Eddie alone reviews and publishes the finished caption.
