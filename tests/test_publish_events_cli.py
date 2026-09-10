import json
from pathlib import Path

from typer.testing import CliRunner

import skill_observatory.cli as cli
from skill_observatory.publication import PublicationReport

runner = CliRunner()


class FakeAtomicPublisher:
    token_seen: str | None = None

    def __init__(self, *, token: str, api_url: str, timeout_seconds: float) -> None:
        type(self).token_seen = token

    def close(self) -> None:
        return None


class FakeLocalAtomicPublisher:
    checkout_root_seen: Path | None = None

    def __init__(self, *, checkout_root: Path) -> None:
        type(self).checkout_root_seen = checkout_root


def test_publish_events_cli_defaults_and_deferred_success(monkeypatch, tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'cli.db'}"
    captured: dict[str, object] = {}

    def fake_publish(session, publisher, **kwargs):
        captured.update(kwargs)
        return PublicationReport(
            events_detected=2,
            events_deferred=1,
            adds=2,
            main_before="A",
            main_after="A",
        )

    monkeypatch.setenv("SKILLOBS_GITHUB_TOKEN", "secret-token")
    monkeypatch.setattr(cli, "GitHubAtomicPublisher", FakeAtomicPublisher)
    monkeypatch.setattr(cli, "publish_pending_events", fake_publish)

    result = runner.invoke(
        cli.app,
        [
            "publish-events",
            "--repository",
            "acme/observatory",
            "--database-url",
            db_url,
            "--checkout-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["events_deferred"] == 1
    assert captured["max_events"] == 100
    assert captured["time_budget_seconds"] == 420
    assert FakeAtomicPublisher.token_seen == "secret-token"


def test_publish_events_cli_returns_nonzero_for_global_failure(monkeypatch, tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'fatal.db'}"

    def fake_publish(session, publisher, **kwargs):
        return PublicationReport(
            failures=["GitHub authentication failed"],
            global_failure=True,
        )

    monkeypatch.setenv("SKILLOBS_GITHUB_TOKEN", "secret-token")
    monkeypatch.setattr(cli, "GitHubAtomicPublisher", FakeAtomicPublisher)
    monkeypatch.setattr(cli, "publish_pending_events", fake_publish)

    result = runner.invoke(
        cli.app,
        [
            "publish-events",
            "--repository",
            "acme/observatory",
            "--database-url",
            db_url,
            "--checkout-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["global_failure"] is True
    assert payload["failures"] == ["GitHub authentication failed"]


def test_publish_events_local_cli_uses_local_transport_without_token(monkeypatch, tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'local-cli.db'}"
    captured: dict[str, object] = {}

    def fake_publish(session, publisher, **kwargs):
        captured.update(kwargs)
        return PublicationReport(
            events_detected=500,
            events_published=500,
            main_before="A",
            main_after="B",
        )

    monkeypatch.delenv("SKILLOBS_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(cli, "LocalGitAtomicPublisher", FakeLocalAtomicPublisher, raising=False)
    monkeypatch.setattr(cli, "publish_pending_events", fake_publish)

    result = runner.invoke(
        cli.app,
        [
            "publish-events-local",
            "--repository",
            "acme/observatory",
            "--database-url",
            db_url,
            "--checkout-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["events_published"] == 500
    assert captured["max_events"] == 500
    assert captured["time_budget_seconds"] == 2400
    assert getattr(captured["aggregate_publish"], "__name__") == "publish_local_materialized_views"
    assert FakeLocalAtomicPublisher.checkout_root_seen == tmp_path
