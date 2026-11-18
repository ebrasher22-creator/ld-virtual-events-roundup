# Repository readiness — November 18, 2026

**Verdict:** ready for a supervised manual discovery pilot for November 29–December 5, 2026, subject to successful final workflow checks below. No real events or independent event verifications have been imported. No automatic publication, paid AI calls, merge or deployment is enabled.

- **Branch:** keep `feature/github-event-pipeline` as temporary default/integration branch. Workflows now support it and future `main`. No history was discarded and no merge occurred. Main promotion requires approval. See branch-strategy.md.
- **Local checks:** original 10 tests passed; expanded suite 14/14 passed, zero failures. Smoke and exact manual CLI demo passed. `validate.py` and `git diff --check` passed. Local Python 3.9.6 and Actions Python 3.12 are the exercised environments; the documented deployment requirement is Python 3.11+ and Python 3.11 was not separately executed in this review.
- **Baseline Actions at fb2dee2:** manual [validation 44370700886](https://github.com/ebrasher22-creator/ld-virtual-events-roundup/actions/runs/44370700886) and [preparation 44370708145](https://github.com/ebrasher22-creator/ld-virtual-events-roundup/actions/runs/44370708145) both succeeded. Final updated-workflow run evidence will be appended after dispatch.
- **Contracts:** schema now drives runtime shape checks instead of separate handwritten required/type rules. Enums, nonempty lists, evidence structure, optional nulls, URL format and timezone-aware date checks are aligned. UTC instants with an IANA display zone are accepted; equivalent instants no longer create false time conflicts. Both agent guides spell out JSON arrays, lowercase agent names and exact enums. The source registry contains 76 classified leads; only the two supplied URLs are populated, while 74 intentional null URLs require agent discovery. The registry is never an intake allowlist.
- **Manual demonstration:** see manual-intake.md for the exact commands executed. Four submissions → two canonical events; overlap preserves ChatGPT + Gemini and three submissions; changed time quarantined; one January event retained; correct RW49 assignment; zero unverified selections; identical rerun. Isolated smoke adds a third synthetic event and simulated human review to demonstrate one-event Markdown generation. Production data remains empty.

## Remaining blockers and operating limits

No known code blocker to accepting a correctly structured real file. Required start date/time, IANA zone and grounded event/registration URLs must be established before machine intake; unresolved leads belong in separate human follow-up notes. Common blockers are Markdown-wrapped JSON, an enclosing `events` object, missing required data, unsupported agent labels/enums, timezone abbreviations, missing timestamp offsets/seconds, extra fields and text costs. These now have explicit guidance and regression coverage.

The current default branch has no protection. Supervised local/manual pilot work can proceed, but enforced multi-contributor approval requires owner-configured rulesets/branch protection and required checks. Workflow artifacts do not persist canonical changes: humans must review and commit intended changes to Git. Read-only Actions cannot merge or publish. Agent scheduling/authenticated intake remains unconfigured by design.

Live verification remains manual; synthetic reviews prove gating mechanics only. Source pages were not live-checked in this review. Discovery coverage and availability of 8–12 qualifying events are unknown until the pilot. URL reuse and completely changed event identities still need human duplicate review. Approval freshness is manual; no automatic expiry exists. Actions use major-version tags rather than immutable SHAs, an explicitly deferred hardening item.

Always pass `--as-of 2026-11-24` locally or `as_of=2026-11-24` in manual preparation dispatch for this pilot. The current date, November 18, otherwise targets November 22–28. The generated RW49 folder is `weeks/2026/RW49_2026-11-29_to_2026-12-05/`.

## PR Review

Scope: sampled initial build and readiness changes, concentrating on scripts, schema, source registry, agent contracts, workflows and tests. No project .brooks-lint.yaml was present. Health Score: 100/100 within the sampled code-readiness scope after fixes; this is not live-event or security certification. No actionable code-decay findings remain in that scope.

Diagnosed findings fixed during readiness:

- **R3 — Contract duplication (Warning, resolved).** Symptom: schema and handwritten validator disagreed on null URLs, field types and empty collections. Source: The Pragmatic Programmer — DRY. Consequence: agent files could pass a schema check and fail ingestion. Remedy: drive shape validation from the schema and add rejection/acceptance contract tests.
- **R6 — Branch/calendar assumptions (Warning, resolved).** Symptom: push filters targeted nonexistent main; preparation lacked an explicit discovery-date input. Source: Domain-Driven Design — Ubiquitous Language. Consequence: initial-branch pushes skipped validation, and current-date dispatch targeted the wrong pilot period. Remedy: retain explicit temporary branch policy, align workflow filters and add as_of input.
- **T2 — Smoke isolation (Warning, resolved).** Symptom: smoke/tests copied production intake and canonical data into fixed-count synthetic scenarios. Source: xUnit Test Patterns — Erratic Test. Consequence: future real intake would break acceptance tests. Remedy: initialize empty isolated data roots and use only test fixtures.

The focused module structure is adequate for V1; no new abstractions or dependencies were introduced. The local tests are behavior-based and do not mock the subject under test. This review sampled a large initial feature; it is not an exhaustive security audit.
