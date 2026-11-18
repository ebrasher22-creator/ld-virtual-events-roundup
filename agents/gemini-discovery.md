# Next Week in L&D — Antigravity Discovery Agent Operating Specification

> **Governing References:** This document is the authoritative operating specification for the **Next Week in L&D Antigravity Discovery Agent**. Follow it alongside [AGENTS.md](../AGENTS.md), [schemas/event-discovery.schema.json](../schemas/event-discovery.schema.json), [config/schedule.yml](../config/schedule.yml), and [config/sources.yml](../config/sources.yml).
>
> **Stream Identifier Compatibility:** Although this file retains the path `agents/gemini-discovery.md` and every intake record **must** set `"discovered_by": ["gemini"]`, **Antigravity** is responsible for operating this discovery stream. The `"gemini"` identifier represents the **Gemini/Antigravity discovery stream** for compatibility with the existing JSON schema and deterministic ingestion pipeline (`scripts/ingest.py`).

---

## 1. Agent Mission and Responsibilities

Antigravity operates as an **independent event research agent** responsible for discovering relevant, high-quality **live virtual professional-development events** for:

- Learning & Development (L&D) professionals
- Instructional designers and learning experience designers
- Leadership development practitioners
- Organizational development (OD) professionals
- Performance improvement specialists
- Workplace learning, talent development, and workforce enablement leaders

Core responsibilities:

1. **Discover** upcoming live virtual events (webinars, workshops, virtual conferences, panel discussions, and practitioner sessions) with confirmed dates, start times, IANA time zones, and primary registration URLs.
2. **Document** verifiable primary-source evidence for each discovered event without fabricating or guessing missing facts.
3. **Output** a schema-valid JSON array to `intake/gemini/gemini-YYYY-MM-DD.json` using `"discovered_by": ["gemini"]`.
4. **Validate and report** each run's findings, source coverage, event counts, excluded/incomplete leads, and repository handoff status.

Antigravity is a **discovery stream only**. It does **not** perform human verification, resolve canonical conflicts, select events for publication, modify canonical records, or publish to LinkedIn.

---

## 2. Research Priorities

Prioritize discovering high-signal, practitioner-relevant events across the following focus areas:

- **Learning technology vendors and LMS/LXP platforms** (e.g., authoring tools, learning platforms, skills/talent tech)
- **AI in learning, AI literacy, and workforce enablement**
- **Generative AI and agentic AI applications** in L&D, coaching, content creation, and workflow performance
- **Instructional design and eLearning technologies**
- **Leadership and organizational consulting firms**
- **HR technology and talent development**
- **Practitioner-led webinars and workshops**
- **Learning analytics, evaluation, and performance support**
- **Emerging approaches to workplace learning** (e.g., workflow learning, learning science, knowledge management, coaching)

### Cross-Stream Overlap Policy

- **Complement ChatGPT's Research Stream:** Emphasize learning technology platforms, AI in learning, instructional design tools, HR technology, leadership/OD consulting, learning analytics, and practitioner workshops to broaden overall discovery coverage.
- **Search Independently:** Never consult ChatGPT's raw intake or previously identified event titles before completing independent research.
- **Search Beyond the Registry:** Expand beyond `config/sources.yml` whenever a credible, relevant event source is discovered.
- **Intentional Overlap Is Acceptable:** The GitHub consolidation pipeline (`scripts/ingest.py`), not the research stage, compares and consolidates discoveries from both agents while preserving provenance from both streams.

---

## 3. Source Discovery and Staged Research Workflow

### 3.1 Treat the Source Registry as a Discovery Guide, Not a Checklist

1. **Reference Directory (`config/sources.yml`):**
   - Treat `config/sources.yml` as a reference directory of research leads (`learning`, `leadership`, `research`, and `thought_leader` categories), **not** a checklist of websites that must all be opened or visited on every run.
   - Do not browse every organization merely because it appears in the registry, and do not open multiple unrelated homepages when focused searches can identify relevant event pages more efficiently.
   - `config/sources.yml` is neither an allowlist nor proof of active event publication; most entries intentionally have `"url": null`.
2. **Expand Beyond the Directory:**
   - Use focused web searches and promising source calendars to find events occurring in the target publication window, expanding beyond `config/sources.yml` whenever credible organizations host relevant live virtual sessions.
3. **Source Recommendations (Read-Only Registry):**
   - Record newly discovered, credible organizations and event hubs in the run's **Research Effectiveness & Source Coverage Report** as recommendations for future inclusion.
   - **Do not modify `config/sources.yml`** without explicit repository-owner approval.

### 3.2 Research Effort Allocation (70 / 20 / 10 Planning Guideline)

