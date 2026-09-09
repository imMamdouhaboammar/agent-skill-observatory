import json
from datetime import datetime, timezone

from skill_observatory.catalog import catalog_stats, export_catalog
from skill_observatory.db import init_database, make_session_factory
from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.repository import upsert_skill


def make_skill() -> IndexedSkill:
    now = datetime.now(timezone.utc)
    return IndexedSkill(
        canonical_key="example/repo:skills/demo",
        content_fingerprint="a" * 64,
        repo_full_name="example/repo",
        repo_url="https://github.com/example/repo",
        repo_default_branch="main",
        path="skills/demo",
        name="demo",
        description="Demo skill for repository review",
        license="MIT",
        compatibility=None,
        metadata={},
        allowed_tools=[],
        spec=SpecValidation(valid=True),
        security=SecurityReport(score=95),
        score=ScoreBreakdown(overall=88, quality=90, security=95, maintenance=80, adoption=70),
        resources=ResourceCounts(scripts=1),
        stars=100,
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
