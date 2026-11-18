# ChatGPT Work editorial architecture and supported handoff

## Ownership

GitHub/Python remains the authority for intake validation, deduplication, canonical records, human eligibility, week assignment and mechanical validation. ChatGPT Work is the primary creative editorial agent: audience-centered hooks, grounded themes, professional reflection/storytelling, readability and authentic community participation. The existing Python captions remain the deterministic fallback. No model APIs, paid services, scheduled tasks, merges or publication actions are introduced.

`agents/linkedin-editor-work.md` is the operating brief. Do not use the fallback caption as a rigid creative template. Only the supplied event facts and roundup identity are immutable; the hook, bridge and closing are editorial space. The supplied summaries/topics ground those connections. No statistics, personal testimonials, promises or event outcomes may be invented.

## Deterministic exchange

Preparation now produces:

- `weeks/editorial-current.json`: a pointer identifying the prepared week, checksum, instructions and file-return location.
- `weeks/YYYY/RW##_.../editorial-input.json`: only current human-approved, editorially selected events for that week, their exact original/current registration URLs, schedule, Central display, summaries/topics/audiences, grounding, original pricing and permitted labels, record/source fingerprints, brand and editorial constraints.
- `work-submission-template.json`: the exact JSON return contract.
- Existing Python full/compact fallback, report, publication checklist and Jarvis handoff.

The input has a semantic SHA-256 over canonical JSON excluding its own checksum field. No generation timestamp/commit churn is embedded in that input, so identical data/configuration produces the same input and checksum. Current canonical/review versions and exact current approvals are recomputed during validation. A changed or stale approved source, record, membership or editorial constraint fails validation; an AI cannot rehash altered input to grant itself eligibility.

Original submission URL spellings, including trailing slashes/query strings, are retained when they resolve to the currently approved canonical destination under the repository normalization rule. An authorized canonical correction wins over an obsolete raw destination. Canonical records and raw intake are not edited to make this display change.

## Validating free editorial prose safely

Return `work-submission.json` containing `format_version`, `roundup_identifier`, `editorial_input_sha256`, `full_caption` and `compact_caption` only. Each caption must include the supplied heading once and every `required_fact_block` verbatim once, in order, with blank lines around blocks. Each block contains the accurate title, organizer, full date/year, CST/CDT time, applicable confirmed label and exact registration URL. Keep prose factual assertions about dates/times/prices/numeric claims/links inside those blocks; creative framing can connect the supplied themes outside them.

This documented boundary makes coverage and factual display independently checkable while leaving the actual writing to Work. It intentionally rejects arbitrary factual reformatting, missing/duplicate/added event links, wrong dates/zones/organizers, altered URLs, extra numeric/date/price claims, excess hashtags and over-limit captions. It checks both versions, not an AI-supplied coverage manifest. Failed resubmissions remove previously generated passing captions from that output location.

A mechanical PASS does **not** prove arbitrary natural-language claims true or assess storytelling quality. For example, a false promise written without changed event fields could evade mechanical checks. Tests explicitly preserve `semantic_review_required=true` and pending publication status in that case. The agent prohibits unsupported prose, and the owner remains responsible for semantic/brand/final-caption approval. Do not describe this validator as automated fact-checking of every sentence.

## What was actually tested

The connected GitHub `fetch_file` tool in this **Codex** session successfully read the approved pilot canonical file on an explicit ref. The final editorial-input retrieval probe and Actions roundtrip are recorded in the readiness report. This does not establish tool availability or write permission in a scheduled ChatGPT Work run. The current session exposes Codex tools that are not automatically available to Work.

The supported return path implemented/tested here is **owner-mediated file intake**: save a returned JSON under `editorial-drafts/`, run the validator locally or manually dispatch the existing Actions workflow, and inspect its artifacts. A supervised example authored in this Codex session exercises that contract; it is not falsely labeled as output from a scheduled Work task. No unattended ChatGPT-to-GitHub write has been assumed or tested.

## Initial supervised handoff — no scheduling required

