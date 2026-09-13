from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFRESH = ROOT / ".github" / "workflows" / "refresh.yml"
MERGE_BOT = ROOT / ".github" / "workflows" / "merge-bot.yml"
BOOTSTRAP = ROOT / ".github" / "workflows" / "bootstrap-catalog.yml"
DEPENDENCY_REVIEW = ROOT / ".github" / "workflows" / "dependency-review.yml"
SKILLS_LINT = ROOT / ".github" / "workflows" / "skills-lint.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_refresh_uses_pr_gated_atomic_patch_flow() -> None:
    workflow = _read(REFRESH)

    assert "PATCH_PRODUCER_APP_ID" in workflow
    assert "PATCH_PRODUCER_PRIVATE_KEY" in workflow
    assert "permissions:\n  contents: read\n  pull-requests: read" in workflow
    assert "skillobs publish-events-local" in workflow
    assert "--max-events 1" in workflow
    assert 'git reset --soft "$BASE_SHA"' in workflow
    assert 'COMMIT_COUNT="$(git rev-list --count "$BASE_SHA"..HEAD)"' in workflow
    assert 'PATCH_BRANCH="bot/patch/${PATCH_ID}"' in workflow
    assert 'git push origin "HEAD:refs/heads/$PATCH_BRANCH"' in workflow
    assert "gh pr create" in workflow


def test_privileged_actions_are_pinned_to_immutable_shas() -> None:
    refresh = _read(REFRESH)
    merge_bot = _read(MERGE_BOT)
    dependency_review = _read(DEPENDENCY_REVIEW)
    skills_lint = _read(SKILLS_LINT)

    create_token = "actions/create-github-app-token@fee1f7d63c2ff003460e3d139729b119787bc349"
    github_script = "actions/github-script@f28e40c7f34bde8b3046d885e986cb6290c5673b"
    checkout = "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
    setup_python = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
    cache = "actions/cache/restore@0057852bfaa89a56745cba8c7296529d2fc39830"
    cache_save = "actions/cache/save@0057852bfaa89a56745cba8c7296529d2fc39830"

    for action in (create_token, checkout, setup_python, cache, cache_save):
        assert action in refresh
    assert create_token in merge_bot
    assert github_script in merge_bot
    assert checkout in dependency_review
    assert checkout in skills_lint
    assert "actions/dependency-review-action@2031cfc080254a8a887f58cffee85186f0e49e48" in dependency_review
    assert "korya/avocetta@5f6f62668f0cfb4c49abc18206f8955765c2e54d" in skills_lint
    assert "actions/create-github-app-token@v2" not in refresh
    assert "actions/create-github-app-token@v2" not in merge_bot
    assert "actions/github-script@v7" not in merge_bot
    assert "actions/checkout@v4" not in dependency_review
    assert "actions/checkout@v4" not in skills_lint


def test_refresh_creates_key_bound_signed_commits_attributed_to_user() -> None:
    workflow = _read(REFRESH)

    assert "PATCH_SIGNING_PRIVATE_KEY" in workflow
    assert "PATCH_SIGNING_PUBLIC_KEY" in workflow
    assert "PATCH_AUTHOR_NAME" in workflow
    assert "Mamdouh Aboammar" in workflow
    assert "58908124+imMamdouhaboammar@users.noreply.github.com" in workflow
    assert "ssh-keygen -y" in workflow
    assert "Configured signing private key does not match PATCH_SIGNING_PUBLIC_KEY" in workflow
    assert "git config gpg.format ssh" in workflow
    assert 'git config user.signingkey "$SIGNING_KEY"' in workflow
    assert "git config commit.gpgsign true" in workflow
    assert "git commit -S" in workflow
    assert "git cat-file commit HEAD | grep -q '^gpgsig '" in workflow
    assert "git verify-commit HEAD" in workflow
    assert "refusing to create an unsigned publication commit" in workflow


def test_patch_id_uses_stable_semantic_event_metadata() -> None:
    workflow = _read(REFRESH)

    assert "EVENT_COMMIT_SHA" in workflow
    assert "EVENT_ID_INPUT" in workflow
    for field in (
        "Skill-Key",
        "Event",
        "Source-Fingerprint",
        "Analysis-Fingerprint",
        "Overall-Score",
        "Security-Score",
        "Categories",
    ):
        assert field in workflow
    assert 'PATCH_ID="$(printf \'%s\\n\' "$EVENT_ID_INPUT" | sha256sum | cut -c1-16)"' in workflow
    assert 'git diff --binary "$BASE_SHA" HEAD' not in workflow
    assert 'printf \'%s\\0\' "$BASE_SHA"' not in workflow


def test_refresh_does_not_use_remote_direct_main_publisher() -> None:
    workflow = _read(REFRESH)

    assert 'skillobs publish-events \\' not in workflow
    assert "git push origin main" not in workflow
    assert "git push origin HEAD:main" not in workflow


