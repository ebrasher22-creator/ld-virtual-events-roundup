# Next Week in L&D | Wednesday LinkedIn Generator Implementation

## Objective

Implement the Wednesday LinkedIn publishing preparation workflow using the existing Next Week in L&D repository.

Repository: https://github.com/ebrasher22-creator/ld-virtual-events-roundup

Current pilot branch: `review/chatgpt-2026-11-18-pilot`

Latest reported commit: `bf8e89d`

Do not rebuild the repository or introduce paid AI API calls.

The objective is to transform the approved weekly event collection into a consistent, professionally written LinkedIn roundup, ready for my final review and manual publication.

## 1. Record My Verification Decision

I have personally verified and approved the seven events in the ChatGPT pilot intake.

This is my authorization to advance those seven records through the existing human-verification workflow.

Do not request another verification of the source pages.

Do not repeat the event research.

Do not invent individual observations or claim that checks were performed by someone else.

Inspect the current human-review ledger design and implement a trustworthy way to record my explicit approval.

If the existing review ledger requires individual verification observations that were not recorded, add a compatible human-attestation mechanism rather than fabricating them.

Retain the record-fingerprint safeguards and invalidate approvals if substantive event information changes.

All seven events may be approved for inclusion in their appropriate roundup weeks.

Five belong to RW49, November 29 to December 5, 2026. The other two belong to RW50.

Do not automatically publish any events.

## 2. Make Pricing Optional

I have decided that missing event pricing should not disqualify an event from publication.

Update the repository's eligibility and editorial logic accordingly.

Requirements:

- Permit `price_type: "unknown"`.
- Preserve the original price value in the underlying event data.
- When pricing is confirmed as free, display "Free".
- When pricing is confirmed as paid, display "Paid" or an independently supported amount.
- When pricing is unknown, omit the price label from the LinkedIn post.
- Never assume an event is free merely because no price is listed.
- Do not require separate price evidence for events with unknown pricing.
- Keep the other event eligibility and human-approval safeguards intact.

Update regression tests to confirm that otherwise approved events remain eligible when pricing is unknown.

## 3. Wednesday Content Generation

Build upon the existing:

- `agents/linkedin-editor.md`
- `scripts/generate_post.py`
- `templates/linkedin-roundup.md`
- `config/branding.yml`
- `config/editorial-rules.yml`

Generate a branded, readable LinkedIn post from the approved canonical event records.

The generator must select only events assigned to the intended Sunday-to-Saturday roundup week.

Do not pull events from later weeks merely to reach the editorial target.

### Editorial Structure

Use this consistent structure:

**Opening**

A short, compelling introduction identifying the roundup as "Next Week in L&D" and highlighting the value of the week's professional-development opportunities.

**Event Listings**

Each event should contain:

- Event title
- Hosting organization
- Day and date
- Start time in Central Time, with CST or CDT as appropriate
- Registration URL
- Price label only when confirmed

**Closing**

End with a brief engagement-oriented CTA that invites readers to share other worthwhile learning opportunities or identify sessions they plan to attend.

Include a limited number of relevant professional hashtags when space allows.

### Voice and Style

The writing should be:

- Professional but conversational
- Helpful and community-centered
- Concise and easy to scan
- Credible and research-grounded
- Enthusiastic about continuous learning without sounding promotional
- Consistent from week to week

Avoid excessive emojis, generic marketing language, fabricated learning objectives, and unnecessary descriptions.

The roundup is a curated professional resource, not a sales advertisement.

## 4. LinkedIn Formatting and Length

Keep the generated LinkedIn caption within the repository's configured 3,000-character limit.

Prioritize the information needed to evaluate and register for an event.

If the complete collection does not fit:

1. Shorten the introduction.
2. Condense individual event descriptions.
3. Remove nonessential text.
4. Preserve accurate titles, dates, times, organizers, and registration links.
5. Provide a compact alternative when necessary.

