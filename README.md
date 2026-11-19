# Next Week in L&D — production operation

ChatGPT + Antigravity discovery → append-only GitHub intake PRs → trusted automated validation/consolidation → current primary-source qualification → Wednesday LinkedIn draft → Jarvis delivery → Eddie’s final review and manual publication.

No per-event owner approval is required. Unresolved sources, material conflicts and the explicit CCL deferral remain excluded. No paid APIs or external automation service.

- [Production operations](docs/production-operations.md)
- [ChatGPT discovery](agents/chatgpt-discovery.md)
- [Antigravity discovery](agents/antigravity-discovery.md)
- [Jarvis prompt](agents/jarvis-editorial-handoff.md) and [setup](docs/jarvis-task-setup.md)
- [Implementation evidence](reports/production-readiness-implementation.md)

Production base is main. Development uses feature branches. Historical Gemini intake is retained byte-for-byte; new Antigravity intake uses antigravity. Wednesday generation: 07:00 America/Chicago; Jarvis: 08:00. Schedules are DST-aware.

```
python3 -m unittest discover -s tests -v
python3 scripts/validate.py
python3 scripts/smoke.py
python3 scripts/submit_intake.py --agent antigravity --file /absolute/path/findings.json --base main
```

Tests/smoke-output are synthetic, never production intake. Historical pilot artifacts and Work drafts remain under reports/history and other historical report directories; they do not authorize publication or represent current weekly readiness.
