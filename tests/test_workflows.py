from pathlib import Path

import yaml


def load_workflow(name: str) -> dict:
    return yaml.safe_load(Path(f".github/workflows/{name}").read_text(encoding="utf-8"))


def test_refresh_runs_every_fifteen_minutes_with_atomic_publication() -> None:
    workflow = load_workflow("refresh.yml")
    triggers = workflow.get("on") or workflow[True]
    assert triggers["schedule"] == [{"cron": "7,22,37,52 * * * *"}]
    assert triggers["push"]["branches"] == ["main"]
    assert "src/skill_observatory/**" in triggers["push"]["paths"]
    assert workflow["concurrency"]["group"] == "atomic-skill-publication"
    assert workflow["concurrency"]["cancel-in-progress"] is False

    text = Path(".github/workflows/refresh.yml").read_text(encoding="utf-8")
    assert "skillobs refresh" in text
    assert "skillobs publish-events" in text
    assert "--max-events 100" in text
    assert "--time-budget-seconds 420" in text
    assert "SKILLOBS_GITHUB_TOKEN" in text
    assert "Repositories scanned" in text
    assert "Skills observed" in text
    assert "git push --force" not in text
    assert "force: true" not in text
    assert "git add \\\n            README.md AWESOME.md" not in text


def test_bootstrap_is_manual_only_and_uses_larger_defaults() -> None:
    workflow = load_workflow("bootstrap-catalog.yml")
    triggers = workflow.get("on") or workflow[True]
    assert set(triggers) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["max_repositories"]["default"] == "100"
    assert inputs["max_events"]["default"] == "500"
    assert inputs["time_budget_seconds"]["default"] == "2400"
    assert workflow["concurrency"]["group"] == "atomic-skill-publication"
    assert workflow["concurrency"]["cancel-in-progress"] is False

    text = Path(".github/workflows/bootstrap-catalog.yml").read_text(encoding="utf-8")
    assert "skillobs publish-events" in text
    assert "--max-events \"$MAX_EVENTS\"" in text
    assert "--time-budget-seconds \"$TIME_BUDGET\"" in text
    assert "Repositories scanned" in text
    assert "Skills observed" in text
    assert "git push --force" not in text
    assert "force: true" not in text


def test_publication_workflows_do_not_use_legacy_snapshot_push() -> None:
    for name in ["refresh.yml", "bootstrap-catalog.yml"]:
        text = Path(f".github/workflows/{name}").read_text(encoding="utf-8")
        assert "git push" not in text
        assert "skillobs publish --" not in text
        assert "git add README.md AWESOME.md" not in text


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
