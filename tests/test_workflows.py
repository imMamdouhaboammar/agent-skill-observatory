from pathlib import Path

import yaml


def load_workflow(name: str) -> dict:
    return yaml.safe_load(Path(f".github/workflows/{name}").read_text(encoding="utf-8"))


def test_refresh_runs_every_fifteen_minutes_and_publishes_all_surfaces() -> None:
    workflow = load_workflow("refresh.yml")
    triggers = workflow.get("on") or workflow[True]
    schedules = triggers["schedule"]
    assert schedules == [{"cron": "7,22,37,52 * * * *"}]
    assert triggers["push"]["branches"] == ["main"]
    assert "src/skill_observatory/**" in triggers["push"]["paths"]
    text = Path(".github/workflows/refresh.yml").read_text(encoding="utf-8")
    assert "skillobs publish" in text
    for path in [
        "README.md",
        "AWESOME.md",
        "awesome/README.md",
        "data/repositories.json",
        "data/refresh.json",
    ]:
        assert path in text
