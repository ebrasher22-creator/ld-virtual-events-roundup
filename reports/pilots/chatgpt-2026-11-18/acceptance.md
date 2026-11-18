# ChatGPT discovery pilot acceptance

**Assessment: ACCEPTED FOR PENDING INTAKE; NOT APPROVED FOR PUBLICATION.**

Review branch: `review/chatgpt-2026-11-18-pilot`. Baseline: `97f0c23`. Input: `intake/chatgpt/chatgpt-2026-11-18-pilot.json`, copied byte-for-byte from the supplied file. No records were repaired, inferred, removed or marked verified. No production canonical/review data was changed.

## Validation

- Official command: `python3 scripts/validate.py intake/chatgpt/chatgpt-2026-11-18-pilot.json` — exit 0, no errors or output (the official validator is silent on success).
- All seven records pass the repository's additional URL/date/timezone checks.
- Independent JSON Schema Draft 2020-12 validation using jsonschema 4.25.1 with date-time and URI format checks — 7/7 pass, zero errors. This audit dependency was installed only in ignored `work/schema-venv`; production dependencies are unchanged.
- Existing regression suite — 14 passed, zero failures. Existing synthetic smoke acceptance test — passed.
- Detailed per-record results and input/schema SHA-256 hashes: `validation-report.json`.

## Isolated ingestion results

`as_of=2026-11-24` targets `2026/RW49_2026-11-29_to_2026-12-05`.

| Check | Result |
| --- | --- |
| Submissions | 7 |
| Canonical preview events | 7 distinct; zero pilot duplicates or conflicts |
| RW49 events | 5 |
| Future events retained | 2, both RW50 (December 6–12) |
| Independent verification | 7 pending; all last_verified_at null |
| Editorial status | 7 pending; none selected |
| Publication-ready selections | 0 |
| Raw provenance | All 7 preserve original record, source URLs, chatgpt attribution, intake path and matching submission fingerprint |
| Full pipeline rerun | Canonical, future and generated week files byte-identical |
| Exact duplicate file test | No additional events or submissions |
| Simulated Gemini duplicate | Still 7 events; one event preserves both agents, both raw submissions and the source-URL union; tracking parameter ignored |
| Simulated changed-time submission | Still 7 events; start/end conflicts flagged; pending status preserved |
| Protected production data | Before/after hashes identical |

The simulated Gemini/time-change inputs existed only inside a temporary test root. They are not pilot observations and were not committed to intake or previews. `preview-NOT-CANONICAL/` contains only the seven-record baseline and its two future events; it is an audit artifact, not the source-of-truth data store. Its RW49 Markdown contains no event listings, as required by the unverified-record gate. Detailed results are in `ingestion-report.json`; actual CLI outputs are in `command-results.json` and unchanged data hashes are in `protected-data-hashes.json`.

## Assigned dates (CST, as submitted; not independently verified)

| Title | Central start | Assigned week |
| --- | --- | --- |
| 2027 Planning Sprint | Dec 1, 12:00 PM | RW49 |
| L&D as a Conductor | Dec 2, 9:00 AM | RW49 |
| Renovate Your Instructional Design Process | Dec 2, 10:00 AM | RW49 |
| Trauma-Informed Leadership | Dec 2, 11:00 AM | RW49 |
| The 2027 Learning Experience | Dec 3, 10:00 AM | RW49 |
| AI in the Flow of Work | Dec 8, 10:00 AM | RW50; future retained |
| Intro to Facilitating Groups | Dec 10, 12:00 PM | RW50; future retained |

## Issues and recommended changes before scheduled discovery

**No schema incompatibility blocks accepting this file.** Optional `organizer_url`, `cost` and some `end_datetime` fields are absent and legitimately remain unknown; do not fabricate them. Free-form topics and language `English` are accepted.

1. **Independent verification blocks publication for all seven.** The evidence is discovery-supplied narrative, not a completed independent check. Verify organizer, live virtual access, date/year/time, current status, price and actual registration destination; add per-claim primary-page observations in the separate human review ledger only after canonical acceptance/assignment. No source pages were fetched or verified during this import.
2. **Use a session-specific registration URL when established.** “Intro to Facilitating Groups” currently uses the generic Leadership Strategies webinar listing as registration_url. A listing may contain a registration control, but that destination was not checked here. Reusing this generic URL for another session will cause the current matcher to consolidate and quarantine differing titles/times as conflicts. Confirm the actual session registration destination before later batches; preserve the original raw submission and make corrections through a reviewed new submission/canonical resolution.
3. **Strengthen evidence details.** The Training Industry excerpts for the December 3 and December 8 sessions do not explicitly state “free”, despite price_type=free. The iSpring excerpt does not explicitly state the year, although start_datetime specifies 2026. These are evidence gaps, not proven factual errors. Independently confirm them and substantiate the summary/speaker claims before editorial selection.
4. **Roundup depth remains below target.** Five candidate events fall in RW49, below the configured 8–12 target, even if all later qualify. Seek at least three additional strong events or explicitly approve a shorter roundup. The two future events must not be moved into RW49 to fill the gap.
5. **Schedule and intake integration remain manual.** Use `as_of=2026-11-24`, not the actual November 18 import date. Neither this import nor existing workflows configures an external ChatGPT/Gemini scheduled task. Existing branch-protection and human-review setup limitations from readiness still apply.

The branch is ready for human intake review. Acceptance of these raw discoveries does not authorize canonical promotion, conflict resolution, final editorial approval, merging or LinkedIn publication.

## Reproduce without touching production data

```sh
python3 scripts/validate.py intake/chatgpt/chatgpt-2026-11-18-pilot.json
python3 -m unittest discover -s tests -v
python3 scripts/smoke.py
python3 - <<'PY'
from pathlib import Path
import shutil
root=Path('work/live-pilot-replay')
root.mkdir(parents=True,exist_ok=False)
for directory in ['config','data','intake']:
    shutil.copytree(directory,root/directory)
PY
python3 scripts/ingest.py --root work/live-pilot-replay
python3 scripts/assign_weeks.py --root work/live-pilot-replay --as-of 2026-11-24
python3 scripts/generate_post.py --root work/live-pilot-replay --as-of 2026-11-24
```

Run the replay initializer only with a fresh directory. Inspect results under `work/live-pilot-replay`; do not copy previews into `data/` without authorization.