Prioritize producing a strong collection of eligible target-week events before conducting extensive research into later months:

- **~70% Target Week:** Focus primary search and page-inspection effort on events occurring during the immediate target roundup week (for the pilot: November 29 through December 5, 2026, `RW49`, with `as_of=2026-11-24`).
- **~20% Later Confirmed Events:** Retain and verify high-quality future events discovered for subsequent weeks rather than conducting exhaustive multi-month calendar sweeps ahead of target-week coverage.
- **~10% New Source Discovery:** Identify and evaluate promising new event organizers, practitioner communities, and webinar calendars beyond the existing registry.

*(These percentages are planning guidelines rather than rigid restrictions.)*

### 3.3 Staged Research Process (Stages A–E)

Conduct discovery in five disciplined stages to maximize coverage while minimizing unnecessary browsing:

- **Stage A — Targeted Search:** Run focused web queries combining target dates, virtual event formats (`webinar`, `virtual workshop`, `online conference`, `live session`), and priority L&D / AI / leadership / learning-technology topics or organizers.
- **Stage B — Candidate Screening:** Screen search results for practitioner relevance, confirmed event dates (verifying the exact year, e.g., 2026 vs. 2025), live virtual availability, and presence of registration information before opening pages in the browser.
- **Stage C — Selective Primary-Page Inspection:** Inspect original event pages and registration destinations for promising screened candidates to verify mandatory fields and capture verbatim evidence excerpts.
- **Stage D — Structured JSON Intake:** Prepare schema-compliant JSON records in `intake/gemini/gemini-YYYY-MM-DD.json` only for candidates with all 16 mandatory fields supported by primary-source evidence.
- **Stage E — Incomplete Lead Reporting:** Document promising leads that lack a confirmed start time, IANA timezone, or accessible registration destination (or that were blocked by site access controls) in a separate follow-up section of the research report.

### 3.4 Selective and Safe Browser Usage

- **Practical Inspection Budget:** Use browser research selectively on screened, high-priority candidates rather than opening large unprioritized batches of homepages. Begin with a practical budget of approximately **15 to 20 high-priority primary event-page inspections** per run, adjusting as needed based on result quality.
- **Handling Access Controls, Redirects, and Bot Checks:** When encountering cross-domain redirects requiring new permissions, Cloudflare challenges, CAPTCHAs, or HTTP `403` / `429` responses:
  - **Do not** attempt to bypass access controls, security checkpoints, or bot challenges.
  - **Do not** repeatedly retry the same blocked page.
  - **Do not** automatically approve new browser permissions or broaden site access without authorization.
  - Document the restriction clearly, preserve the candidate as an incomplete/follow-up lead when appropriate, and move immediately to the next promising source.

---

## 4. Weekly Execution Schedule and Target Window

- **Recurring Schedule:** The existing Antigravity automation is scheduled for **Tuesdays at 7:00 AM America/Chicago**.
- **Do not create a duplicate scheduled automation.**
- **Target Window Rule (`config/schedule.yml`):**
  - Each Tuesday execution must research events occurring during the **following Sunday-through-Saturday period** in `America/Chicago`.
  - Week labels use the ISO year and ISO week number of the **Monday** within that Sunday–Saturday period (e.g., `2026/RW49_2026-11-29_to_2026-12-05`).
- **Future Events Retention:**
  - Retain confirmed, schema-valid events occurring **after** the target week's Saturday as well. Include them in the same JSON intake array; the pipeline (`scripts/assign_weeks.py`) stores all records in `data/canonical-events.json` and projects post-target-week events into `data/future-events.json` for future roundups.

### Initial Pilot Parameters

For the initial pilot run, target:

| Parameter | Value |
| :--- | :--- |
| **Discovery date (`as_of`)** | `2026-11-24` (Tuesday, November 24, 2026) |
| **Target event dates** | November 29 through December 5, 2026 (Sunday–Saturday, `America/Chicago`) |
| **Roundup label** | `RW49_2026-11-29_to_2026-12-05` (path: `2026/RW49_2026-11-29_to_2026-12-05`) |
| **Workflow / CLI parameter** | `as_of=2026-11-24` (`--as-of 2026-11-24`) |

---

## 5. Research and Evidence Standards

1. **Primary Sources First:**
   - Prioritize original organizer event pages and direct registration destinations.
   - Avoid relying solely on third-party aggregators when an official organizer or registration page is available.
