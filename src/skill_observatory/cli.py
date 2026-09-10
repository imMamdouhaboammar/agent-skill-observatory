from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import typer
import uvicorn

from .catalog import catalog_stats, export_catalog
from .config import Settings
from .db import init_database, make_session_factory
from .domain import RepositorySignals
from .github import GitHubClient
from .github_publisher import GitHubAtomicPublisher, GitHubPublisherError
from .local_git_publisher import LocalGitAtomicPublisher, publish_local_materialized_views
from .migrations import upgrade_database
from .parser import parse_skill_directory
from .pipeline import refresh_catalog
from .publication import PublicationReport, publish_pending_events
from .publishing import publish_catalog
from .scoring import score_skill
from .security import assess_skill_security

app = typer.Typer(
    no_args_is_help=True,
    help="Discover, validate, score and publish open Agent Skills.",
)


def _settings(database_url: str | None = None) -> Settings:
    base = Settings()
    return Settings(database_url=database_url or base.database_url)


@app.command("init-db")
def init_db(
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
) -> None:
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
def scan_local(
    path: Path = typer.Argument(..., exists=True, file_okay=False, readable=True),
) -> None:
    parsed = parse_skill_directory(path)
    security = assess_skill_security(parsed)
    now = datetime.now(UTC)
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
    max_repositories: int | None = typer.Option(
        None, min=1, help="Bound the number of candidate repos."
    ),
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


@app.command("publish-events")
def publish_events_command(
    repository: str = typer.Option(..., help="Target GitHub repository in owner/repo form."),
    branch: str = typer.Option("main", help="Target branch for fast-forward publication."),
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
    checkout_root: Path = typer.Option(
        Path("."), exists=True, file_okay=False, help="Fresh checkout containing canonical records."
    ),
    max_events: int = typer.Option(100, min=1, help="Maximum Skill events to attempt."),
    time_budget_seconds: int = typer.Option(
        420, min=1, help="Maximum publication wall-clock budget in seconds."
    ),
) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    factory = make_session_factory(settings.database_url)
    publisher: GitHubAtomicPublisher | None = None
    try:
        publisher = GitHubAtomicPublisher(
            token=settings.github_token,
            api_url=settings.github_api_url,
            timeout_seconds=settings.request_timeout_seconds,
        )
        with factory() as session:
            report = publish_pending_events(
                session,
                publisher,
                checkout_root=checkout_root,
                repository=repository,
                branch=branch,
                max_events=max_events,
                time_budget_seconds=time_budget_seconds,
            )
    except GitHubPublisherError as exc:
        report = PublicationReport(failures=[str(exc)], global_failure=True)
    finally:
        if publisher is not None:
            publisher.close()

    typer.echo(report.model_dump_json(indent=2))
    if report.global_failure:
        raise typer.Exit(code=1)


@app.command("publish-events-local")
def publish_events_local_command(
    repository: str = typer.Option(..., help="Target GitHub repository in owner/repo form."),
    branch: str = typer.Option("main", help="Checked-out branch for bootstrap publication."),
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
    checkout_root: Path = typer.Option(
        Path("."), exists=True, file_okay=False, help="Local Git checkout containing canonical records."
    ),
    max_events: int = typer.Option(500, min=1, help="Maximum Skill events to attempt."),
    time_budget_seconds: int = typer.Option(
        2400, min=1, help="Maximum publication wall-clock budget in seconds."
    ),
) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    factory = make_session_factory(settings.database_url)
    publisher = LocalGitAtomicPublisher(checkout_root=checkout_root)
    try:
        with factory() as session:
            report = publish_pending_events(
                session,
                publisher,
                checkout_root=checkout_root,
                repository=repository,
                branch=branch,
                max_events=max_events,
                time_budget_seconds=time_budget_seconds,
                aggregate_publish=publish_local_materialized_views,
            )
    except GitHubPublisherError as exc:
        report = PublicationReport(failures=[str(exc)], global_failure=True)

    typer.echo(report.model_dump_json(indent=2))
    if report.global_failure:
        raise typer.Exit(code=1)


@app.command("publish")
def publish_command(
    data_dir: Path = typer.Option(Path("data"), help="Directory for generated catalog data."),
    readme: Path = typer.Option(Path("README.md"), help="README file to update."),
    awesome: Path = typer.Option(Path("AWESOME.md"), help="Generated Awesome catalog path."),
    awesome_directory: Path = typer.Option(
        Path("awesome/README.md"), help="GitHub Awesome directory README."
    ),
    database_url: str | None = typer.Option(None, help="SQLAlchemy database URL."),
) -> None:
    settings = _settings(database_url)
    init_database(settings.database_url)
    factory = make_session_factory(settings.database_url)
    with factory() as session:
        stats = publish_catalog(
            session,
            data_dir=data_dir,
            readme_path=readme,
            awesome_path=awesome,
            awesome_directory_path=awesome_directory,
        )
    typer.echo(json.dumps(stats, indent=2))


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


if __name__ == "__main__":
    app()
