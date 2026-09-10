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
from skill_observatory.github_publisher import GitHubAtomicPublisher
from skill_observatory.publication_store import skill_record_path

NOW = datetime(2026, 9, 10, 8, 30, tzinfo=UTC)
REPOSITORY = "acme/observatory"
README = (
    "# Human heading\n\nHuman text v1\n"
    "<!-- AWESOME_INDEX_START -->\nold\n<!-- AWESOME_INDEX_END -->\n"
    "Human suffix\n"
)


def _skill() -> IndexedSkill:
    return IndexedSkill(
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
        evidence={"categories": ["engineering"]},
    )


def _event() -> tuple[SkillEvent, dict[str, Any]]:
    skill = _skill()
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


def test_happy_path_uses_git_database_and_fast_forward_ref_update() -> None:
    event, catalog = _event()
    requests: list[tuple[str, str, dict[str, Any]]] = []
    blob_number = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal blob_number
        body = _json_body(request)
        requests.append((request.method, request.url.path, body))
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "A"}})
        if path.endswith("/git/commits/A"):
            return httpx.Response(200, json={"tree": {"sha": "TREE-A"}})
        if path.endswith("/contents/README.md"):
            assert request.url.params["ref"] == "A"
            return _content(README)
        if "/contents/catalog/skills/" in path:
            assert request.url.params["ref"] == "A"
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/blobs"):
            blob_number += 1
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if path.endswith("/git/trees"):
            assert body["base_tree"] == "TREE-A"
            return httpx.Response(201, json={"sha": "TREE-C"})
        if path.endswith("/git/commits"):
            assert body["parents"] == ["A"]
            assert body["message"] == "skill(add): example · owner/repo"
            return httpx.Response(201, json={"sha": "C"})
        if path.endswith("/git/refs/heads/main"):
            assert body == {"sha": "C", "force": False}
            return httpx.Response(200, json={"object": {"sha": "C"}})
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    result = publisher.publish_event(event, catalog, repository=REPOSITORY)

    assert result.status == "published"
    assert result.commit_sha == "C"
    assert result.parent_sha == "A"
    assert result.attempts == 1
    assert requests[:4] == [
        ("GET", "/repos/acme/observatory/git/ref/heads/main", {}),
        ("GET", "/repos/acme/observatory/git/commits/A", {}),
        ("GET", "/repos/acme/observatory/contents/README.md", {}),
        (
            "GET",
            f"/repos/acme/observatory/contents/{skill_record_path(event.canonical_key)}",
            {},
        ),
    ]
    patch_requests = [item for item in requests if item[0] == "PATCH"]
    assert patch_requests and all(item[2]["force"] is False for item in patch_requests)


def test_ref_conflict_reloads_main_and_rebuilds_on_new_parent() -> None:
    event, catalog = _event()
    head_reads = iter(["A", "B"])
    current_head = "A"
    commit_parents: list[str] = []
    patch_bodies: list[dict[str, Any]] = []
    readmes = {"A": README, "B": README.replace("Human text v1", "Human text v2")}
    blob_number = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal current_head, blob_number
        body = _json_body(request)
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            current_head = next(head_reads)
            return httpx.Response(200, json={"object": {"sha": current_head}})
        if "/git/commits/" in path and request.method == "GET":
            return httpx.Response(200, json={"tree": {"sha": f"TREE-{current_head}"}})
        if path.endswith("/contents/README.md"):
            return _content(readmes[current_head])
        if "/contents/catalog/skills/" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/blobs"):
            blob_number += 1
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if path.endswith("/git/trees"):
            assert body["base_tree"] == f"TREE-{current_head}"
            return httpx.Response(201, json={"sha": f"NEW-TREE-{current_head}"})
        if path.endswith("/git/commits") and request.method == "POST":
            commit_parents.append(body["parents"][0])
            return httpx.Response(201, json={"sha": f"C-{current_head}"})
        if path.endswith("/git/refs/heads/main"):
            patch_bodies.append(body)
            if len(patch_bodies) == 1:
                return httpx.Response(422, json={"message": "Reference update failed"})
            return httpx.Response(200, json={"object": {"sha": "C-B"}})
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    result = publisher.publish_event(event, catalog, repository=REPOSITORY)

    assert result.status == "published"
    assert result.attempts == 2
    assert result.parent_sha == "B"
    assert commit_parents == ["A", "B"]
    assert all(body["force"] is False for body in patch_bodies)