def test_refresh_queue_is_paginated_main_scoped_and_cryptographically_owned() -> None:
    workflow = _read(REFRESH)

    assert "gh api --paginate --slurp" in workflow
    assert '-f base=main' in workflow
    assert '.head.repo.full_name == $repo' in workflow
    assert '.head.ref | startswith(\"bot/patch/\")' in workflow
    assert "PATCH_AUTHOR_LOGIN" in workflow
    assert "PATCH_AUTHOR_EMAIL" in workflow
    assert "Generated-by: agent-skill-observatory" in workflow
    assert "Patch-ID: $PATCH_ID" in workflow
    assert "ssh-keygen -Y verify" in workflow
    assert "PATCH_SIGNING_PUBLIC_KEY" in workflow
    assert "Ignoring reserved-prefix PR" in workflow
    assert "Expected at most one cryptographically trusted publication PR" in workflow


def test_refresh_retires_stale_patch_and_respects_deliberate_close() -> None:
    workflow = _read(REFRESH)

    assert "CURRENT_MAIN_SHA" in workflow
    assert "PARENT_SHA" in workflow
    assert "skillobs-close-reason: stale-base" in workflow
    assert 'git push origin --delete "$PR_BRANCH" || true' in workflow
    assert "Semantic patch $PATCH_ID was deliberately closed; automatic recreation is suppressed." in workflow
    assert "Reopened stale-base PR" in workflow
    assert "suppressed=true" in workflow
    assert "blocked=false" in workflow


def test_bootstrap_has_no_independent_publication_path() -> None:
    workflow = _read(BOOTSTRAP)

    assert "gh workflow run refresh.yml" in workflow
    assert "skillobs publish-events-local" not in workflow
    assert "git push" not in workflow
    assert "PATCH_SIGNING_PRIVATE_KEY" not in workflow
    assert "contents: write" not in workflow


def test_release_gate_workflows_fail_closed() -> None:
    dependency_review = _read(DEPENDENCY_REVIEW)
    skills_lint = _read(SKILLS_LINT)

    assert "Dependency Review is a required release gate and must fail closed" in dependency_review
    assert 'if [ "$STATUS" != "200" ]' in dependency_review
    assert "exit 1" in dependency_review
    assert "available=false" not in dependency_review
    assert "continue-on-error" not in skills_lint


def test_merge_bot_uses_a_separate_app_identity_with_ruleset_read_access() -> None:
    workflow = _read(MERGE_BOT)

    assert "MERGE_BOT_APP_ID" in workflow
    assert "MERGE_BOT_PRIVATE_KEY" in workflow
    assert "permission-administration: read" in workflow
    assert "PATCH_PRODUCER_APP_ID" not in workflow
    assert "PATCH_PRODUCER_PRIVATE_KEY" not in workflow


def test_merge_bot_rechecks_every_release_workflow_that_can_finish_last() -> None:
    workflow = _read(MERGE_BOT)

    for name in (
        "CI",
        "CodeQL",
        "Dependency Review",
        "Agent Skills Lint",
        "ChatGPT & Codex Plugin Autopilot",
    ):
        assert f"      - {name}" in workflow


def test_merge_bot_has_periodic_reconciliation() -> None:
    workflow = _read(MERGE_BOT)

    assert "    - cron: '*/5 * * * *'" in workflow
    assert "github.event_name == 'schedule'" in workflow
    assert "state: 'open'" in workflow
    assert "pull.head?.repo?.full_name === `${owner}/${repo}`" in workflow
    assert "pull.head?.ref?.startsWith('bot/patch/')" in workflow
    assert "group: patch-merge-gate" in workflow


def test_merge_bot_requires_release_checks_from_github_actions_app() -> None:
    workflow = _read(MERGE_BOT)

    for name in (
        "verify (3.11)",
        "verify (3.12)",
        "verify (3.13)",
        "analyze",
        "dependency-review",
        "skills-lint",
        "autopilot",
    ):
        assert f"'{name}'" in workflow
    assert "REQUIRED_CHECK_INTEGRATION_ID" in workflow
    assert "'15368'" in workflow
    assert "releaseCheckSpecs" in workflow
    assert "integrationId: actionsIntegrationId" in workflow
    assert "Required release check must succeed" in workflow


def test_review_app_identity_is_enforced_as_server_required_check() -> None:
    workflow = _read(MERGE_BOT)

    assert "REQUIRED_REVIEW_CHECKS" in workflow
    assert "Gitar@827041" in workflow
    assert "check-name@app-id" in workflow
    assert "reviewCheckSpecs" in workflow
    assert "requiredCheckSpecs" in workflow
    assert "match.integration_id" in workflow
    assert "spec.integrationId" in workflow
    assert "Required review-app check must succeed" in workflow
    assert "REQUIRED_REVIEW_APPS" not in workflow


