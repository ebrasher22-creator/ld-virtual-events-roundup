# Proposed Work task amendment — NOT applied

Apply only after owner approval of the launch ref, Wednesday run time and task activation. Edit the existing task; do not create a duplicate. Actual scheduled retrieval/return still needs a supervised scheduled acceptance run.

## Proposed operating instructions

Prepare Next Week in L&D's LinkedIn editorial package for the owner. Use GitHub repository ebrasher22-creator/ld-virtual-events-roundup at the owner-designated launch ref. **Do not run until that exact ref is supplied and contains current approved editorial input.** The rehearsal ref is review/wednesday-operational-handoff-2026-11-18; it is not an approved production branch.

Retrieve agents/linkedin-editor-work.md, docs/editorial-handoff-operations.md, and weeks/editorial-current.json. Follow its editorial_input_path to the Python-produced approved input, checking that its as_of and dates match the intended immediately upcoming Sunday–Saturday week in America/Chicago. The existing pointer may be supplied through the downloaded Wednesday Actions artifact if repository delivery is unavailable. If pointer/input is stale or retrieval is incomplete, report the missing input and stop. Do not guess the week number, reuse a cached week, discover new events, change event eligibility, edit data or grant approvals. Check export_status, roundup_identifier, event count and checksum. Follow the agent instructions for full and compact captions and immutable fact blocks.

Return a downloadable work-submission.json using the existing five-field format. Include the target week and input checksum in the response and state 'UNVALIDATED — owner-mediated repository validation required.' Do not claim that local model checks are the official validator.

The tested GitHub Work write route returns 403. Do not attempt to push, dispatch Actions or request broader access. Tell the owner to download the file and run:

python3 scripts/editorial_handoff.py --submission '/absolute/path/work-submission.json' --as-of YYYY-MM-DD

Use the explicit Python preparation date supplied for that week. On official failure revise only the draft and return a new submission. On official PASS the owner transfers the generated jarvis-message.txt or ZIP to the existing Jarvis conversation. Do not claim the scheduled task can automatically notify Jarvis; no unattended route is verified. Do not create or alter tasks, merge, publish, change canonical facts/approvals or call paid AI APIs. A mechanical pass still requires editorial review and explicit final human publication approval.

## Owner decisions before applying

- Choose the launch ref containing approved preparation and validation infrastructure.
- Resolve the observed 07:00 versus 08:00 America/Chicago discrepancy; use one agreed time with daylight-saving behavior.
- Verify delivery of the existing weeks/editorial-current.json pointer and its referenced input to the selected Work surface. Actions currently uploads this snapshot as an artifact; automated repository refresh is not established by this branch.
- Accept the manual return/validation/transfer boundary or commission and test a supported unattended route.