def test_network_failure_after_accepted_ref_update_converges_to_noop() -> None:
    event, catalog = _event()
    assert event.after is not None
    state = {"published": False}
    commit_posts = 0
    blob_number = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal commit_posts, blob_number
        body = _json_body(request)
        path = request.url.path
        head = "C" if state["published"] else "A"
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": head}})
        if path.endswith(f"/git/commits/{head}"):
            return httpx.Response(200, json={"tree": {"sha": f"TREE-{head}"}})
        if path.endswith("/contents/README.md"):
            return _content(README)
        if "/contents/catalog/skills/" in path:
            if state["published"]:
                return _content(event.after.model_dump_json())
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/blobs"):
            blob_number += 1
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "TREE-C"})
        if path.endswith("/git/commits") and request.method == "POST":
            commit_posts += 1
            assert body["parents"] == ["A"]
            return httpx.Response(201, json={"sha": "C"})
        if path.endswith("/git/refs/heads/main"):
            state["published"] = True
            raise httpx.ReadError("connection lost after update", request=request)
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    result = publisher.publish_event(event, catalog, repository=REPOSITORY)

    assert result.status == "noop"
    assert result.attempts == 2
    assert commit_posts == 1


def test_concurrent_human_readme_edit_is_preserved_on_retry() -> None:
    event, catalog = _event()
    heads = iter(["A", "B"])
    current_head = "A"
    blob_contents: list[str] = []
    patch_count = 0
    blob_number = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal current_head, patch_count, blob_number
        body = _json_body(request)
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            current_head = next(heads)
            return httpx.Response(200, json={"object": {"sha": current_head}})
        if path.endswith(f"/git/commits/{current_head}"):
            return httpx.Response(200, json={"tree": {"sha": f"TREE-{current_head}"}})
        if path.endswith("/contents/README.md"):
            text = (
                README
                if current_head == "A"
                else README.replace("Human text v1", "NEW HUMAN EDIT")
            )
            return _content(text)
        if "/contents/catalog/skills/" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/blobs"):
            blob_number += 1
            blob_contents.append(base64.b64decode(body["content"]).decode())
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": f"NEW-TREE-{current_head}"})
        if path.endswith("/git/commits") and request.method == "POST":
            return httpx.Response(201, json={"sha": f"C-{current_head}"})
        if path.endswith("/git/refs/heads/main"):
            patch_count += 1
            if patch_count == 1:
                return httpx.Response(422, json={"message": "Reference update failed"})
            return httpx.Response(200, json={"object": {"sha": "C-B"}})
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    result = publisher.publish_event(event, catalog, repository=REPOSITORY)

    assert result.status == "published"
    readme_blobs = [text for text in blob_contents if "AWESOME_INDEX_START" in text]
    assert "NEW HUMAN EDIT" in readme_blobs[-1]
    assert "Human text v1" not in readme_blobs[-1]


def test_retry_limit_returns_deferred_without_force_update() -> None:
    event, catalog = _event()
    patch_bodies: list[dict[str, Any]] = []
    blob_number = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal blob_number
        body = _json_body(request)
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "A"}})
        if path.endswith("/git/commits/A"):
            return httpx.Response(200, json={"tree": {"sha": "TREE-A"}})
        if path.endswith("/contents/README.md"):
            return _content(README)
        if "/contents/catalog/skills/" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/blobs"):
            blob_number += 1
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "TREE-C"})
        if path.endswith("/git/commits") and request.method == "POST":
            return httpx.Response(201, json={"sha": "C"})
        if path.endswith("/git/refs/heads/main"):
            patch_bodies.append(body)
            return httpx.Response(422, json={"message": "Reference update failed"})
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    result = publisher.publish_event(
        event, catalog, repository=REPOSITORY, max_attempts=2
    )

    assert result.status == "deferred"
    assert result.attempts == 2
    assert len(patch_bodies) == 2
    assert all(body["force"] is False for body in patch_bodies)
