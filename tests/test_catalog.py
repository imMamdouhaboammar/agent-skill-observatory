import json
from datetime import UTC, datetime

from skill_observatory.catalog import (
    catalog_stats,
    export_catalog,
    records_as_dicts,
    repository_rollups,
)
from skill_observatory.db import init_database, make_session_factory
from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.repository import upsert_skill


def make_skill(
    name: str = "demo",
    *,
    repo_full_name: str = "example/repo",
    overall: int = 88,
    quality: int = 90,
    security: int = 95,
    stars: int = 100,
) -> IndexedSkill:
    now = datetime.now(UTC)
    return IndexedSkill(
        canonical_key=f"{repo_full_name}:skills/{name}",
        content_fingerprint=(name[0] * 64)[:64],
        repo_full_name=repo_full_name,
        repo_url=f"https://github.com/{repo_full_name}",
        repo_default_branch="main",
        path=f"skills/{name}",
        name=name,
        description=f"{name} skill for repository review",
        license="MIT",
        compatibility=None,
        metadata={},
        allowed_tools=[],
        spec=SpecValidation(valid=True),
        security=SecurityReport(score=security),
        score=ScoreBreakdown(
            overall=overall,
            quality=quality,
            security=security,
            maintenance=80,
            adoption=70,
        ),
        resources=ResourceCounts(scripts=1),
        stars=stars,
        forks=10,
        pushed_at=now,
        archived=False,
        discovery_source="test",
        indexed_at=now,
        evidence={"categories": ["engineering"]},
    )


def test_catalog_stats_and_exports(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'catalog.db'}"
    init_database(url)
    factory = make_session_factory(url)
    with factory() as session:
        upsert_skill(session, make_skill())
        stats = catalog_stats(session)
        json_path = export_catalog(session, tmp_path / "catalog.json", "json")
        csv_path = export_catalog(session, tmp_path / "catalog.csv", "csv")
    assert stats == {
        "skills": 1,
        "repositories": 1,
        "spec_valid": 1,
        "security_85_plus": 1,
        "score_80_plus": 1,
    }
    rows = json.loads(json_path.read_text())
    assert rows[0]["name"] == "demo"
    assert "overall_score" in csv_path.read_text()


def test_catalog_ordering_ignores_popularity_signals(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'ranking.db'}"
    init_database(url)
    factory = make_session_factory(url)
    with factory() as session:
        upsert_skill(
            session,
            make_skill("popular", overall=90, security=91, quality=99, stars=1_000_000),
        )
        upsert_skill(
            session,
            make_skill("alpha", overall=90, security=95, quality=95, stars=1),
        )
        upsert_skill(
            session,
            make_skill("beta", overall=90, security=95, quality=95, stars=999_999),
        )
        rows = records_as_dicts(session)

    assert [row["name"] for row in rows] == ["alpha", "beta", "popular"]


def test_repository_ordering_ignores_popularity_signals(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'repo-ranking.db'}"
    init_database(url)
    factory = make_session_factory(url)
    with factory() as session:
        upsert_skill(
            session,
            make_skill(
                "popular",
                repo_full_name="zeta/popular",
                overall=90,
                stars=1_000_000,
            ),
        )
        upsert_skill(
            session,
            make_skill(
                "quiet",
                repo_full_name="alpha/quiet",
                overall=90,
                stars=1,
            ),
        )
        repos = repository_rollups(session)

    assert [repo["repo_full_name"] for repo in repos] == ["alpha/quiet", "zeta/popular"]


def test_nested_repository_skill_order_uses_quality_not_stars(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'nested-ranking.db'}"
    init_database(url)
    factory = make_session_factory(url)
    with factory() as session:
        upsert_skill(
            session,
            make_skill(
                "popular",
                repo_full_name="example/repo",
                overall=90,
                security=95,
                quality=80,
                stars=1_000_000,
            ),
        )
        upsert_skill(
            session,
            make_skill(
                "quiet",
                repo_full_name="example/repo",
                overall=90,
                security=99,
                quality=99,
                stars=1,
            ),
        )
        repos = repository_rollups(session)

    assert [skill["name"] for skill in repos[0]["skills"]] == ["quiet", "popular"]


def test_export_rejects_unknown_format(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'catalog.db'}"
    init_database(url)
    factory = make_session_factory(url)
    with factory() as session:
        try:
            export_catalog(session, tmp_path / "x", "xml")
        except ValueError as exc:
            assert "json" in str(exc)
        else:
            raise AssertionError("expected ValueError")