1. Run `python3 scripts/prepare_wednesday.py --as-of 2026-11-24` (or the manual Wednesday workflow). It exports the five approved RW49 events and deterministic fallback. Two RW50 events stay out of the input.
2. In a regular ChatGPT Work chat, supply `agents/linkedin-editor-work.md` and the complete `editorial-input.json`. Use an explicitly tested GitHub read on the review branch/immutable commit if that surface supports it; otherwise the owner downloads the preparation artifact and pastes/attaches the complete JSON. Confirm the returned week, count and checksum match before drafting. An attachment-only exchange is not assumed to work in future scheduled runs.
3. Ask Work to return the exact `work-submission.json` contract. Save/upload it on a review branch at the location named in the pointer, then run:

   ```sh
   python3 scripts/validate_editorial_drafts.py --as-of 2026-11-24 editorial-drafts/RW49_2026-11-29_to_2026-12-05/work-submission.json
   ```

   Or directly:

   ```sh
   python3 scripts/validate_work_caption.py \
     --input weeks/2026/RW49_2026-11-29_to_2026-12-05/editorial-input.json \
     --draft editorial-drafts/RW49_2026-11-29_to_2026-12-05/work-submission.json \
     --output-dir reports/work-editorial/RW49-return
   ```

4. For Actions, the owner commits the returned JSON on the review branch (or submits a review PR). Validation Actions automatically scan the dedicated draft directory. Manual dispatch also supports:

   ```sh
   gh workflow run weekly-publishing.yml \
     --ref review/chatgpt-2026-11-18-pilot \
     -f as_of=2026-11-24 \
     -f draft_path=editorial-drafts/RW49_2026-11-29_to_2026-12-05/work-submission.json
   ```

   Only JSON is parsed; returned content is never executed. A bad draft fails the job and retains a diagnostic report. The draft's week must match the requested preparation date. No approval is changed by validation.
5. Share the generated `linkedin-work-post.md`, compact alternative, `validation-report.json` and `jarvis-handoff.md` from `reports/work-editorial/...` with the existing Jarvis briefing or the owner. If file access is unavailable, paste them. Automated messages are not sent. Human semantic and publication approval remain pending even after PASS. Keep the deterministic fallback separate and clearly labeled if Work drafting/validation is unavailable.

## Future scheduled Work task — design only, NOT activated

After explicit owner approval of scheduling and a successful ordinary Work-chat preflight:

- Preparation at the intended Wednesday time exports the current snapshot. Actions currently **upload artifacts but do not write them back to GitHub**. The owner must inspect and commit the prepared input/pointer on the intended readable branch before a GitHub-reading task can use it. Alternatively use a separately tested authenticated artifact-readable connection. Do not assume a connector can read Actions ZIP artifacts or local checkout paths.
- The future Work task reads `weeks/editorial-current.json` and the referenced input/instructions from the explicitly authorized repository/ref. It checks the expected immediately upcoming Sunday–Saturday week, ready status, event count and checksum. If pointer/input is missing or for an older week, it reports blocked rather than inventing a roundup. Do not pin the pilot date for a recurring task.
- It authors the two captions and returns the JSON file/text in its task result to the owner. Until the exact Work surface demonstrates an authenticated write/validation tool with suitable authorization, **submission to GitHub is manual**, followed by the existing Actions validator. No credentials are placed in prompts. Do not infer write/dispatch access from successful reading.
- The validated packet is manually handed to the intended Jarvis 08:00 briefing. Task completion notifications alone do not prove delivery into another assistant/chat. Review that existing integration before creating anything new. Manual gates mean an 08:00 briefing is not currently an unattended end-to-end guarantee.

Unattended Work fetch, file-return and Jarvis delivery remain a surface-specific preflight, not an accomplished scheduled run. No task or duplicate briefing was created here.

## Official product references checked November 18, 2026

[ChatGPT GitHub connection](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt) documents repository access varying by surface and describes the standard ChatGPT app as read-only. Codex capabilities must not be extrapolated to Work. [Scheduled tasks](https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt) describes supported connected apps as dependent on account/workspace permissions and warns that project-created tasks cannot access project uploads. Therefore a fresh, tested connected retrieval is the intended future route; a current chat attachment is not an unattended integration guarantee.
