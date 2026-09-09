from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import typer
import uvicorn
from sqlalchemy.orm import Session

from .catalog import catalog_stats, export_catalog
from .config import Settings
from .db import init_database, make_session_factory
from .domain import RepositorySignals
from .github import GitHubClient
from .migrations import upgrade_database
from .parser import parse_skill_directory
from .pipeline import refresh_catalog
from .scoring import score_skill
from .security import assess_skill_security

app = typer.Typer(no_args_is_help=True, help="Discover, validate, score and publish open Agent Skills.")


def _settings(database_url: str | None = None) -> Settings:
    base = Settings()
    return Settings(database_url=database_url or base.database_url)


@app.command("init-db")
def init_db(database_url: str | None = typer.Option(None, help="SQLAlchemy database URL.")) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    typer.echo(f"Initialized {settings.database_url}")


@app.command()
def migrate(
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
    revision: str = typer.Option("head", help="Alembic revision to upgrade to."),
) -> None:
    settings = _settings(database_url)
    upgrade_database(settings.database_url, revision)
    typer.echo(f"Migrated {settings.database_url} to {revision}")


@app.command()
def scan_local(path: Path = typer.Argument(..., exists=True, file_okay=False, readable=True)) -> None:
    parsed = parse_skill_directory(path)
    security = assess_skill_security(parsed)
    now = datetime.now(timezone.utc)
    score = score_skill(
        spec=parsed.spec,
        security=security,
        repo=RepositorySignals(
            pushed_at=now,
            has_tests=(path / "tests").exists() or (path / "evals").exists(),
            has_readme=(path / "README.md").exists(),
        ),
        description_length=len(parsed.description),
        body_chars=len(parsed.body),
    )
    typer.echo(
        json.dumps(
            {
                "name": parsed.name,
                "spec": parsed.spec.model_dump(mode="json"),
                "security": security.model_dump(mode="json"),
                "score": score.model_dump(mode="json"),
                "resources": parsed.resource_counts.model_dump(mode="json"),
            },
            indent=2,
        )
    )


@app.command()
def refresh(
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
    max_repositories: int | None = typer.Option(None, min=1, help="Bound the number of candidate repos."),
) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    factory = make_session_factory(settings.database_url)
    with GitHubClient(settings) as client, factory() as session:
        report = refresh_catalog(client, session, max_repositories=max_repositories)
    typer.echo(json.dumps(report, indent=2))
    if report["errors"]:
        typer.echo(f"Completed with {len(report['errors'])} per-repository errors", err=True)


@app.command("export")
def export_command(
    output: Path = typer.Argument(...),
    format: str = typer.Option("json", help="json or csv"),
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    factory = make_session_factory(settings.database_url)
    with factory() as session:
        path = export_catalog(session, output, format=format)
    typer.echo(str(path))


@app.command("stats")
def stats_command(
    output: Path | None = typer.Option(None, help="Optional JSON output path."),
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    factory = make_session_factory(settings.database_url)
    with factory() as session:
        payload = catalog_stats(session)
    rendered = json.dumps(payload, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(str(output))
    else:
        typer.echo(rendered)


@app.command("build-site")
def build_site(
    output_dir: Path = typer.Option(Path("site"), help="Static site output directory."),
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    factory = make_session_factory(settings.database_url)
    source_web = Path(__file__).resolve().parent / "web"
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset in source_web.iterdir():
        if asset.is_file():
            shutil.copy2(asset, output_dir / asset.name)
    with factory() as session:
        export_catalog(session, output_dir / "catalog.json", format="json")
        (output_dir / "stats.json").write_text(
            json.dumps(catalog_stats(session), indent=2), encoding="utf-8"
        )
    typer.echo(str(output_dir))


@app.command()
def doctor(database_url: str | None = typer.Option(None, help="SQLAlchemy database URL.")) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    token_state = "configured" if settings.github_token else "not configured"
    typer.echo(f"database: ok ({settings.database_url})")
    typer.echo(f"github token: {token_state}")
    typer.echo("security model: static scan only; third-party scripts are never executed")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000, min=1, max=65535),
    reload: bool = typer.Option(False),
) -> None:
    uvicorn.run("skill_observatory.api:app", host=host, port=port, reload=reload)
