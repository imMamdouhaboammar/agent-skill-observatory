from pathlib import Path

import yaml


def load_workflow(name: str) -> dict:
    return yaml.safe_load(Path(f".github/workflows/{name}").read_text(encoding="utf-8"))


def test_refresh_runs_every_fifteen_minutes_and_proposes_one_pr_patch() -> None:
    workflow = load_workflow("refresh.yml")
    triggers = workflow.get("on") or workflow[True]
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] == [{"cron": "*/15 * * * *"}]
    assert workflow["concurrency"]["group"] == "atomic-skill-publication"
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert workflow["jobs"]["refresh"]["timeout-minutes"] < 15
    assert workflow["permissions"]["contents"] == "read"

    text = Path(".github/workflows/refresh.yml").read_text(encoding="utf-8")
    assert "skillobs refresh" in text
    assert "actions/create-github-app-token@v2" in text
    assert "PATCH_PRODUCER_APP_ID" in text
    assert "PATCH_PRODUCER_PRIVATE_KEY" in text
    assert "python -m skill_observatory.pr_publication_cli" in text
    assert "--max-events 1" in text
    assert "SKILLOBS_GITHUB_TOKEN: ${{ steps.producer-token.outputs.token }}" in text
    assert "git push" not in text
    assert "refs/heads/main" not in text
    assert "contents: write" not in text


def test_bootstrap_is_manual_only_and_cannot_push_main() -> None:
    workflow = load_workflow("bootstrap-catalog.yml")
    triggers = workflow.get("on") or workflow[True]
    assert set(triggers) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["max_repositories"]["default"] == "100"
    assert inputs["max_events"]["default"] == "1"
    assert inputs["time_budget_seconds"]["default"] == "2400"
    assert inputs["skip_scan"]["type"] == "boolean"
    assert inputs["skip_scan"]["default"] is False
    assert workflow["concurrency"]["group"] == "atomic-skill-publication"
    assert workflow["permissions"]["contents"] == "read"

    steps = workflow["jobs"]["bootstrap"]["steps"]
    checkout = steps[0]
    scan_step = next(step for step in steps if step.get("name") == "Scan bootstrap candidate set")
    cache_guard = next(
        step
        for step in steps
        if step.get("name") == "Require cached observations for publish-only bootstrap"
    )
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["ref"] == "main"
    assert scan_step["if"] == "${{ !inputs.skip_scan }}"
    assert cache_guard["if"] == "${{ inputs.skip_scan }}"

    text = Path(".github/workflows/bootstrap-catalog.yml").read_text(encoding="utf-8")
    assert "skip_scan requires a restored observation database cache" in text
    assert "actions/create-github-app-token@v2" in text
    assert "PATCH_PRODUCER_APP_ID" in text
    assert "PATCH_PRODUCER_PRIVATE_KEY" in text
    assert "python -m skill_observatory.pr_publication_cli" in text
    assert "--max-events 1" in text
    assert "git push" not in text
    assert "publish-events-local" not in text
    assert "contents: write" not in text


def test_merge_bot_requires_reviewed_atomic_generated_patch() -> None:
    workflow = load_workflow("merge-bot-patches.yml")
    triggers = workflow.get("on") or workflow[True]
    assert set(triggers) == {
        "check_suite",
        "pull_request_review",
        "schedule",
        "workflow_dispatch",
    }
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["permissions"]["checks"] == "read"
    assert workflow["permissions"]["pull-requests"] == "read"

    text = Path(".github/workflows/merge-bot-patches.yml").read_text(encoding="utf-8")
    assert "PATCH_MERGER_APP_ID" in text
    assert "PATCH_MERGER_PRIVATE_KEY" in text
    assert "bot/observatory-patch/" in text
    assert "pr.commits !== 1" in text
    assert "verify (3.11)" in text
    assert "verify (3.12)" in text
    assert "verify (3.13)" in text
    assert "CodeQL" in text
    assert "TRUSTED_REVIEWER_APPS" in text
    assert "sourcery-ai[bot]" in text
    assert "coderabbitai[bot]" in text
    assert "gitar-bot[bot]" in text
    assert "review.commit_id === reviewedSha" in text
    assert "Waiting for a trusted reviewer App to review the exact head SHA" in text
    assert "CHANGES_REQUESTED" in text
    assert "github.paginate(github.rest.checks.listForRef" in text
    assert "github.paginate(github.rest.pulls.listReviews" in text
    assert "github.paginate(github.rest.pulls.list" in text
    assert "reviewThreads(first:100, after:$after)" in text
    assert "pageInfo { hasNextPage endCursor }" in text
    assert "!connection.pageInfo.hasNextPage" in text
    assert "!thread.isResolved" in text
    assert "fresh.head.sha !== reviewedSha" in text
    assert "sha: reviewedSha" in text
    assert "merge_method: 'squash'" in text


def test_canary_dispatch_preserves_api_budget_for_publication() -> None:
    text = Path(".github/workflows/bootstrap-canary-dispatch.yml").read_text(encoding="utf-8")
    assert "-f max_events=25" in text
    assert "-f time_budget_seconds=2400" in text
    assert "-f skip_scan=true" in text


def test_publication_workflows_avoid_all_direct_main_writes() -> None:
    for name in ["refresh.yml", "bootstrap-catalog.yml"]:
        text = Path(f".github/workflows/{name}").read_text(encoding="utf-8")
        assert "git push" not in text
        assert "contents: write" not in text
        assert "skillobs publish --" not in text
        assert "publish-events-local" not in text


def test_ci_runs_full_static_gate() -> None:
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python -m ruff check ." in text
    assert "python -m mypy src" in text
    assert "python -m compileall -q src" in text
    assert "alembic check" in text
    assert "--cov-fail-under=80" in text


def test_pages_deploys_after_refresh() -> None:
    workflow = load_workflow("pages.yml")
    triggers = workflow.get("on") or workflow[True]
    assert triggers["workflow_run"]["workflows"] == ["Refresh catalog"]
    text = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "github.event.workflow_run.conclusion == 'success'" in text
