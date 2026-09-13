# PR-gated generated patches

Generated catalog changes are delivered through a serial pull-request queue. The producer and merger are separate GitHub Apps.

## Required repository secrets

- `PATCH_PRODUCER_APP_ID`
- `PATCH_PRODUCER_PRIVATE_KEY`
- `PATCH_MERGER_APP_ID`
- `PATCH_MERGER_PRIVATE_KEY`

The producer App needs repository Contents write and Pull requests write permissions. It must not have Administration permission and is not used for merging. Metadata read is granted automatically by GitHub Apps.

The merger App needs Checks read, Pull requests write, and Contents write permissions. Checks read is required because the merge gate validates the exact head SHA against CI and reviewer check runs before calling the merge API. The merger App does not create patch branches or commits.

## Main branch ruleset

Protect `main` with a repository ruleset that requires pull requests and blocks direct pushes. Require these checks before merge:

- `verify (3.11)`
- `verify (3.12)`
- `verify (3.13)`
- `CodeQL`

Do not grant the producer App bypass permission. If a bypass actor is required for the ruleset, restrict it to the merger App.

## Reviewer Apps

The merger also requires at least one trusted reviewer App to submit a review against the exact PR head SHA. The workflow currently recognizes Sourcery, CodeRabbit, and Gitar reviewer identities.

A provider is not required merely because it is installed. This avoids making publication availability depend on one vendor's billing or review quota. A trusted review that reports a positive numeric issue count blocks merge, as do active change requests and unresolved inline review threads.

## Runtime contract

- One generated patch branch uses the `bot/observatory-patch/` prefix
- One generated patch PR contains exactly one commit
- Only one generated patch PR may be open at a time, even when the repository has more than 100 open PRs
- Required CI and CodeQL checks must succeed on the exact head SHA
- At least one trusted reviewer App must review that exact head SHA
- Any active `CHANGES_REQUESTED` review blocks merge
- Any unresolved review thread blocks merge, including threads beyond the first GraphQL page
- The merger re-reads the PR immediately before merging and passes the exact reviewed head SHA to GitHub
- Producer workflows have read-only `GITHUB_TOKEN` permissions and use the producer App token only for patch branch and PR creation

The workflows intentionally fail closed when either App credential pair is missing.