def test_merge_bot_rejects_active_change_requests_and_rechecks_before_merge() -> None:
    workflow = _read(MERGE_BOT)

    assert "github.rest.pulls.listReviews" in workflow
    assert "latestDecisiveByReviewer" in workflow
    assert "review.state === 'DISMISSED'" in workflow
    assert "review.state === 'APPROVED' || review.state === 'CHANGES_REQUESTED'" in workflow
    assert "Active CHANGES_REQUESTED review blocks merge" in workflow
    assert "A CHANGES_REQUESTED review appeared during gate evaluation" in workflow
    assert workflow.count("activeChangeRequests(pull_number)") >= 2


def test_merge_bot_requires_server_side_ruleset_without_bypass() -> None:
    workflow = _read(MERGE_BOT)

    assert "PUBLICATION_RULESET_NAME" in workflow
    assert "Agent Skill Publication Gate" in workflow
    assert "GET /repos/{owner}/{repo}/rulesets" in workflow
    assert "GET /repos/{owner}/{repo}/rulesets/{ruleset_id}" in workflow
    assert "ruleset.enforcement !== 'active'" in workflow
    assert "ruleset.bypass_actors || []" in workflow
    assert "must have no bypass actors" in workflow
    assert "strict_required_status_checks_policy !== true" in workflow
    assert "required_review_thread_resolution" in workflow
    assert "required_linear_history" in workflow
    assert "missingServerChecks" in workflow


def test_ruleset_patterns_are_evaluated_for_effective_main_coverage() -> None:
    workflow = _read(MERGE_BOT)

    assert "function refPatternMatches" in workflow
    assert "pattern === '~DEFAULT_BRANCH'" in workflow
    assert "pattern === '~ALL'" in workflow
    assert "targetsMain = includedRefs.some" in workflow
    assert "excludesMain = excludedRefs.some" in workflow
    assert "after include/exclude pattern evaluation" in workflow


def test_server_policy_preserves_merge_commit_strategy() -> None:
    workflow = _read(MERGE_BOT)

    assert "repository.allow_merge_commit !== true" in workflow
    assert "Allow merge commits must be enabled" in workflow
    assert "allowed_merge_methods" in workflow
    assert "allowedMergeMethods.length !== 1 || allowedMergeMethods[0] !== 'merge'" in workflow
    assert "must allow only the normal merge method" in workflow
    assert "cannot require linear history" in workflow


def test_merge_bot_enforces_atomicity_exact_sha_and_preserving_merge() -> None:
    workflow = _read(MERGE_BOT)

    assert "commits.length !== 1 || commits[0].sha !== headSha" in workflow
    assert "freshPr.head.sha !== headSha" in workflow
    assert "merge_method: 'merge'" in workflow
    assert "merge_method: 'squash'" not in workflow
    assert "sha: headSha" in workflow
    assert "signed authored commit" in workflow


def test_merge_bot_requires_verified_user_attribution_and_expected_signing_key() -> None:
    workflow = _read(MERGE_BOT)

    assert "EXPECTED_PATCH_AUTHOR_LOGIN" in workflow
    assert "EXPECTED_PATCH_AUTHOR_EMAIL" in workflow
    assert "EXPECTED_PATCH_SIGNING_PUBLIC_KEY" in workflow
    assert "headCommit.author?.login" in workflow
    assert "headCommit.commit.author?.email" in workflow
    assert "headCommit.commit.committer?.email" in workflow
    assert "verification?.verified" in workflow
    assert "verification.signature" in workflow
    assert "verification.payload" in workflow
    assert "ssh-keygen" in workflow
    assert "'-Y', 'verify'" in workflow
    assert "'-I', expectedEmail" in workflow
    assert "'-n', 'git'" in workflow
    assert "Signing-key gate failed" in workflow
    assert "Signature gate failed" in workflow
    assert "Attribution gate failed" in workflow


def test_merge_bot_closes_stale_atomic_patch_for_rebuild() -> None:
    workflow = _read(MERGE_BOT)

    assert "headCommit.parents?.length === 1" in workflow
    assert "parentSha !== mainRef.object.sha" in workflow
    assert "skillobs-close-reason: stale-base" in workflow
    assert "github.rest.pulls.update" in workflow
    assert "state: 'closed'" in workflow
    assert "github.rest.git.deleteRef" in workflow
    assert "freshMainRef.object.sha !== parentSha" in workflow


def test_merge_bot_uses_latest_check_per_name_and_app_and_ignores_self_history() -> None:
    workflow = _read(MERGE_BOT)

    assert "const latestChecks = new Map()" in workflow
    assert "checkKey(run.name, Number(run.app?.id || 0))" in workflow
    assert "run.id > previous.id" in workflow
    assert "checkKey('merge-gate', 15368)" in workflow
    assert "key !== selfCheckKey" in workflow
    assert "Latest check gate failed" in workflow


def test_merge_bot_blocks_unresolved_review_threads() -> None:
    workflow = _read(MERGE_BOT)

    assert "reviewThreads(first: 100)" in workflow
    assert "reviewThreads.nodes.some((thread) => !thread.isResolved)" in workflow
