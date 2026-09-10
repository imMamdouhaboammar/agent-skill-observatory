import base64
from datetime import UTC, datetime

import httpx
import pytest

from skill_observatory.config import Settings
from skill_observatory.domain import DiscoveredRepository
from skill_observatory.github import (
    CODE_DISCOVERY_QUERIES,
    DEFAULT_DISCOVERY_QUERIES,
    GitHubClient,
    GitHubError,
)


def repo_payload(full_name="example/skills"):
    return {
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "default_branch": "main",
        "description": "Agent skills",
        "stargazers_count": 5,
        "forks_count": 1,
        "pushed_at": "2026-09-09T10:00:00Z",
        "archived": False,
        "license": {"spdx_id": "MIT"},
        "topics": ["agent-skills"],
    }


def test_discovery_queries_cover_multiple_skill_surfaces_and_domains() -> None:
    repository_queries = " ".join(DEFAULT_DISCOVERY_QUERIES).lower()
    code_queries = " ".join(CODE_DISCOVERY_QUERIES).lower()

    assert "agent skills" in repository_queries
    assert "skill.md" in repository_queries
    for surface in (
        ".agents/skills",
        ".claude/skills",
        ".github/skills",
        "skills/",
    ):
        assert surface in code_queries
    for domain in ("security", "research", "marketing", "data", "testing"):
        assert domain in code_queries
    for domain in (
        "architecture",
        "orchestration",
        "business",
        "sales",
        "recruiting",
        "translation",
        "pdf",
    ):
        assert domain in repository_queries


def test_discovery_query_counts_stay_within_github_search_budgets() -> None:
    assert len(DEFAULT_DISCOVERY_QUERIES) <= 30
    assert len(CODE_DISCOVERY_QUERIES) <= 10


def test_github_search_tree_code_and_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/search/repositories":
            return httpx.Response(200, json={"items": [repo_payload()]})
        if path == "/search/code":
            return httpx.Response(
                200,
                json={"items": [{"repository": {"full_name": "example/skills"}}]},
            )
        if path == "/repos/example/skills":
            return httpx.Response(200, json=repo_payload())
        if path.endswith("/git/trees/main"):
            return httpx.Response(
                200,
                json={"tree": [{"path": "skills/demo/SKILL.md", "type": "blob"}]},
            )
        if path.endswith("/contents/skills/demo/SKILL.md"):
            manifest = b"---\nname: demo\ndescription: Demo. Use when needed.\n---\nBody\n"
            data = base64.b64encode(manifest).decode()
            return httpx.Response(
                200,
                json={"type": "file", "size": 60, "encoding": "base64", "content": data},
            )
        return httpx.Response(404, json={"message": "not found"})

    transport = httpx.MockTransport(handler)
    http = httpx.Client(base_url="https://api.github.com", transport=transport)
    settings = Settings(github_token="token", max_repositories_per_query=10)
    client = GitHubClient(settings, client=http)

    repos = client.search_repositories("topic:agent-skills")
    assert repos[0].full_name == "example/skills"
    assert repos[0].license_spdx == "MIT"
    assert client.search_code_repositories("description filename:SKILL.md") == ["example/skills"]
    assert client.recursive_tree(repos[0])[0]["path"].endswith("SKILL.md")
    assert "name: demo" in client.read_text_file(repos[0], "skills/demo/SKILL.md")


def test_github_error_includes_rate_limit() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0"},
            json={"message": "rate"},
        )
    )
    http = httpx.Client(base_url="https://api.github.com", transport=transport)
    client = GitHubClient(Settings(), client=http)
    with pytest.raises(GitHubError, match="remaining=0"):
        client.search_repositories("topic:agent-skills")


def test_repository_model_accepts_timezone() -> None:
    repo = DiscoveredRepository(
        full_name="x/y",
        html_url="https://github.com/x/y",
        pushed_at=datetime.now(UTC),
        discovery_source="test",
    )
    assert repo.default_branch == "main"
