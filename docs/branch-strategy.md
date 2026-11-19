# Production branch strategy

`main` is the default production branch. It was created at tested commit 12f9242cdba70b8992e8744b9d96f40670a815bc following the explicit owner P1–P8 promotion approval. Historical integration/review/diagnostic branches remain intact. Diagnostic PRs #1–#4 were not merged.

All development uses feature/fix branches and protected PRs with the required validate check. main-history-protection blocks deletion and force pushes. main-validated-changes requires PRs and validation, with no bypass actors and no per-event human-approval requirement.

GitHub rejected a built-in Actions integration bypass (HTTP422). The owner approved the supported alternative: trusted automation creates data-only PRs, explicitly dispatches validation, records a validate status only for the exact successful SHA, and merges through normal branch enforcement. It never uses --admin. The repository permits Actions PR creation through GitHub’s combined creation/review setting; these workflows never submit approving reviews.

Raw discovery PRs are validated as data, copied append-only by trusted main code, and closed only after successful protected persistence. Their branches are retained. Antigravity/ChatGPT discovery agents cannot merge or approve; only repository-controlled processing persists data. Historical owner reviews remain an audit ledger, not a recurring qualification gate. Eddie alone reviews the final caption and publishes manually.
