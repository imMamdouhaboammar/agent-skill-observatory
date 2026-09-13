# PR-gated atomic publication

Agent Skill Observatory publishes generated catalog changes through reviewed pull requests. Scheduled publication and the manual bootstrap entry point do not write directly to `main`.

## Delivery contract

Each generated patch follows one path:

1. `Refresh catalog` scans repositories and restores the observation database.
2. The producer paginates the complete open-PR set targeting `main`, considers only same-repository `bot/patch/*` heads, and treats a PR as queue-owned only after one-commit shape, Mamdouh attribution, provenance trailers, GitHub verification, and exact `PATCH_SIGNING_PUBLIC_KEY` verification pass.
3. If the existing trusted generated PR is based on an older `main`, it is marked as a stale-base close and its branch is retired so the same semantic patch can be rebuilt safely.
4. `skillobs publish-events-local --max-events 1` generates one Skill event plus its materialized catalog changes locally.
5. The generated local commits are collapsed into exactly one final commit.
6. That commit is authored and committed with the configured GitHub-linked Mamdouh identity and signed with the dedicated SSH signing key.
7. The patch ID is derived only from stable semantic event metadata: skill key, event type, source and analysis fingerprints, scores, and categories. Volatile publication timestamps and the current base SHA do not change the identity of the same logical patch.
8. The producer pushes only `bot/patch/<patch-id>` and opens a PR against `main`.
9. CI and configured review Apps publish checks against the exact PR head SHA.
10. The separate Merge Bot verifies the exact commit, expected SSH key, server-side ruleset, release checks, review-App checks, active review vetoes, and review-thread state.
11. The Merge Bot uses a normal merge commit, preserving the original signed patch commit unchanged as an ancestor of `main`.

The queue is intentionally serial: at most one cryptographically trusted generated patch PR may be open at a time. A same-repository PR that merely uses the reserved branch prefix cannot stall the queue unless it also satisfies the producer identity and signing contract.

## GitHub profile attribution

Future generated patch commits are designed to appear as contributions for `imMamdouhaboammar` when GitHub's normal contribution rules are satisfied.

Default commit identity:

```text
Name: Mamdouh Aboammar
Login: imMamdouhaboammar
Email: 58908124+imMamdouhaboammar@users.noreply.github.com
```

The producer sets both author and committer to that GitHub-linked noreply address. The Merge Bot refuses a generated patch if GitHub does not map the author to `imMamdouhaboammar` or if either email differs.

For the contribution graph, the authored patch commit must become reachable from the repository's default branch. The Merge Bot therefore uses a normal merge commit rather than squash or rebase. Squash or rebase would replace the original signed commit object.

## Verified SSH signatures

Create a dedicated Ed25519 key pair for publication automation. Register the public half on the `imMamdouhaboammar` GitHub account as an SSH signing key.

Store:

- private key in Actions secret `PATCH_SIGNING_PRIVATE_KEY`
- public key in repository variable `PATCH_SIGNING_PUBLIC_KEY`

The producer derives the public key from the private secret and requires an exact normalized match with `PATCH_SIGNING_PUBLIC_KEY` before signing. It creates the final commit with Git SSH signing enabled and runs `git verify-commit` before pushing.

Both the producer queue reconciler and Merge Bot independently require GitHub to expose a Verified signature and signed payload, then verify that payload with `ssh-keygen -Y verify` against the configured public key and expected author email.

Do not reuse a workstation authentication key for this automation.

## Producer GitHub App

Use a dedicated Producer App with only the permissions needed to create patch branches and pull requests:

- Contents: Read and write
- Pull requests: Read and write
- Metadata: Read

Required Actions secrets:

- `PATCH_PRODUCER_APP_ID`
- `PATCH_PRODUCER_PRIVATE_KEY`

The workflow's ordinary `GITHUB_TOKEN` remains read-only for repository content.

## Merge GitHub App

Use a different App for merging:

- Administration: Read
- Contents: Read and write
- Pull requests: Read and write
- Checks: Read
- Commit statuses: Read
- Metadata: Read

Required Actions secrets:

- `MERGE_BOT_APP_ID`
- `MERGE_BOT_PRIVATE_KEY`

The Merge App does not create publication patches.

## Review Apps are app-pinned required checks

The security-critical review verdict is a GitHub check produced by a specific review App, not a pull-request approval identity inferred client-side. This lets the repository ruleset enforce the review App identity atomically at merge time.

Configure `REQUIRED_REVIEW_CHECKS` as comma-separated `check-name@app-id` values. The default is:

```text
Gitar@827041
```