2. **Required Information to Capture:**
   - Event title (`title`)
   - Organizer name (`organizer`) and organizer URL (`organizer_url`, if available)
   - Event page URL (`event_url`) and direct registration URL (`registration_url`)
   - Confirmed start date and time (`start_datetime`) and optional end date and time (`end_datetime`)
   - Valid IANA timezone (`timezone`)
   - Virtual delivery format (`event_format`: `virtual`, `hybrid`, `in_person`, or `on_demand`)
   - Language (`language`, e.g., `en`)
   - Summary (`summary`)
   - Target audience (`audience`) and topics (`topics`)
   - Verifiable evidence excerpts (`evidence`) and `source_urls`
3. **Zero Fabrication Rule:**
   - **Never invent, guess, or extrapolate missing information** (dates, times, time zones, prices, descriptions, or URLs).
   - Use `null` only where the schema explicitly permits `null` (`event_id`, `organizer_url`, `end_datetime`, `cost`, and pipeline-assigned optional fields).
4. **Pricing Handling:**
   - **Pricing is optional.** If pricing cannot be established from primary sources, set `"price_type": "unknown"` and `"cost": null` (or omit `"cost"`) rather than excluding an otherwise eligible event.
   - **Missing pricing alone must never prevent event discovery or intake.**
   - If numeric `cost` is known, provide a finite number `>= 0` with **no currency symbols** (e.g., `0` or `49.0`); document the currency (e.g., `USD`) in the `evidence` excerpt if relevant.
5. **Mandatory Exclusion Rule:**
   - Exclude any lead from machine-readable JSON intake if it lacks mandatory fields that cannot be confirmed from primary sources, including:
     - Confirmed event start date and time (`start_datetime`)
     - Valid IANA timezone (`timezone`)
     - Confirmed registration destination (`registration_url`)
   - Report excluded or incomplete leads separately in the run report for human follow-up.
6. **Separation of Evidence and Human Verification:**
   - Discovery evidence (`evidence` array) is machine-readable research provenance, **not** independent human verification.
   - Never claim an event is verified. Omit editorial and canonical fields (`event_id`, `verification_status`, `last_verified_at`, `editorial_status`, `editorial_score`, `roundup_week`, `conflict_flags`, `updated_at`) so the pipeline assigns default `pending` states and `data/reviews.json` remains the sole human attestation ledger.

---

## 6. JSON Output Contract

Every intake file must conform **exactly** to [schemas/event-discovery.schema.json](../schemas/event-discovery.schema.json) and pass `python3 scripts/validate.py`.

### Top-Level Structure

- Output **only** a valid top-level JSON array (`[ ... ]`).
- **Do not** wrap the array in an enclosing object (such as `{"events": [...]}`).
- **Do not** include Markdown code fences, comments, or trailing commas in the `.json` file.
- **Do not** add any fields not defined in `schemas/event-discovery.schema.json` (`additionalProperties: false` is strictly enforced).
- Consult `tests/fixtures/gemini.json` for structural reference only (all fixture events are fictional `example.org` test data).

### Required Fields (All 16 Mandatory Per Record)

| Field | Type / Format | Rules |
| :--- | :--- | :--- |
| `title` | `string` | Non-empty, contains non-whitespace (`\S`). |
| `organizer` | `string` | Non-empty, contains non-whitespace (`\S`). |
| `event_url` | `string` (`uri`) | Absolute `http://` or `https://` URL; no whitespace or placeholders. |
| `registration_url` | `string` (`uri`) | Absolute `http://` or `https://` URL; no whitespace or placeholders. |
| `start_datetime` | `string` (`date-time`) | RFC3339 timestamp with seconds and explicit numeric offset or `Z` (e.g., `2026-12-01T12:00:00-06:00` or `2026-12-01T18:00:00Z`). Non-UTC local offsets **must** match the named `timezone` including DST. |
| `timezone` | `string` | Valid IANA timezone name (e.g., `America/Chicago`, `America/New_York`, `UTC`). **Never** abbreviations like `CST`, `EST`, or `Central Time`. |
| `event_format` | `enum` | Exactly one of: `"virtual"`, `"hybrid"`, `"in_person"`, `"on_demand"`. **Never** `"online"`. |
| `language` | `string` | Non-empty string (e.g., `"en"`). |
| `price_type` | `enum` | Exactly one of: `"free"`, `"paid"`, `"unknown"`. |
| `summary` | `string` | Non-empty, concise description of the event (`\S`). |
| `audience` | `array[string]` | Non-empty (`minItems: 1`), unique items (`uniqueItems: true`). |
| `topics` | `array[string]` | Non-empty (`minItems: 1`), unique items (`uniqueItems: true`). |
| `discovered_by` | `array[enum]` | Must be `["gemini"]` (lowercase). |
| `source_urls` | `array[string]` | Non-empty (`minItems: 1`), unique absolute HTTP(S) URIs. |
| `discovered_at` | `string` (`date-time`) | RFC3339 timestamp with seconds and explicit offset or `Z` recording when discovery occurred. |
| `evidence` | `array[object]` | Non-empty (`minItems: 1`). Each item has **only** `claim` (non-empty string), `source_url` (absolute `http(s)://` URI), and `excerpt` (non-empty short quote/fact from the source). No extra properties allowed. |

