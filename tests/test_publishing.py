import json
from datetime import datetime, timezone

from skill_observatory.catalog import repository_rollups
from skill_observatory.db import init_database, make_session_factory
from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.publishing import publish_catalog
from skill_observatory.repository import upsert_skill


def make_skill(*, name: str, path: str, score: int, categories: list[str]) -> IndexedSkill:
    now = datetime(2026, 9, 9, 15, 0, tzinfo=timezone.utc)
    return IndexedSkill(
        canonical_key=f"example/repo:{path}",
        content_fingerprint=(name[0] * 64)[:64],
        repo_full_name="example/repo",
        repo_url="https://github.com/example/repo",
        repo_default_branch="main",
        path=path,
        name=name,
        description=f"{name} does useful repository work",
        license="MIT",
        compatibility=None,
        metadata={},
        allowed_tools=[],
        spec=SpecValidation(valid=True),
        security=SecurityReport(score=95),
        score=ScoreBreakdown(
            overall=score,
            quality=90,
            security=95,
            maintenance=80,
            adoption=70,
        ),
        resources=ResourceCounts(scripts=1),
        stars=100,
        forks=10,
        pushed_at=now,
        archived=False,
        discovery_source="test",
        indexed_at=now,
        evidence={
            "categories": categories,
            "manifest": f"https://example.test/{path}/SKILL.md",
            "client_compatibility_evidence": {"OpenAI Codex": ["test evidence"]},
        },
    )


def test_repository_rollups_group_multiple_skills(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'catalog.db'}"
    init_database(url)
    factory = make_session_factory(url)
    with factory() as session:
        upsert_skill(
            session,
            make_skill(name="alpha", path="skills/alpha", score=91, categories=["engineering"]),
        )
        upsert_skill(
            session,
            make_skill(name="beta", path="skills/beta", score=82, categories=["research"]),
        )
        repos = repository_rollups(session)

    assert len(repos) == 1
    assert repos[0]["repo_full_name"] == "example/repo"
    assert repos[0]["skills_count"] == 2
    assert repos[0]["best_score"] == 91
    assert repos[0]["categories"] == ["engineering", "research"]


def test_publish_catalog_writes_github_markdown_surfaces(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'catalog.db'}"
    init_database(url)
    factory = make_session_factory(url)
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Demo\n\n## Live Awesome Index\n\n"
        "<!-- AWESOME_INDEX_START -->\nold\n<!-- AWESOME_INDEX_END -->\n",
        encoding="utf-8",
    )
    awesome = tmp_path / "AWESOME.md"
    awesome_directory = tmp_path / "awesome" / "README.md"
    data = tmp_path / "data"
    generated = datetime(2026, 9, 9, 15, 15, tzinfo=timezone.utc)

    with factory() as session:
        upsert_skill(
            session,
            make_skill(name="alpha", path="skills/alpha", score=91, categories=["engineering"]),
        )
        result = publish_catalog(
            session,
            data_dir=data,
            readme_path=readme,
            awesome_path=awesome,
            awesome_directory_path=awesome_directory,
            generated_at=generated,
        )

    assert result["skills"] == 1
    assert json.loads((data / "catalog.json").read_text())[0]["name"] == "alpha"
    assert json.loads((data / "repositories.json").read_text())[0]["skills_count"] == 1
    assert json.loads((data / "refresh.json").read_text())["generated_at"] == "2026-09-09T15:15:00+00:00"
    assert "[alpha](https://example.test/skills/alpha/SKILL.md)" in awesome.read_text()
    assert "(./data/catalog.json)" in awesome.read_text()
    assert "(../data/catalog.json)" in awesome_directory.read_text()
    rendered_readme = readme.read_text()
    assert "<!-- AWESOME_INDEX_START -->" in rendered_readme
    assert "Last refreshed: **2026-09-09 15:15 UTC**" in rendered_readme
    assert "old" not in rendered_readme
