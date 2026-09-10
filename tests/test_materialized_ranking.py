from skill_observatory.materialized import published_repository_rollups


def _row(repo: str, *, stars: int, score: int = 90, security: int = 95) -> dict:
    return {
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
            "quality": 90,
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
