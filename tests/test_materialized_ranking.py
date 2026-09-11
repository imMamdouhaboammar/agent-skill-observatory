from datetime import UTC, datetime

from skill_observatory.materialized import published_repository_rollups
from skill_observatory.publishing import render_awesome_markdown


def _row(
    repo: str,
    *,
    stars: int,
    score: int = 90,
    security: int = 95,
    quality: int = 90,
) -> dict:
    return {
        "canonical_key": f"{repo}:skills/{repo.split('/')[-1]}",
        "repo_full_name": repo,
        "repo_url": f"https://github.com/{repo}",
        "repo_default_branch": "main",
        "path": "skills/example",
        "name": repo.split("/")[-1],
        "description": "Example",
        "stars": stars,
        "forks": 0,
        "pushed_at": "2026-09-10T00:00:00+00:00",
        "archived": False,
        "spec": {"valid": True},
        "score": {
            "overall": score,
            "quality": quality,
            "security": security,
            "maintenance": 80,
            "adoption": 0,
        },
        "evidence": {"categories": ["engineering"]},
    }


def test_repository_rollup_ties_do_not_use_stars() -> None:
    rows = [
        _row("zeta/popular", stars=1_000_000),
        _row("alpha/unknown", stars=0),
    ]

    repos = published_repository_rollups(rows)

    assert [repo["repo_full_name"] for repo in repos] == [
        "alpha/unknown",
        "zeta/popular",
    ]


def test_legacy_awesome_skill_ranking_uses_quality_not_stars() -> None:
    rows = [
        _row("zeta/popular", stars=1_000_000, security=95, quality=80),
        _row("alpha/quiet", stars=1, security=99, quality=99),
    ]

    markdown = render_awesome_markdown(
        rows,
        [],
        {},
        datetime(2026, 9, 10, 18, 0, tzinfo=UTC),
    )
    top_section = markdown.split("## Repository directory", 1)[0]
    category_section = markdown.split("### engineering", 1)[1]

    assert top_section.index("[quiet]") < top_section.index("[popular]")
    assert category_section.index("[quiet]") < category_section.index("[popular]")
