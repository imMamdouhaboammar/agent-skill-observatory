import json

from typer.testing import CliRunner

from skill_observatory.cli import app

runner = CliRunner()


def test_scan_local_command() -> None:
    result = runner.invoke(app, ["scan-local", "tests/fixtures/sample-skill"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["name"] == "sample-skill"
    assert payload["spec"]["valid"] is True


def test_init_stats_doctor_and_build_site(tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'cli.db'}"
    init_result = runner.invoke(app, ["init-db", "--database-url", db_url])
    assert init_result.exit_code == 0

    stats_path = tmp_path / "stats.json"
    stats_result = runner.invoke(
        app,
        ["stats", "--database-url", db_url, "--output", str(stats_path)],
    )
    assert stats_result.exit_code == 0
    assert json.loads(stats_path.read_text())["skills"] == 0

    doctor_result = runner.invoke(app, ["doctor", "--database-url", db_url])
    assert doctor_result.exit_code == 0
    assert "security model: static scan only" in doctor_result.output

    site_dir = tmp_path / "site"
    site_result = runner.invoke(
        app,
        ["build-site", "--database-url", db_url, "--output-dir", str(site_dir)],
    )
    assert site_result.exit_code == 0
    assert (site_dir / "index.html").exists()
    assert json.loads((site_dir / "catalog.json").read_text()) == []
