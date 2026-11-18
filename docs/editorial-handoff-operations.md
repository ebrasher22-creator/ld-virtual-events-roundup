# Wednesday editorial operational handoff

This review branch isolates editorial operations from Antigravity's consolidation work. Base: d019b05. No canonical data, review ledger, source approvals, discovery code or scheduling settings may be changed by this handoff.

A supervised RW49 capability rehearsal will test explicit-ref input retrieval and the available Work write/return surface. An authorized probe may create only `handoff-probes/rw49-work-capability.json` on `review/wednesday-operational-handoff-2026-11-18`. It must not create credentials, change permissions or write to any other branch. A failed/unavailable write is an operational limitation, not grounds to widen access.

Until an unattended submission route is demonstrated, preserve the supported owner-mediated return: Work generates work-submission.json; the owner downloads it; the local editorial handoff command invokes the existing validator and produces a self-contained human/Jarvis review packet. No new production workflow or schedule is activated by this branch.
