# Wednesday editorial handoff: supervised operational runbook

Scope: editorial operations only, isolated from Antigravity on `review/wednesday-operational-handoff-2026-11-18`, based on d019b05. No consolidation, canonical data, approvals, existing agent instructions or workflow definitions changed. No production activation authorized.

## Verified capabilities and limits

On November 18, 2026 a one-off Work rehearsal read `agents/linkedin-editor-work.md` and the approved RW49 `editorial-input.json` at exact commit d019b05. Five approved events and checksum `faad3f55b17ec14eb538c42157860e370b73d6b348ac75563f66eb3a1bdd1e5f` were confirmed. Work returned the existing supervised captions as a downloadable `work-submission.json`; the downloaded file matched the prior pilot submission byte for byte. This rehearsal tests retrieval, return and transport, not fresh creative quality or scheduled execution.

An authorized harmless create-file probe on this isolated branch failed with HTTP 403, `Resource not accessible by integration`. Independent GitHub contents lookup returned 404. Read access is demonstrated; unattended writes and Actions dispatch from Work are not. No scope/credential changes were made. Do not build an automatic GitHub return route on that integration.

The existing Work task was inspected without editing. Its actual task editor says **8:00 AM CT**, despite an earlier chat confirmation saying 7 AM. Saved instructions do not pin the editorial review branch/ref. GitHub's default remains `feature/github-event-pipeline`, which does not contain the current approved package. Before production, owner approval is required to settle the intended time and correct the input reference. No scheduled execution was triggered or verified. Do not duplicate or activate another task.

The observed Work account uses the existing Pro plan. This implementation uses Python standard library and existing GitHub Actions; no model API, API key, paid service or new subscription is introduced. Existing product quotas and billing rules still apply.

## Simplest reliable route

1. Python preparation writes the existing `weeks/editorial-current.json` manifest and produces approved-only `weeks/YYYY/RWnn_START_to_END/editorial-input.json`. The current manual Wednesday Actions workflow already produces this artifact and the deterministic fallback caption. Production recurrence remains inactive. The hosted artifact contains a fresh manifest, but this workflow does not commit it back to GitHub; scheduled Work access to the fresh artifact or an owner-mediated export must be established.
2. Work must receive an explicit repository **ref and path**, or the owner must paste/upload the complete approved input and `agents/linkedin-editor-work.md`. Validate the identifier, export status, count and checksum. If retrieval fails, stop; never reconstruct or discover replacement events.
3. Work follows the existing agent instructions and returns the exact five-field JSON contract in `work-submission.json`. Its output is an unvalidated draft. A scheduled task may be configured later only with owner approval; the supervised read test does not prove scheduled retrieval.
4. Owner downloads the file. From this review checkout run:

   ```sh
   python3 scripts/editorial_handoff.py --submission '/absolute/path/work-submission.json' --as-of 2026-11-24
   ```

   For normal weeks use the intended preparation date rather than the fixed rehearsal date. This invokes the **existing** `validate_work_caption.py` authority automatically, checks current approvals/checksum and packages the output. It never regenerates input or changes event data. Success exits 0; validation failure exits 1 and produces diagnostics without publishable captions. Missing input, malformed source paths and existing packet directories fail closed. Repeat with a new packet directory after revisions; do not overwrite earlier evidence.
5. On PASS, open the printed `review-packets/.../review-packet.zip`. It contains the exact submission, full caption, compact alternative, official validation report, protected file hashes, publication status, checklist and self-contained `jarvis-message.txt`. Packet status is a snapshot at creation (`prepared_not_sent`), not a live delivery tracker. Record any actual receipt separately.
6. Paste `jarvis-message.txt` into the existing Jarvis conversation, or give the ZIP directly to the owner. No repository access is needed. Require receipt confirming week/count and pending approval. Do not call delivery publication approval. Browser attachment automation was unavailable because the extension lacked file-URL permission; plain-text transfer succeeded without expanding permissions.
7. Owner reviews semantics, tone and the final caption, records approve/hold/reject, and publishes manually only after explicit approval. Mechanical PASS cannot assess all prose claims or confer publication approval.

## Existing Actions alternative

An owner can place the returned JSON under `editorial-drafts/` on a review branch and manually run the existing workflow:

```sh
gh workflow run weekly-publishing.yml --ref review/wednesday-operational-handoff-2026-11-18 -f as_of=2026-11-24 -f draft_path=editorial-drafts/RW49_2026-11-29_to_2026-12-05/work-submission.json
```

It invokes the existing caption validator, uploads `work-editorial-validation` and `wednesday-linkedin-review`, and retains human approval. The new local return command additionally creates a single portable review ZIP. It is not an unattended file watcher, server or workflow. Future integration into a production workflow is a separate owner-approved change.

## Supervised RW49 result

Downloaded Work return passed official validation: five events in exact order, exact fact blocks, original URLs, dates, zones, organizers and checksum; full 1,807 characters, compact 1,386, both below 3,000. The six new handoff tests plus forty existing tests passed; the isolated smoke test, repository validator and existing editorial draft scan passed. Negative tests intentionally emit FAIL diagnostics while asserting rejection.

The full self-contained packet was pasted into the owner's existing Jarvis conversation. Jarvis acknowledged receipt for Nov 29–Dec 5, five approved events, mechanical pass and pending editorial/publication approval; it explicitly distinguished this supervised transfer from automatic delivery. No Jarvis repository access was claimed or needed. Receipt is preserved separately in the operational evidence report.

## Readiness decision

**Ready for supervised owner-mediated editorial operations; not ready for an unattended production loop.** Automatic after local receipt: official validation, rejection diagnostics, immutable packet assembly. Manual: Work file download, command invocation or review-branch upload/Actions dispatch, Jarvis transfer, semantic review and publication. Blockers: Work write denied; scheduled retrieval/submission/delivery untested; task ref and time need owner-approved correction; launch branch integration and recurrence still require approval. Preserve the existing deterministic Python fallback.

Product references: [GitHub in ChatGPT](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt), [Tasks in ChatGPT](https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt). Actual surface tests above take precedence over inferred capabilities.
