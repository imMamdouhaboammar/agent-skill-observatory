from pathlib import Path

import yaml


def load_workflow(name: str) -> dict:
    return yaml.safe_load(Path(f".github/workflows/{name}").read_text(encoding="utf-8"))


def test_refresh_runs_every_fifteen_minutes_and_supports_manual_dispatch() -> None:
    workflow = load_workflow("refresh.yml")
    triggers = workflow.get("on") or workflow[True]
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] == [{"cron": "*/15 * * * *"}]
    assert workflow["concurrency"]["group"] == "atomic-skill-publication"
    assert workflow["concurrency"]["cancel-in-progress"] is False
    assert workflow["jobs"]["refresh"]["timeout-minutes"] < 15

    text = Path(".github/workflows/refresh.yml").read_text(encoding="utf-8")
    assert "skillobs refresh" in text
    assert "skillobs publish-events-local" in text
    assert "--max-events 1" in text
    assert "--time-budget-seconds 420" in text
    assert "SKILLOBS_GITHUB_TOKEN" in text
    assert "Repositories scanned" in text
    assert "Skills observed" in text
    assert 'PATCH_BRANCH="bot/patch/${PATCH_ID}"' in text
    assert 'git push origin "HEAD:refs/heads/$PATCH_BRANCH"' in text
    assert "gh pr create" in text
    assert "git push origin HEAD:main" not in text
    assert "git push origin main" not in text
    assert "git push --force" not in text
    assert "force: true" not in text


def test_bootstrap_is_manual_pr_gated_dispatch_shim() -> None:
    workflow = load_workflow("bootstrap-catalog.yml")
    triggers = workflow.get("on") or workflow[True]
    assert set(triggers) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"max_repositories"}
    assert inputs["max_repositories"]["default"] == "100"
    assert workflow["permissions"] == {"actions": "write", "contents": "read"}
    assert workflow["jobs"]["bootstrap"]["timeout-minutes"] == 5

    text = Path(".github/workflows/bootstrap-catalog.yml").read_text(encoding="utf-8")
    assert "gh workflow run refresh.yml" in text
    assert '-f max_repositories="$MAX_REPOSITORIES"' in text
    assert "Direct writes to `main`: **disabled**" in text
    assert "skillobs publish-events-local" not in text
    assert "git push" not in text
    assert "contents: write" not in text


def test_canary_dispatch_uses_pr_gated_bootstrap_contract() -> None:
    text = Path(".github/workflows/bootstrap-canary-dispatch.yml").read_text(encoding="utf-8")
    assert "gh workflow run bootstrap-catalog.yml" in text
    assert "-f max_repositories=100" in text
    assert "max_events" not in text
    assert "time_budget_seconds" not in text
    assert "skip_scan" not in text


def test_publication_workflows_have_no_direct_main_push() -> None:
    refresh = Path(".github/workflows/refresh.yml").read_text(encoding="utf-8")
    bootstrap = Path(".github/workflows/bootstrap-catalog.yml").read_text(encoding="utf-8")

    assert 'git push origin "HEAD:refs/heads/$PATCH_BRANCH"' in refresh
    assert "git push origin HEAD:main" not in refresh
    assert "git push origin main" not in refresh
    assert "skillobs publish-events \\" not in refresh
    assert "skillobs publish --" not in refresh
    assert "gh pr create" in refresh

    assert "git push" not in bootstrap
    assert "skillobs publish-events-local" not in bootstrap
    assert "gh workflow run refresh.yml" in bootstrap


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
