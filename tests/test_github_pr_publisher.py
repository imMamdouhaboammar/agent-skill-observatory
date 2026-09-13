import base64
import json
from datetime import UTC, datetime
from typing import Any

import httpx

from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import SkillEvent, build_published_record
from skill_observatory.pr_publication_cli import (
    BOT_BRANCH_PREFIX,
    GitHubPullRequestPublisher,
)

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
REPOSITORY = "acme/observatory"
README = (
    "# Human heading\n\nHuman text\n"
    "<!-- AWESOME_INDEX_START -->\nold\n<!-- AWESOME_INDEX_END -->\n"
)


def _event() -> tuple[SkillEvent, dict[str, Any]]:
    skill = IndexedSkill(
        canonical_key="owner/repo:skills/example",
        content_fingerprint="c" * 64,
        source_fingerprint="s" * 64,
        analysis_fingerprint="a" * 64,
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_default_branch="main",
        path="skills/example",
        name="example",
        description="Example skill",
        license="MIT",
        compatibility=None,
        metadata={},
        allowed_tools=[],
        spec=SpecValidation(valid=True),
        security=SecurityReport(score=95),
        score=ScoreBreakdown(
            overall=90,
            quality=90,
            security=95,
            maintenance=80,
            adoption=70,
        ),
        resources=ResourceCounts(),
        stars=10,
        forks=2,
        pushed_at=NOW,
        archived=False,
        discovery_source="test",
        indexed_at=NOW,
        evidence={"categories": ["engineering"], "qualification": {"qualified": True}},
    )
    after = build_published_record(skill, published_at=NOW, event="add")
    event = SkillEvent(
        type="add",
        canonical_key=skill.canonical_key,
        after=after,
        priority=4,
        observed_at=NOW,
    )
    return event, {skill.canonical_key: after}


def _content(text: str) -> httpx.Response:
    encoded = base64.b64encode(text.encode()).decode()
    return httpx.Response(200, json={"content": encoded, "encoding": "base64"})


def _json_body(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content.decode()) if request.content else {}


def test_event_publication_creates_one_commit_on_patch_branch_and_opens_pr() -> None:
    event, catalog = _event()
    requests: list[tuple[str, str, dict[str, Any]]] = []
    blob_number = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal blob_number
        path = request.url.path
        body = _json_body(request)
        requests.append((request.method, path, body))
        if request.method == "GET" and path.endswith("/pulls"):
            return httpx.Response(200, json=[])
        if request.method == "GET" and path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "A"}})
        if request.method == "GET" and "/git/ref/heads/" in path and not path.endswith("/main"):
            return httpx.Response(404, json={"message": "Not Found"})
        if request.method == "GET" and path.endswith("/git/commits/A"):
            return httpx.Response(200, json={"tree": {"sha": "TREE-A"}})
        if request.method == "GET" and path.endswith("/contents/README.md"):
            return _content(README)
        if request.method == "GET" and "/contents/catalog/skills/" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if request.method == "POST" and path.endswith("/git/blobs"):
            blob_number += 1
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if request.method == "POST" and path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "TREE-C"})
        if request.method == "POST" and path.endswith("/git/commits"):
            assert body["parents"] == ["A"]
            return httpx.Response(201, json={"sha": "C"})
        if request.method == "POST" and path.endswith("/git/refs"):
            assert body["ref"].startswith(f"refs/heads/{BOT_BRANCH_PREFIX}")
            assert body["ref"] != "refs/heads/main"
            assert body["sha"] == "C"
            return httpx.Response(201, json={"object": {"sha": "C"}})
        if request.method == "POST" and path.endswith("/pulls"):
            assert body["base"] == "main"
            assert body["head"].startswith(BOT_BRANCH_PREFIX)
            assert body["maintainer_can_modify"] is False
            return httpx.Response(201, json={"number": 42, "html_url": "https://example/pr/42"})
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubPullRequestPublisher(
        token="token",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    result = publisher.publish_event(event, catalog, repository=REPOSITORY)

    assert result.status == "published"
    assert result.commit_sha == "C"
    assert result.parent_sha == "A"
    assert not [item for item in requests if item[0] == "PATCH"]
    main_writes = [
        item
        for item in requests
        if item[0] in {"POST", "PATCH", "PUT"} and item[1].endswith("/refs/heads/main")
    ]
    assert main_writes == []


def test_open_generated_pr_defers_without_creating_git_objects() -> None:
    event, catalog = _event()
    writes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method != "GET":
            writes.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/pulls"):
            return httpx.Response(
                200,
                json=[
                    {
                        "number": 9,
                        "head": {"ref": f"{BOT_BRANCH_PREFIX}skill-add-existing"},
                    }
                ],
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubPullRequestPublisher(
        token="token",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    result = publisher.publish_event(event, catalog, repository=REPOSITORY)

    assert result.status == "deferred"
    assert writes == []


def test_open_generated_pr_on_later_page_still_defers_serial_queue() -> None:
    event, catalog = _event()
    pages: list[str | None] = []
    writes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method != "GET":
            writes.append(request.url.path)
        if request.method == "GET" and request.url.path.endswith("/pulls"):
            page = request.url.params.get("page")
            pages.append(page)
            if page == "1":
                return httpx.Response(
                    200,
                    json=[
                        {"number": number, "head": {"ref": f"feature/unrelated-{number}"}}
                        for number in range(1, 101)
                    ],
                )
            if page == "2":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "number": 101,
                            "head": {"ref": f"{BOT_BRANCH_PREFIX}skill-add-existing"},
                        }
                    ],
                )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubPullRequestPublisher(
        token="token",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    result = publisher.publish_event(event, catalog, repository=REPOSITORY)

    assert result.status == "deferred"
    assert pages == ["1", "2"]
    assert writes == []
