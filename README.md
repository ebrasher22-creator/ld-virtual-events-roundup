# Next Week in L&D

A GitHub-based event discovery intake, canonical record and LinkedIn preparation system. Python 3.11+ standard library; no paid AI APIs or automatic LinkedIn publication.

The current implementation is on `review/chatgpt-2026-11-18-pilot`. The temporary remote default remains `feature/github-event-pipeline`; no merge/default promotion has been authorized. See [branch strategy](docs/branch-strategy.md).

## Primary Work editorial agent and deterministic fallback

ChatGPT Work owns creative framing, grounded themes, professional storytelling and community engagement. Python owns eligibility and facts, exports `editorial-input.json`, and mechanically validates the returned captions. Python full/compact captions remain the fallback. See [Work handoff and validation](docs/work-editorial-handoff.md) and [agent instructions](agents/linkedin-editor-work.md). No Work task is scheduled; returned JSON enters through an owner-mediated file upload, never an assumed unattended GitHub write.

## Wednesday pilot

```sh
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
python3 scripts/smoke.py
python3 scripts/pilot_acceptance.py
python3 scripts/prepare_wednesday.py --as-of 2026-11-24
python3 scripts/validate_post.py --as-of 2026-11-24
```

The owner has explicitly approved seven pilot events through a preserved, hash-bound human attestation. Five are RW49 (November 29–December 5); two remain RW50. Actual source-check times and per-claim observations were not supplied and have not been invented. Event approval does not authorize a final caption or publication.

Open `weeks/2026/RW49_2026-11-29_to_2026-12-05/linkedin-post.md` or the compact alternative. The folder also contains an editorial report, final publication checklist and Jarvis handoff. The configured 8–12 event target is advisory; the generator includes every eligible event for that week, never borrows from another week, and flags an explicit exception if essential details cannot fit the configured 3,000 characters.

[Wednesday preparation, attestation contract, inactive schedule and Jarvis handoff](docs/wednesday-preparation.md) describes local/manual Actions execution and the later activation steps. Use the existing `weekly-publishing.yml` with the review branch and `as_of=2026-11-24`. Recurring preparation is not enabled. Publication remains manual.

## Manual discovery intake

Give external ChatGPT/Gemini sessions the prompts in `agents/`, the schema and source registry. Save returned JSON arrays to new `intake/chatgpt/` or `intake/gemini/` files on a review branch. Do not replace historical submissions. Never assume scheduled assistants have authenticated GitHub write access. The 76 classified source leads are not proof of current events or a source allowlist; 74 supplied names intentionally have no guessed URL.

```sh
python3 scripts/validate.py
python3 scripts/ingest.py
python3 scripts/assign_weeks.py --as-of 2026-11-24
```

Syntactic validation does not prove facts, URL availability or registration functionality. Uncertain events stay pending. Raw submissions, SHA-256 fingerprints, source URLs, agent attribution and intake paths remain auditable. Matching uses normalized registration URL, then normalized title + organizer + instant. Reused URLs with changed times flag conflicts; completely changed identities may need human duplicate review. New submissions invalidate approvals; exact reruns do not multiply events. Canonical records and review decisions persist through Git. `future-events.json` is a derived projection after the target Saturday.

Review primary evidence and resolve conflicts before recording a human approval. The original detailed claim-observation ledger remains supported; explicit owner statements can instead be recorded through the documented human-attestation route. Both bind exact canonical fingerprints and keep editorial selection separate from final publication. Never fabricate observations or use an agent's verification assertion as approval. Original pricing is preserved; unknown or unconfirmed price is optional and omitted from captions. Confirmed labels are Free/Paid; no missing-price inference is made.

## Calendar and output policy

Sunday–Saturday boundaries use America/Chicago. Labels use the ISO year/week of the Monday in that period. `as_of` is a discovery/preparation date; Tuesday November 24 or Wednesday November 25 targets RW49. Sunday itself targets the following Sunday. IANA timezone conversion handles CST/CDT. JSON-compatible YAML configuration avoids extra parser dependencies.

Caption content is deterministic; generation time and source-version metadata are explicitly reported. Source approval or canonical changes invalidate stale output. All generated artifacts require final human review. Never publish an over-limit or exception draft.

## Safety and integration

Validation Actions use read-only permissions. Wednesday preparation on the pilot branch is manual-only, reads persisted approvals and uploads review artifacts; it does not ingest discoveries, create approvals, commit canonical data, merge, deploy or publish. No recurring Jarvis task was created. Owner-configured branch protections/required reviews remain necessary for enforced multi-contributor controls. Approval-source hashes are integrity checks, not a substitute for trusted write permissions. Existing action major tags can be hardened to immutable SHAs in a later authorized change.

Future authenticated intake should use a repository-limited GitHub App, short-lived credentials stored outside prompts, payload validation, signatures/replay protection and rate limits, submitting intake PRs rather than editing human approvals. Manual intake stays supported.

## Historical evidence

[Original synthetic manual intake](docs/manual-intake.md), [readiness report](docs/readiness-report.md), and `reports/pilots/chatgpt-2026-11-18/` preserve earlier pending-stage evidence. Those snapshots are historical; current approval state is in `data/reviews.json` and `approvals/`. Synthetic fixture reviews remain test-only.
