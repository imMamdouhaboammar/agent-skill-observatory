import base64
import json
from datetime import UTC, datetime
from pathlib import Path
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

NOW = datetime(2026, 9, 10, 12, 47, tzinfo=UTC)
README = (
    "# Observatory\n\nHuman-owned introduction.\n\n"
    "<!-- AWESOME_INDEX_START -->\nold\n<!-- AWESOME_INDEX_END -->\n"
)


def _event() -> tuple[SkillEvent, dict[str, Any]]:
    skill = IndexedSkill(
        canonical_key="owner/repo:skills/demo",
        content_fingerprint="c" * 64,
        source_fingerprint="s" * 64,
        analysis_fingerprint="a" * 64,
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_default_branch="main",
        path="skills/demo",
        name="demo",
        description="Demo skill",
        license="MIT",
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
    after = build_published_record(skill, published_at=NOW, event="add")
    event = SkillEvent(
        type="add",
        canonical_key=skill.canonical_key,
        after=after,
        priority=4,
        observed_at=NOW,
    )
    return event, {skill.canonical_key: after}


def _wrapped_content(text: str) -> httpx.Response:
    encoded = base64.b64encode(text.encode()).decode()
    wrapped = "\n".join(encoded[index : index + 60] for index in range(0, len(encoded), 60))
    return httpx.Response(200, json={"content": wrapped, "encoding": "base64"})


def _json_body(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content.decode()) if request.content else {}


def test_publish_event_accepts_github_line_wrapped_base64_content() -> None:
    event, catalog = _event()
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
            return _wrapped_content(README)
        if "/contents/catalog/skills/" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/blobs"):
            blob_number += 1
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "TREE-C"})
        if path.endswith("/git/commits") and request.method == "POST":
            assert body["parents"] == ["A"]
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
    result = publisher.publish_event(event, catalog, repository="acme/observatory")

    assert result.status == "published"
    assert result.commit_sha == "C"


def test_publication_workflows_propagate_failures_through_tee() -> None:
    for name in ["refresh.yml", "bootstrap-catalog.yml"]:
        text = Path(f".github/workflows/{name}").read_text(encoding="utf-8")
        assert "set -o pipefail" in text
        assert "skillobs publish-events" in text
        assert "| tee .cache/publication-report.json" in text
