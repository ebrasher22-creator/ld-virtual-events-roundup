# Supervised discovery consolidation acceptance

**The isolated comparison passes; direct integration with the current ingestor is not ready.** Both seven-record datasets pass the **current** validator. The current **40-test** regression suite, including owner-attestation and Work editorial validation, and the synthetic smoke pass. The experimental review projection preserves 14 submissions as 11 distinct candidates. No original file, approved record, review entry, source approval, editorial input or validated caption was changed.

Sources: ChatGPT `d019b05`; Antigravity `93f8715`. Antigravity was fetched only after the user confirmed its push. Its branch descends from common base `97f0c23` and contains the earlier 14-test discovery baseline. This test ran the current implementation, not that older harness. Original intake JSON and both Antigravity reports are preserved byte-for-byte under `originals/`, with pinned commit/path/SHA-256 manifest. No branch was merged.

## Discovery effectiveness

| Validated-intake metric | ChatGPT | Antigravity |
| --- | ---: | ---: |
| Records supplied and accepted by current validator | 7 | 7 |
| Events shared between intake datasets | 3 | 3 |
| Unique contributions relative to the other intake | 4 | 4 |
| RW49 complete intake candidates | 5 | 3 |
| Future complete intake candidates | 2 | 4 |

**Union: 11 distinct events; 3 overlaps.** Antigravity contributes one incremental RW49 candidate and three incremental future candidates. This is a small supervised sample, not proof of general agent quality or time/cost efficiency. Reported research effort and primary-page inspections were not independently measured. Agent-supplied excerpts were preserved, not converted into human verification.

| Sunday–Saturday roundup | ChatGPT | Antigravity | Shared | Distinct discovery candidates | Already approved / eligible | New pending |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RW49: Nov 29–Dec 5, 2026 | 5 | 3 | 2 | **6** | **5** | **1** |
| RW50: Dec 6–12, 2026 | 2 | 2 | 1 | **3** | **2** | **1** |
| RW03: Jan 17–23, 2027 | 0 | 1 | 0 | **1** | **0** | **1** |
| RW04: Jan 24–30, 2027 | 0 | 1 | 0 | **1** | **0** | **1** |
| Total | 7 | 7 | 3 | **11** | **7** | **4** |

“Discovery candidate” means structurally valid, dated, relevant-looking virtual intake; it does not mean live facts or eligibility have been independently verified. Only the seven unchanged owner-approved event versions remain publication-eligible. All four new Antigravity events remain pending, with no editorial selection. Unknown CCL pricing is not an exclusion under the current optional-pricing policy.

## Event-level overlap and differences

| Event | Identity evidence in supplied records | Reconciliation result |
| --- | --- | --- |
| L&D as a Conductor | Same normalized registration URL, title and UTC start; supplied organizer domain | iSpring / iSpring Solutions treated as scoped name variants in the review projection. Title case, language and tracking parameters are cosmetic. Different summary/topics/audience and new cost/organizer URL stay proposed; canonical approved values retained. |
| The 2027 Learning Experience | Same event/registration page, title and start; supplied Training Industry domain | Training Industry / Training Industry, Inc. grouped. New 3:45 PM ET end time is an enrichment against an unknown end, not a contradiction. Different summary and editorial context remain unreviewed. |
| AI in the Flow of Work | Same primary event page, normalized title, scoped organizer identity and UTC start | Grouped once despite organizer suffix and alternate Zoom registration destination. Existing approved event-page destination retained; Zoom destination and description are proposals, not adopted facts. |

There are **no differing event start dates/times** across the three overlaps. There are **three description variants**, one proposed end-time enrichment, one genuinely different registration destination, and optional cost/organizer URL/editorial-context additions. These are fully recorded in `cross-stream-differences.json`; absence of a conflict is not permission to adopt a new description or statistic. The iSpring third-party URL includes a Nov 5 slug while its supplied excerpt/start say Dec 2: preserve that source inconsistency as a caution, not evidence that the already-approved date is wrong.

New Antigravity-only pending candidates:

- How Collective Energy Shapes Performance — RW49.
- Better Leaders by Design: Updating L&D’s Approach to Leadership Development — RW50.
- Learning Tech Showcase: Learning Management Systems — 2027 RW03.
- Leader Talk: L&D Strategy for Business Results in 2027 — 2027 RW04.

ChatGPT-only complete-intake contributions are Planning Sprint, Renovate Your Instructional Design Process, Trauma-Informed Leadership and Intro to Facilitating Groups. Antigravity also mentions Planning Sprint in its incomplete leads; this is a fourth shared *mention*, not a fourth shared complete-intake record or a new unique event. Use its already-approved record without requesting another source review.

## What the current production ingestor would do (sandbox only)

