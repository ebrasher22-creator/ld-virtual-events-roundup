# Work editorial architecture readiness

**Ready for a supervised ChatGPT Work editorial handoff; not yet an unattended Work→GitHub→Jarvis integration.** No Work task was scheduled and no merge/publication occurred.

## Implemented

- Python preparation exports a deterministic `editorial-input.json` with only the five current approved/selected RW49 events. Two RW50 records remain outside it. Exact original URL spellings are preserved when consistent with the approved destination; approved corrections override old submission URLs. Summaries/topics are drawn unchanged from the hash-bound canonical records.
- `weeks/editorial-current.json` gives the week, input path/checksum and instructions/return locations. Actions upload snapshots but do not commit them: a connected Work reader needs a deliberately persisted readable snapshot or a separately proven artifact retrieval path.
- `agents/linkedin-editor-work.md` assigns Work the audience hook, grounded themes, professional reflection/storytelling, readability and authentic participation CTA. It requires varied framing with a consistent identity and complete full/compact alternatives. Eligibility and factual event blocks remain immutable.
- New standard-library validation checks both actual captions against current input/approvals, exact required coverage, event ordering, titles, organizers, full date/year, Central time/zone, original registration URLs and character limits. Missing/duplicate/changed blocks, extra event URLs/date/time/price/numeric claims, stale/tampered input and over-limit captions fail. Old passing outputs are removed after failed resubmission.
- Dedicated JSON file intake under `editorial-drafts/` supports local validation, PR validation, and optional returned-draft validation in the existing manual Wednesday workflow. No API keys, model calls or unattended Work writes are used. Input/draft content is data, never shell/code execution.
- The original Python full/compact generator remains a clearly labeled fallback. Canonical records, human approvals, raw intake and recurrence-disabled configuration are unchanged.

## Verification completed locally

**40 regression tests passed, zero failures**, including expected rejection cases. Original synthetic smoke and approved-seven end-to-end acceptance passed. A Codex-authored supervised exchange example validates with five events in both captions; full 1,580 characters, compact 1,312. It is a test of the Work return contract, not a falsely claimed Work scheduled run or publication approval.

Input exports are stable across generation timestamps. Tests prove unknown pricing and pending/future records do not bypass the existing authority; stale approved content cannot be accepted by changing the submitted checksum. A test also demonstrates the limit: arbitrary unsupported prose outside structured event facts is not semantically verified by string checks. Every PASS explicitly retains `semantic_review_required=true` and final publication approval pending.

The connected GitHub `fetch_file` tool in this Codex session successfully retrieved the approved canonical file from explicit ref `ce2a301`. Final input readback and manual Actions evidence will be appended after the implementation push.

## Supported handoff and remaining preflight

See [handoff instructions](../../../../docs/work-editorial-handoff.md) for exact commands. Supported return path: owner obtains Work’s JSON file/text, saves it on the review branch, then runs local/Actions validation and transfers the validated packet to the existing Jarvis briefing or reviews it personally. This repository does not send messages or assume Jarvis access.

Before scheduling, perform one ordinary Work-chat preflight in the actual intended surface: retrieve the explicit ref/input and checksum (or supervised owner attachment), author/export a draft, and return it through the tested file intake. The current Codex connector test does not establish scheduled Work capabilities. No attempt was made to create a task, grant Work write permissions or impersonate a Work run. A human-mediated JSON roundtrip and Actions execution test establish the repository side; actual scheduled retrieval and delivery remain untested.

The standard ChatGPT [GitHub documentation](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt) describes read-only access and surface-dependent availability. [Task documentation](https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt) makes connected-app access permission-dependent and warns about project-upload access in scheduled tasks. Do not assume Codex write tools, local paths, chat attachments or task completion notifications provide an unattended Work validation/Jarvis bridge.

**Recommendation:** keep schedules inactive. The architecture supports a supervised Work editing pilot now. Complete the surface-specific preflight and agree how fresh prepared snapshots and returned drafts cross the manual boundaries before requesting activation. Mechanical validation is not semantic review or publication consent.