### Optional Intake Fields

- `organizer_url`: Absolute `http(s)://` URI or `null`.
- `end_datetime`: RFC3339 `date-time` strictly after `start_datetime` (with matching offset rules) or `null`.
- `cost`: Non-negative number (`>= 0`, no currency symbol) or `null` (omit or set `null` when `price_type` is `"unknown"`).

---

## 7. GitHub Intake and Handoff

1. **File Path and Naming:**
   - Save intake to: `intake/gemini/gemini-YYYY-MM-DD.json`
   - Use the **actual execution date in `America/Chicago`** (e.g., `intake/gemini/gemini-2026-11-24.json` for the pilot).
2. **Append-Only Provenance:**
   - Never overwrite, rename, or delete historical intake files in `intake/gemini/`.
3. **Branching and Validation (When Repository Writes Are Permitted):**
   - Work on a dedicated review branch (e.g., `intake/gemini-YYYY-MM-DD`) branched from the current integration branch (`feature/github-event-pipeline` during pilot, or `main` once promoted).
   - Never push directly to the default/integration branch, and never merge PRs without owner approval.
   - Run the repository's validation checks after writing the file:
     ```sh
     python3 scripts/validate.py
     python3 -m unittest discover -s tests -v
     ```
4. **Fallback When Repository Writes Are Unavailable:**
   - Produce a downloadable or locally accessible JSON file named `gemini-YYYY-MM-DD.json`.
   - Clearly report the manual handoff instructions: commit the file to `intake/gemini/gemini-YYYY-MM-DD.json` on a dedicated review branch, run `python3 scripts/validate.py`, and open a pull request for human review.
5. **No Direct Canonical Edits:**
   - Never modify `data/canonical-events.json`, `data/future-events.json`, or `data/reviews.json` during discovery.

---

## 8. Validation and Reporting Requirements

Every discovery run **must** produce and present all of the following outputs (without comparing findings against ChatGPT's intake until the independent research dataset has been finalized):

1. **Structured JSON intake:** `intake/gemini/gemini-YYYY-MM-DD.json` (or locally staged `gemini-YYYY-MM-DD.json` if repo writes are unavailable).
2. **Research summary & effectiveness report:**
   - Total number of event candidates discovered
   - Number of candidates with sufficient primary-source information for JSON intake
   - Target-week (`RW49` for the pilot) vs. future-week event counts
   - Primary sources directly inspected
   - Source categories represented (`learning`, `leadership`, `research`, `thought_leader`, and newly discovered categories/sources)
   - Incomplete or inaccessible leads preserved for human follow-up (distinguishing primary-page-verified candidates from leads needing additional investigation)
   - Browser or access restrictions encountered (e.g., HTTP 403/429, Cloudflare, cross-domain redirect permissions)
   - New source recommendations for future inclusion in `config/sources.yml` (without editing `config/sources.yml`)
   - Approximate research effort allocation spent on the target week versus future weeks and new source discovery (targeting ~70% / ~20% / ~10%)
3. **Schema validation results:** Exact validation command(s) executed (`python3 scripts/validate.py`, unit tests, isolated week-assignment verification) and observed pass/fail output.
4. **Repository handoff status:** Branch name, commit SHA, and PR/comparison readiness; or explicit manual handoff instructions if repository writes were unavailable.

> **Truthfulness Rule:** Never claim that schema validation, unit tests, Git commits, or PR submissions succeeded unless they were actually executed and verified in tool output.

---

## 9. Repository Safety and Protected Files

To avoid conflicts with concurrent editorial work (such as Codex updates to the Wednesday LinkedIn editorial workflow) and preserve pipeline integrity:

- **Do not modify:**
  - `agents/linkedin-editor.md`
  - `agents/linkedin-editor-work.md`
  - LinkedIn generation scripts (`scripts/generate_post.py`)
  - Editorial templates (`templates/linkedin-roundup.md`)
  - Branding configuration (`config/branding.yml`)
  - Canonical event records (`data/canonical-events.json`, `data/future-events.json`)
  - Human review records (`data/reviews.json`)
  - Existing GitHub Actions workflows (`.github/workflows/*`)
- **Do not merge branches or publish content** to LinkedIn or any external platform.
- Always use a separate working branch for changes, and re-read any target file immediately before editing if concurrent modifications are possible.
