# Jarvis task setup

Name: Next Week in L&D | Jarvis Editorial Handoff
Schedule: Wednesdays, 08:00 America/Chicago, DST-aware.
Environment: existing private published roundup Cloud environment, existing GitHub connection, main.
Prompt: use the complete text in agents/jarvis-editorial-handoff.md. This file and the agent file together are the full implementation specification.

Create only after the Wednesday workflow passes hosted validation and the owner confirms task creation. Verify the saved task ID, enabled state, inherited published environment and next occurrence; test delivery through the task's own supported run mechanism. Do not claim delivery into a separate Jarvis chat without observing that destination. If targeting a separate chat is unsupported, report the limitation and provide the native task result directly to Eddie. Do not change or create a second discovery task.

## Complete scheduled-task prompt

# Next Week in L&D | Jarvis Editorial Handoff

Run every Wednesday at 08:00 America/Chicago. Read-only delivery to Eddie; never edit, merge, approve or publish.

Use the existing GitHub connection for ebrasher22-creator/ld-virtual-events-roundup, ref main. Calculate the upcoming Sunday–Saturday with scripts/pipeline.py target() using the current Chicago date. Read weeks/current-handoff.json, the matching weeks/<year>/<roundup>/editorial-report.json and linkedin-post.md from one immutable current main commit. Do not trust a stale current pointer: require the target roundup, a generated_on_local_date equal to today's Chicago date, source/report agreement and publication_approval_status awaiting_final_human_review.

Confirm the post exists, independently count its Unicode characters (maximum 3000, working budget 2800), count report events_included and compare with handoff count, verify qualification_mode automated_no_per_event_human_approval and current registration checks, report exclusions, warnings and workflow status. Compare source file hashes when available. On missing, stale, over-limit or inconsistent artifacts report NOT READY — ACTION REQUIRED with exact blocker and source links. Never return a stale caption as current. On valid artifacts with advisories report READY WITH WARNINGS; otherwise READY FOR EDDIE’S REVIEW. Mechanical validation is never publication approval.

Present Eddie with the post text or a direct GitHub link to linkedin-post.md, the editorial report link, target period, included-event count, actual character count, registration/qualification summary and unresolved warnings. Say clearly: nothing was published; Eddie decides whether to publish. Do not request separate event-by-event approvals. Do not regenerate or alter the caption. No paid APIs, new services, credentials, or changes to any schedule.

In the Cloud checkout, run `python3 scripts/jarvis_handoff.py` for the read-only packet checks and report any failed readiness status. Read GitHub from one current main commit rather than reusing old chat files.
