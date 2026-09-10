from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from .config import Settings
from .domain import DiscoveredRepository

DEFAULT_DISCOVERY_QUERIES = (
    "topic:agent-skills",
    '"agent skills" in:name,description,readme',
    '"claude skills" in:name,description,readme',
    '"codex skills" in:name,description,readme',
    '"SKILL.md" in:readme',
    '"agent skills" architecture in:name,description,readme',
    '"agent skills" orchestration in:name,description,readme',
    '"agent skills" business in:name,description,readme',
    '"agent skills" sales in:name,description,readme',
    '"agent skills" recruiting in:name,description,readme',
    '"agent skills" translation in:name,description,readme',
    '"agent skills" pdf in:name,description,readme',
)

CODE_DISCOVERY_QUERIES = (
    '"description:" filename:SKILL.md path:.agents/skills',
    '"description:" filename:SKILL.md path:.claude/skills',
    '"description:" filename:SKILL.md path:.github/skills',
    '"description:" filename:SKILL.md path:skills/',
    "security filename:SKILL.md",
    "research filename:SKILL.md",
    "marketing filename:SKILL.md",
    "data filename:SKILL.md",
    "testing filename:SKILL.md",
)

OFFICIAL_SEEDS = (
    "agentskills/agentskills",
    "anthropics/skills",
    "github/awesome-copilot",
)


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or Settings()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": self.settings.user_agent,
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        self._owns_client = client is None
        self.client = client or httpx.Client(
            base_url=self.settings.github_api_url,
            headers=headers,
            timeout=self.settings.request_timeout_seconds,
            follow_redirects=True,
        )

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_: object) -> None:
        if self._owns_client:
            self.client.close()

    def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        response = self.client.get(path, **kwargs)
        if response.status_code >= 400:
            remaining = response.headers.get("x-ratelimit-remaining", "unknown")
            raise GitHubError(
                f"GitHub API {response.status_code} for {path}; rate-limit remaining={remaining}"
            )
        return response

    @staticmethod
    def _repository(item: dict[str, Any], source: str) -> DiscoveredRepository:
        license_data = item.get("license") or {}
        return DiscoveredRepository(
            full_name=item["full_name"],
            html_url=item["html_url"],
            default_branch=item.get("default_branch") or "main",
            description=item.get("description") or "",
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            pushed_at=datetime.fromisoformat(item["pushed_at"].replace("Z", "+00:00")),
            archived=bool(item.get("archived", False)),
            license_spdx=license_data.get("spdx_id") if isinstance(license_data, dict) else None,
            topics=list(item.get("topics") or []),
            discovery_source=source,
        )

    def search_repositories(
        self, query: str, per_page: int | None = None
    ) -> list[DiscoveredRepository]:
        size = min(per_page or self.settings.max_repositories_per_query, 100)
        response = self._get(
            "/search/repositories",
            params={"q": query, "sort": "updated", "order": "desc", "per_page": size},
        )
        return [
            self._repository(item, f"repo-search:{query}")
            for item in response.json().get("items", [])
        ]

    def get_repository(self, full_name: str, source: str = "seed") -> DiscoveredRepository:
        response = self._get(f"/repos/{full_name}")
        return self._repository(response.json(), source)

    def search_code_repositories(self, query: str, per_page: int = 50) -> list[str]:
        if not self.settings.github_token:
            return []
        response = self._get(
            "/search/code",
            params={"q": query, "per_page": min(per_page, 100)},
        )
        names: list[str] = []
        seen: set[str] = set()
        for item in response.json().get("items", []):
            repository = item.get("repository") or {}
            full_name = repository.get("full_name")
            if isinstance(full_name, str) and full_name.lower() not in seen:
                seen.add(full_name.lower())
                names.append(full_name)
        return names

    def discover(
        self, queries: tuple[str, ...] = DEFAULT_DISCOVERY_QUERIES
    ) -> list[DiscoveredRepository]:
        discovered: dict[str, DiscoveredRepository] = {}
        for query in queries:
            for repo in self.search_repositories(query):
                key = repo.full_name.lower()
                previous = discovered.get(key)
                if previous is None or repo.pushed_at > previous.pushed_at:
                    discovered[key] = repo
        if self.settings.github_token:
            for code_query in CODE_DISCOVERY_QUERIES:
                try:
                    names = self.search_code_repositories(code_query, per_page=25)
                except GitHubError:
                    continue
                for name in names:
                    if name.lower() in discovered:
                        continue
                    try:
                        repo = self.get_repository(name, source=f"code-search:{code_query}")
                    except GitHubError:
                        continue
                    discovered[repo.full_name.lower()] = repo
        for seed in OFFICIAL_SEEDS:
            try:
                repo = self.get_repository(seed, source="official-seed")
            except GitHubError:
                continue
            discovered.setdefault(repo.full_name.lower(), repo)
        return sorted(discovered.values(), key=lambda item: item.pushed_at, reverse=True)

    def recursive_tree(self, repo: DiscoveredRepository) -> list[dict[str, Any]]:
        ref = quote(repo.default_branch, safe="")
        response = self._get(f"/repos/{repo.full_name}/git/trees/{ref}", params={"recursive": "1"})
        payload = response.json()
        if payload.get("truncated"):
            raise GitHubError(f"Recursive tree for {repo.full_name} is truncated")
        return list(payload.get("tree") or [])

    def read_text_file(
        self, repo: DiscoveredRepository, path: str, max_bytes: int = 512_000
    ) -> str:
        safe_path = quote(path, safe="/")
        response = self._get(
            f"/repos/{repo.full_name}/contents/{safe_path}",
            params={"ref": repo.default_branch},
        )
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("type") != "file":
            raise GitHubError(f"Expected file at {repo.full_name}:{path}")
        size = int(payload.get("size") or 0)
        if size > max_bytes:
            raise GitHubError(f"Refusing file larger than {max_bytes} bytes: {path}")
        content = payload.get("content")
        if not content:
            raise GitHubError(f"GitHub did not return inline content for {path}")
        encoding = payload.get("encoding")
        if encoding != "base64":
            raise GitHubError(f"Unsupported GitHub content encoding {encoding!r} for {path}")
        return base64.b64decode(content).decode("utf-8", errors="replace")