Never silently remove approved events solely because of the character limit.

If all necessary event information still cannot fit, generate a clearly flagged editorial exception for human review.

Do not invent abbreviated registration URLs.

## 5. Weekly Event Count

The current editorial target is 8 to 12 events.

For the RW49 pilot, only five qualifying events have been identified and approved.

Generate the post with those five events.

The target minimum is an editorial preference, not an absolute publication requirement.

When fewer than eight events qualify, report a below-target advisory but do not block generation.

Never add unverified or future-week events to increase the count.

## 6. Required Generated Artifacts

For each roundup week, produce:

`linkedin-post.md`

The full LinkedIn caption, ready for copy and paste.

`linkedin-post-compact.md`

A shorter alternative that preserves essential event details.

`editorial-report.json`

Include:

- Roundup identifier
- Generation timestamp
- Total approved events for the target week
- Events included
- Events excluded and reasons
- Missing optional pricing information
- Character counts
- Source commit or canonical record version
- Publication approval status

`publication-checklist.md`

Include a short final review checklist covering formatting, readability, event order, links, time zone display, and publication readiness.

Generated artifacts do not constitute authorization to publish.

## 7. Wednesday Schedule and Automation

Prepare a recurring workflow for:

**Wednesday at 7:00 AM America/Chicago**

Each Wednesday, identify the roundup for the immediately upcoming Sunday-to-Saturday period.

The initial pilot must support:

`as_of=2026-11-24`

Target:

`RW49_2026-11-29_to_2026-12-05`

Implement the workflow using GitHub Actions or the existing repository infrastructure, without paid OpenAI or Gemini API calls.

Use manual `workflow_dispatch` for the initial pilot.

The workflow should:

1. Read the approved canonical events.
2. Confirm human approval records are current.
3. Assign the correct roundup week.
4. Generate the LinkedIn content.
5. Validate the output.
6. Store or upload review artifacts.
7. Report successful completion or errors.

Do not enable recurring unattended execution until the supervised pilot passes and I approve activation.

## 8. Jarvis Handoff

Prepare a clear handoff that Jarvis can use for an 8:00 AM Wednesday briefing.

The handoff should include:

- Roundup week
- LinkedIn draft
- Event count
- Link to generated artifacts
- Any unresolved editorial issues
- Final approval status

Do not assume Jarvis has automatic access to the repository or the artifact files.

Document a supported handoff method and identify any manual or integration steps necessary.

Do not create another duplicate recurring briefing task without reviewing the intended integration.

## 9. Publication Safeguards

LinkedIn publication remains manual.

Do not:

- Automatically post to LinkedIn
- Merge repository branches without my approval
- Change event details without evidence
- Add unapproved events
- Fabricate prices
- Introduce paid model API calls
- Treat generated content as approved publication
- Bypass the repository's canonical event approval mechanisms

## 10. Acceptance Test

Run a supervised end-to-end test using the five approved RW49 events.

Confirm that:

1. My approval is represented accurately in the repository.
2. The generator recognizes all five RW49 events as eligible.
3. The two RW50 events remain available for future roundups.
4. Missing pricing does not disqualify an event.
5. All event times display correctly in Central Time.
6. The post stays within the configured LinkedIn character limit.
7. The full and compact versions are generated successfully.
8. The editorial report correctly identifies five approved events.
9. Repeated execution produces stable output, apart from explicitly time-dependent report metadata.
10. No publication or unauthorized merge occurs.

Run the complete regression suite and report the results.

## 11. Delivery

Provide:

- Implementation summary
- Updated files
- Full and compact LinkedIn drafts
- Test results
- Editorial readiness report
- Remaining integration limitations
- Git branch and commit details
- Recommendation on activating the Wednesday automation

Do not merge, deploy, or publish without my approval.

**The immediate priority is producing the first accurate, approved, publication-ready LinkedIn roundup for RW49.**