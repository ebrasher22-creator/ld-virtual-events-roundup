# Branch strategy during readiness and pilot

The remote was empty before the initial build. Its first pushed branch, `feature/github-event-pipeline`, became the default. There is no main branch to merge into.

For the pilot, retain this feature branch as the temporary default/integration branch, preserving `fb2dee2` and all descendants. Do not create, rename or switch the default to main as an implicit approval of the build. Both workflows now explicitly target this temporary branch and future `main`. Manual dispatch uses the selected ref. The preparation workflow only uploads artifacts; it has no repository write or publication permission.

Use separate `intake/...` or `fix/...` branches for subsequent submissions, targeting the temporary default for human review. No pull requests are merged by automation. Require repository-owner approval for accepting intake/canonical/review changes. GitHub reported the current branch is unprotected during this readiness check; enforcement is an owner integration task. Configure branch/ruleset protections and required `validate` checks after the successful Actions runs, accounting for repository plan support. Do not enable an admin bypass or relax protections to accept failed intake.

After explicit approval of the initial platform, create `main` at the approved commit, designate it the default, configure protections there, retarget open pull requests, and remove the temporary feature-branch workflow filters. This can be a deliberate approved promotion without rewriting or deleting history. No such promotion, merge or default-branch change was performed by the readiness review.