Every configured review check must finish with `success` on the current patch SHA. `neutral` and `skipped` are not accepted for a required review-App verdict.

Release checks are pinned to GitHub Actions App ID `15368` by default:

```text
verify (3.11)
verify (3.12)
verify (3.13)
analyze
dependency-review
skills-lint
autopilot
```

Every required release check must also finish with `success`. The dependency-review workflow fails closed when the dependency graph is unavailable, and repository skill lint no longer masks a real lint failure with `continue-on-error`.

If a different review App becomes authoritative, add its exact check name and GitHub App ID to `REQUIRED_REVIEW_CHECKS` and to the repository ruleset.

Pull-request review submissions remain a supplemental human veto. The Merge Bot computes the latest decisive state per reviewer, ignores later COMMENTED/PENDING noise, removes dismissed states, and refuses to merge while any active `CHANGES_REQUESTED` state exists. It repeats that veto check immediately before the merge call. The server-atomic review authorization boundary remains the app-pinned required checks, not PR-review identity matching.

A repository may additionally require one or more approving PR reviews in its ruleset. That is a stronger optional policy, not a substitute for `REQUIRED_REVIEW_CHECKS`.

## Latest-check semantics

GitHub may retain historical attempts for a check on the same SHA. The Merge Bot evaluates only the newest check run for each `(check name, GitHub App ID)` pair.

The Merge Bot's own `merge-gate@15368` check is excluded from its general check verdict so a previous fail-closed attempt cannot poison a later valid retry.

## Stale patch reconciliation and deliberate rejection

A generated PR contains exactly one commit whose only parent must be the current `main` SHA.

If `main` advances while a generated PR is waiting for review, both producer reconciliation and Merge Bot reconciliation detect the stale parent. They close the PR with the machine-readable marker:

```text
<!-- skillobs-close-reason: stale-base -->
```

and retire the stale branch. A later producer run regenerates the same semantic patch on the new base as one newly signed commit. Because the patch ID is semantic rather than timestamp- or base-derived, the producer can distinguish a stale automatic close from a human rejection. It recreates or reopens only stale-base closures.

If a generated PR is deliberately closed without the stale-base marker, future scheduled runs suppress that same semantic patch rather than silently recreating it. A changed semantic event receives a different patch ID and can open a new PR.

Fork PRs never participate in this queue. The producer also ignores same-repository reserved-prefix PRs that fail the exact one-commit, attribution, provenance, or signing-key checks.

## Required main ruleset

Create an active branch ruleset named `Agent Skill Publication Gate` for the default branch.

It must:

- have no bypass actors, including Producer and Merge Apps
- require pull requests
- require review-thread resolution
- dismiss stale reviews on push
- require strict/up-to-date status checks
- require every release check above with GitHub Actions App ID `15368`
- require every configured review-App check with its exact GitHub App ID
- allow **only** normal merge commits for publication PRs; squash and rebase must not be server-permitted alternatives
- not require linear history
- block force pushes and branch deletion where appropriate

The Merge Bot evaluates the ruleset's include and exclude ref patterns against `refs/heads/main`, including wildcard patterns, before trusting it. It reads and revalidates the policy immediately before merge and refuses to proceed if the contract is missing or weaker than expected.

## Bootstrap entry point

`.github/workflows/bootstrap-catalog.yml` is only a manual compatibility shim. It dispatches `Refresh catalog` and performs no catalog generation or direct `main` write itself.

There is one publication implementation and one signing path. This avoids maintaining a privileged bootstrap exception that would conflict with the no-bypass ruleset.

## Repository variables

Required:

- `PATCH_SIGNING_PUBLIC_KEY`

Optional overrides:

- `PATCH_AUTHOR_NAME`, default `Mamdouh Aboammar`
- `PATCH_AUTHOR_EMAIL`, default `58908124+imMamdouhaboammar@users.noreply.github.com`
- `PATCH_AUTHOR_LOGIN`, default `imMamdouhaboammar`
- `REQUIRED_REVIEW_CHECKS`, default `Gitar@827041`
- `PUBLICATION_RULESET_NAME`, default `Agent Skill Publication Gate`
- `REQUIRED_CHECK_INTEGRATION_ID`, default `15368`

## Fail-closed rollout

Publication stops instead of producing an unsigned or weakly reviewed patch when any required App credential, signing key, public key, release check, review check, or ruleset requirement is missing.

The bootstrap PR that introduces these workflows is a one-time exception because the Merge Bot does not exist on `main` yet. Merge that bootstrap PR only after its current diff has passed repository checks and review. Then configure the Apps, signing key, Actions secrets/variables, and ruleset before expecting generated publication PRs to complete end to end.
