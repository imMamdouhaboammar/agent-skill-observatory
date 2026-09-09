from sqlalchemy import inspect

from skill_observatory.db import make_engine
from skill_observatory.migrations import upgrade_database


def test_initial_migration_creates_catalog_tables(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'migration.db'}"
    upgrade_database(url)
    engine = make_engine(url)
    try:
        names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert {"skills", "repository_snapshots", "alembic_version"}.issubset(names)
