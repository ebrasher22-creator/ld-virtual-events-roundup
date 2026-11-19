# Engineering rules — approved P1–P8 production policy
Preserve historical raw intake, evidence, provenance, approvals and review decisions. Use Python 3.11+ standard library; no paid AI calls or new services. Develop on feature branches; run the full unittest suite, validator and isolated smoke before integration. Production is main. Owner authorized promotion and automated data persistence after successful tests. Never merge diagnostic/synthetic PRs or publish to LinkedIn.

Qualification is deterministic and automatic; there is no separate per-event human approval. Current live primary-source checks must establish required facts; discovery evidence alone cannot confirm an inaccessible page. Exclude unresolved material conflicts and incomplete checks, and report them. Preserve the explicit CCL deferral in config/qualification.yml. Never infer free admission.

Intake workflows execute trusted main code only; PR content is read as data. Only owner-authorized same-repository intake PRs with matching source identity and append-only paths are processed. Never execute submission code or interpolate submission text into shell commands. Keep token permissions narrow and do not expose credentials.

Wednesday at 07:00 America/Chicago, deterministic GitHub generation is authoritative. Jarvis at 08:00 reads the completed post/report without editing. Only Eddie's final LinkedIn review and manual publication are recurring human checkpoints. Never claim an unobserved schedule, delivery, workflow result or primary-source check succeeded.
