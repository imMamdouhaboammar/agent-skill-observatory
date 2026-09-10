from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from skill_observatory.cli import app
from skill_observatory.db import init_database

runner = CliRunner()


def test_doctor_reports_database_and_security_state(tmp_path: Path) -> None:
    db_path = tmp_path / "doctor.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    result = runner.invoke(app, ["doctor", "--database-url", db_url])
    assert result.exit_code == 0
    assert "database: ok" in result.stdout
    assert "security model: static scan only" in result.stdout


def test_init_db_and_migrate_commands_initialize_schema(tmp_path: Path) -> None:
    db_init = tmp_path / "init.db"
    url_init = f"sqlite+pysqlite:///{db_init}"
    init_res = runner.invoke(app, ["init-db", "--database-url", url_init])
    assert init_res.exit_code == 0
    assert "Initialized" in init_res.stdout

    db_mig = tmp_path / "migrate.db"
    url_mig = f"sqlite+pysqlite:///{db_mig}"
    mig_res = runner.invoke(app, ["migrate", "--database-url", url_mig])
    assert mig_res.exit_code == 0
    assert "Migrated" in mig_res.stdout


def test_scan_local_evaluates_spec_and_security_signals() -> None:
    fixture = Path("tests/fixtures/sample-skill")
    result = runner.invoke(app, ["scan-local", str(fixture)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "sample-skill"
    assert payload["spec"]["valid"] is True
    assert payload["security"]["score"] == 100
    assert payload["resources"]["scripts"] == 1


def test_export_and_stats_commands_produce_expected_outputs(tmp_path: Path) -> None:
    db_path = tmp_path / "export.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    init_database(db_url)

    # Test stats command to stdout
    stats_res = runner.invoke(app, ["stats", "--database-url", db_url])
    assert stats_res.exit_code == 0
    stats_data = json.loads(stats_res.stdout)
    assert "skills" in stats_data
    assert "repositories" in stats_data

    # Test stats command to file
    stats_file = tmp_path / "stats.json"
    stats_file_res = runner.invoke(
        app, ["stats", "--output", str(stats_file), "--database-url", db_url]
    )
    assert stats_file_res.exit_code == 0
    assert stats_file.is_file()

    # Test export JSON
    json_out = tmp_path / "catalog.json"
    exp_json = runner.invoke(
        app, ["export", str(json_out), "--format", "json", "--database-url", db_url]
    )
    assert exp_json.exit_code == 0
    assert json_out.is_file()

    # Test export CSV
    csv_out = tmp_path / "catalog.csv"
    exp_csv = runner.invoke(
        app, ["export", str(csv_out), "--format", "csv", "--database-url", db_url]
    )
    assert exp_csv.exit_code == 0
    assert csv_out.is_file()


def test_build_site_copies_assets_and_exports_catalog(tmp_path: Path) -> None:
    db_path = tmp_path / "site.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    site_dir = tmp_path / "site"

    result = runner.invoke(
        app, ["build-site", "--output-dir", str(site_dir), "--database-url", db_url]
    )
    assert result.exit_code == 0
    assert (site_dir / "index.html").is_file()
    assert (site_dir / "styles.css").is_file()
    assert (site_dir / "app.js").is_file()
    assert (site_dir / "catalog.json").is_file()
    assert (site_dir / "stats.json").is_file()
