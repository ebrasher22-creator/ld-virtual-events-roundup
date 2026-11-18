# Next Week in L&D

A platform-independent, GitHub-based event intake and editorial pipeline. Python 3.11+; no dependencies, paid AI calls, unattended discovery writes, or LinkedIn publication. This repository started empty.

## Local setup and operation

```sh
git clone https://github.com/ebrasher22-creator/ld-virtual-events-roundup.git
cd ld-virtual-events-roundup
git switch feature/github-event-pipeline
python3 -m unittest discover -s tests -v
python3 scripts/smoke.py
python3 scripts/validate.py
python3 scripts/ingest.py
python3 scripts/assign_weeks.py --as-of 2026-11-24
python3 scripts/generate_post.py --as-of 2026-11-24
```

Without `--as-of`, assignment and generation use the current Chicago date. The parameter is the discovery date, not the event date. Tuesday November 24 targets `2026/RW49_2026-11-29_to_2026-12-05`. Sunday itself targets the next Sunday. Week labels use the Monday's ISO year and week, including across New Year. Display uses IANA America/Chicago and CST/CDT. Config `.yml` files use JSON syntax (valid YAML) so the standard library can read them. The schedule file describes the implemented V1 calendar policy; changing calendar policy requires a code change and boundary tests.

## Manual discovery and intake

1. Give ChatGPT or Gemini its prompt from `agents/`, the schema and source leads. Both may discover across every category. These are external human-operated discovery assistants, not API integrations.
2. Save the returned JSON array to `intake/chatgpt/unique-name.json` or `intake/gemini/unique-name.json`. Open a pull request. Never replace historical intake files.
3. Validate locally. Require branch protection and human approval before merging intake into main. This repository does not configure remote branch protection automatically.
4. Run ingestion and assignment on a working branch and commit resulting canonical changes. GitHub is the persisted source of truth. `future-events.json` is a derived projection of events after the targeted Saturday, not a separate writable database. All other records remain in canonical storage.

Raw submissions remain in intake and in canonical `submissions`, with SHA-256 fingerprints and provenance paths. Canonical URLs remove tracking parameters and fragments. Matching uses registration URL first, then normalized title + organizer + timestamp. A reused URL with a changed time is quarantined as a conflict; recurring events sharing a URL require human separation. Completely changed identity with no matching URL or timestamp requires a human duplicate review. No fuzzy match silently combines records. Reruns skip exact submissions; new submissions invalidate review.

## Independent verification and editorial review

Syntactic validation is offline: shape, links, timestamps, timezone offsets and selected enums. It does **not** establish that a URL exists, points to registration, or proves a claim. No script fetches untrusted discovery URLs. Humans must independently open primary organizer and registration pages and check relevance, virtual availability, date/time, registration destination, organizer identity, current status and price. Inaccessible or uncertain pages stay pending. Agent evidence alone never qualifies.

After ingestion and week assignment, compute the exact canonical fingerprint:

```sh
python3 -c 'import sys; sys.path.insert(0,"scripts"); from pipeline import *; print([(e["event_id"],fingerprint(e)) for e in read(ROOT/"data/canonical-events.json")])'
```

Add a record to `data/reviews.json`, keyed by event ID:

```json
{
  "evt_REPLACE": {
    "record_sha256": "REPLACE_WITH_CURRENT_FINGERPRINT",
    "decision": "verified",
    "editorial_decision": "selected",
    "reviewer": "Human reviewer name",
    "verified_at": "2026-11-24T20:00:00Z",
    "score": 8,
    "claims": {
      "relevance": {"primary_url": "https://organizer.example/event", "observation": "Record what you independently checked"},
      "virtual_availability": {"primary_url": "https://organizer.example/event", "observation": "..."},
      "datetime": {"primary_url": "https://organizer.example/event", "observation": "..."},
      "registration_url": {"primary_url": "https://organizer.example/register", "observation": "..."},
      "organizer": {"primary_url": "https://organizer.example/event", "observation": "..."},
      "status": {"primary_url": "https://organizer.example/event", "observation": "..."},
      "price": {"primary_url": "https://organizer.example/event", "observation": "..."}
    }
  }
}
```

This is a trusted human attestation, not automatic live verification. Protect reviews with CODEOWNERS/required approvals in repository settings. Discovery-supplied verified/editorial fields are discarded; authoritative review decisions live separately in reviews.json. Canonical verification defaults stay pending; effective eligibility is computed from the review ledger. Hashes invalidate approvals when any canonical content changes, including assignment. Review after assignment. Recheck time-sensitive pages before publication; V1 has no automatic review-expiry policy.

To resolve conflicts, inspect all preserved submissions against primary evidence, edit canonical fields and clear only resolved conflict flags on a reviewed branch. Add `resolution_notes` with reviewer, time, source URLs and rationale; the old/new values remain in Git history and raw submissions. Then regenerate a fresh review hash. Never clear a flag simply to increase the event count.

Generation prioritizes free virtual sessions, then human score, with a configurable target of 8–12. Paid and hybrid sessions are labeled. Humans must exclude vague sales pitches, duplicate promotions and weak learning value before selecting. Fewer qualified events produces a below-target warning in `review.json`, not invented filler. Markdown and compact alternative are deterministic; if even the compact version exceeds the configured character limit, generation fails for human reduction. No generated file constitutes publication approval. Review wording, links, timezone and count, then manually copy an approved post into LinkedIn.

## Automation and security

`validate.yml` tests pull requests with read-only permissions, without secrets or AI calls. `weekly-publishing.yml` prepares ingestion and optional regeneration on manual dispatch or merged intake/review changes to main. It uploads canonical changes and drafts as review artifacts; it cannot commit, merge or publish. Download and inspect artifacts, then persist intended changes through a reviewed PR. No schedule is enabled: manual discovery is required. Action major-version tags should be pinned to reviewed immutable SHAs before a hardened production rollout. Never use pull_request_target to execute intake code.

Future automated intake can use a GitHub App limited to one repository with contents and pull-request write permissions, short-lived installation tokens held outside prompts, strict payload/schema/size validation, request signatures, replay protection and rate limits. It should only create intake PRs, never edit the review ledger or canonical approvals. Keep manual upload available. Scheduled ChatGPT/Gemini tasks are not assumed to have authenticated write access.

## Acceptance evidence and limitations

`python3 scripts/smoke.py` operates in a temporary repository-shaped folder, imports both fixtures, consolidates overlap, flags conflicting times, retains a future event, proves rerun stability, simulates a separate trusted review, and emits a one-event sample draft under `tests/smoke-output/`. Every example is synthetic and uses example.org. No real event has been live-verified. Production intake/canonical/review files remain empty. The generated sample is deliberately below the editorial target and is not publishable.

The tests cover valid/invalid submissions, missing timezone offsets, malformed URLs, duplicate provenance, changed dates/times, quarantine, unverified exclusion, DST gaps/folds, Sunday/Saturday boundaries, ISO year transitions, deterministic output, review invalidation and length failure. V1 deliberately requires human verification, conflict resolution, selection, final approval and publication. Remote Actions execution, branch protection and actual ChatGPT/Gemini task setup require repository-owner integration.
