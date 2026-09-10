from sqlalchemy import inspect

from skill_observatory.db import make_engine
from skill_observatory.migrations import upgrade_database


def test_initial_migration_creates_catalog_tables(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'migration.db'}"
    upgrade_database(url)
    engine = make_engine(url)
    try:
        inspector = inspect(engine)
        names = set(inspector.get_table_names())
        skill_columns = {column["name"] for column in inspector.get_columns("skills")}
    finally:
        engine.dispose()
    assert {"skills", "repository_snapshots", "alembic_version"}.issubset(names)
    assert {
        "source_fingerprint",
        "analysis_fingerprint",
        "consecutive_misses",
        "last_successful_repo_scan_at",
    }.issubset(skill_columns)