- Fresh combined ingestion yields **12**, not 11, records: it misses the AI in the Flow of Work overlap because the registration URL differs and “Inc.” prevents its organizer fallback match.
- Two records get native conflict flags: iSpring (organizer/title case) and Leader Talk (organizer/end time). Description variants are **not** flagged by the current comparison field list. This gap needs a regression test and explicit proposal/conflict handling.
- Fresh ingestion leaves every event pending and selects none. Native future projection has **6 rows**, including the missed duplicate; reconciled unique future count is **5**. All five unique future events are preserved in their proper weeks.
- Exact native reruns produce identical canonical/future bytes. Reversing record order within the two same-named intake files also produced identical results for this sample; that is a characterization, not a guarantee of arbitrary arrival-order independence.
- Seeded with the seven approved records, the unchanged native ingestor changes **two** approved event fingerprints and makes their old reviews stale. It leaves five previously approved records eligible and creates new pending records, including the missed duplicate. No such ingestion was run on production data.
- For those two seeded matches, `updated_at` is not the latest instant: lexical comparison of a UTC approval timestamp against a later `-06:00` discovery timestamp chooses incorrectly. Discovery timestamps remain preserved in raw submissions; timestamp aggregation should compare parsed instants.
- The canonical-file version change makes the old Work editorial input stale, so the old draft correctly fails against that hypothetical integrated state. This was tested only in the sandbox. The **actual** approved input/draft still passes the official validator with the original 1,807/1,386 characters.

These observed failures are integration blockers, not reasons to repeat already-completed source verification. `native-fresh/` and `native-seeded/` are explicitly test previews, not replacement canonical data.

## Safe migration recommendation

1. Preserve approved canonical versions, owner approvals and the validated RW49 caption package. Attach corroborating raw submissions/aliases/evidence as a sidecar keyed by stable event ID instead of mutating approved records during discovery. The review projection demonstrates this: all seven approved event fingerprints remain identical and all 14 raw submissions/source unions survive.
2. Add a narrowly scoped organizer alias mechanism backed by supplied shared primary/registration domains and matching identity fields. Never strip legal suffixes globally or merge on organizer/time alone. The two different Dec 10 sessions remain separate. Quarantine ambiguous reused-URL/date identities instead of guessing.
3. Add explicit substantive-field proposals for summary, end time, registration destination, cost, topics and audience. Keep existing approved values by default. If an optional proposal is rejected/not adopted, no source re-review or reapproval is required for the unchanged approved event. Only adopting a substantive change needs an explicit owner decision for that changed version/claim.
4. The two current-ingestor affected records are `evt_3f2f090963c7e1d0` (iSpring) and `evt_5b0c2b55e8407e36` (Leader Talk). Fixing the third overlap and appending its provenance directly to its approved record would also affect `evt_fb9c960a4c6a704d` (AI in the Flow of Work). Do not silently replace these review hashes. Use sidecars/versioned proposals now, or a separately authorized, audited approval-fingerprint migration that proves approved substantive content is unchanged. A future split of content/provenance hashes needs design approval and tests; it is not implemented here.
5. Even adding only the four new pending events to canonical storage changes the global input source-version hash. After explicit integration approval, re-export the RW49 input, compare all five event blocks/summaries/context against the old input, record an old→new checksum migration and rebind the draft envelope **only if caption bytes and approved content remain unchanged**. Revalidate; retain the old package as the historical pilot artifact. This is a package-version migration, not a demand for another source review. No migration was applied here.
6. Approve the four new events separately before editorial inclusion. RW49 would have six candidates but still only five approved; do not automatically insert CCL into the validated post. Extend tests for alias + alternate URL, summary variants, proposed end times, metadata-only approval preservation, global-input migration and mixed-offset updated_at chronology before integrating streams.

## Incomplete leads and research coverage

`incomplete-leads.json` preserves the Antigravity report’s **16 numbered entries plus one unnumbered Blanchard note**. One is the already-approved Planning Sprint, leaving **16 other lead entries**. These are not necessarily 16 distinct events: the HR.com row bundles sessions and some entries are multi-day series. The report’s total “28 candidates” is therefore a reported grouped count, not an independently established deduplicated discovery total.

Priority follow-ups include FranklinCovey Impact, Articulate’s Storyline AI session, HCI’s AI-ready workforce session, i4cp priorities, ATD sessions and NeuroLeadership’s workshop; future leads include Articulate, ICF, ROI Institute and Learning Guild sessions. They remain outside machine intake. Dates, prices, access problems and source recommendations in the Antigravity report are supplied claims, not independently checked facts here. No site restrictions were bypassed or new verification fabricated. ChatGPT’s earlier pilot did not supply a comparable incomplete-lead inventory, so no absence/coverage inference is made for that stream.

## Artifacts and reproducibility

- `originals/manifest.json`: exact preserved Git objects and SHA-256 hashes.
- `command-results.json`: actual current validator/CLI outputs.
- `acceptance-results.json`: metrics and native-ingestor limitations.
- `reconciled-review-groups.json`, `reconciled-future-groups.json`: review-only grouped projection with frozen approved versions, all raw provenance and pending proposals.
- `cross-stream-differences.json`: every compared substantive/cosmetic field variant.
- `native-seeded/approval-impact.json`: exact before/after affected fingerprints and hypothetical stale-input errors.
- `incomplete-leads.json`: follow-up entries with reported gaps.
- `preservation-proof.json`: before/after hashes of every preexisting tracked file, including approvals, canonical/future data, input and validated Work caption artifacts.
- `preserved-work-validation.json`: fresh official PASS for the existing real Work submission.

Re-run the isolated experiment:

```sh
python3 reports/pilots/discovery-consolidation-2026-11-18/run_consolidation.py
python3 -m unittest discover -s tests -v
python3 scripts/smoke.py
```

The experiment writes only this report directory and temporary sandboxes. It does not ingest Gemini into repository intake/data, update approvals, rebind draft checksums, merge branches or publish. The current production code is intentionally unchanged pending integration decisions.
