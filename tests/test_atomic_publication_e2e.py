import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import select

from skill_observatory.aggregate_publication import AggregatePublicationResult
from skill_observatory.db import SkillRecord, init_database, make_session_factory
from skill_observatory.directory import render_skill_event
from skill_observatory.domain import (
    DiscoveredRepository,
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import PublicationResult, SkillEvent, build_published_record
from skill_observatory.github import GitHubError
from skill_observatory.github_publisher import GitHubAtomicPublisher
from skill_observatory.materialized import materialize_records
from skill_observatory.pipeline import index_repository
from skill_observatory.publication import publish_pending_events
from skill_observatory.publication_store import (
    category_markdown_path,
    load_published_catalog,
    repository_markdown_path,
    skill_markdown_path,
    skill_record_path,
)
from skill_observatory.repository import reconcile_successful_repository_scan, upsert_skill

NOW = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)
REPOSITORY = "acme/observatory"
README = (
    "# Observatory\n\nHuman-owned introduction.\n\n"
    "<!-- AWESOME_INDEX_START -->\nold\n<!-- AWESOME_INDEX_END -->\n"
)


def _skill(name: str, *, stars: int = 10) -> IndexedSkill:
    return IndexedSkill(
        canonical_key=f"owner/repo:skills/{name}",
        content_fingerprint=(name[0] * 64)[:64],
        source_fingerprint=(name[-1] * 64)[:64],
        analysis_fingerprint=(name[0] * 64)[:64],
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_default_branch="main",
        path=f"skills/{name}",
        name=name,
        description=f"{name} skill",
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
        stars=stars,
        forks=2,
        pushed_at=NOW,
        archived=False,
        discovery_source="test",
        indexed_at=NOW,
        last_successful_repo_scan_at=NOW,
        evidence={"categories": ["engineering"]},
    )


class CheckoutPublisher:
    """Apply the real directory renderer to a checkout while recording atomic commits."""

    def __init__(self, checkout_root: Path) -> None:
        self.checkout_root = checkout_root
        self.head = "A"
        self.commits: list[tuple[str, str, str]] = []
        self.event_calls: list[str] = []
        self.event_types: list[str] = []

    def current_head(self, repository: str, branch: str = "main") -> str:
        return self.head

    def publish_event(self, event, catalog, *, repository: str, branch: str = "main"):
        self.event_calls.append(event.canonical_key)
        self.event_types.append(event.type)
        readme_path = self.checkout_root / "README.md"
        patch = render_skill_event(
            event,
            catalog,
            current_root_readme=readme_path.read_text(encoding="utf-8"),
        )
        for relative, text in patch.writes.items():
            path = self.checkout_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for relative in patch.deletes:
            path = self.checkout_root / relative
            if path.exists():
                path.unlink()

        parent = self.head
        commit_sha = f"C{len(self.commits) + 1}"
        self.head = commit_sha
        self.commits.append((commit_sha, parent, event.canonical_key))
        return PublicationResult(
            canonical_key=event.canonical_key,
            event_type=event.type,
            status="published",
            commit_sha=commit_sha,
            parent_sha=parent,
            attempts=1,
            files_changed=sorted([*patch.writes, *patch.deletes]),
        )


def _aggregate_noop(publisher, outputs, *, repository: str, branch: str):
    return AggregatePublicationResult(status="noop", parent_sha=publisher.head)


def _prepare_checkout(root: Path) -> None:
    (root / "README.md").write_text(README, encoding="utf-8")


def _publish(
    factory,
    publisher: CheckoutPublisher,
    checkout_root: Path,
    *,
    max_events: int = 100,
):
    with factory() as session:
        return publish_pending_events(
            session,
            publisher,
            checkout_root=checkout_root,
            repository=REPOSITORY,
            branch="main",
            max_events=max_events,
            time_budget_seconds=420,
            now=NOW,
            aggregate_publish=_aggregate_noop,
        )


def _content(text: str) -> httpx.Response:
    encoded = base64.b64encode(text.encode()).decode()
    return httpx.Response(200, json={"content": encoded, "encoding": "base64"})


def _json_body(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content.decode()) if request.content else {}


def _add_event(name: str = "alpha") -> tuple[SkillEvent, dict[str, Any]]:
    skill = _skill(name)
    after = build_published_record(skill, published_at=NOW, event="add")
    event = SkillEvent(
        type="add",
        canonical_key=skill.canonical_key,
        after=after,
        priority=4,
        observed_at=NOW,
    )
    return event, {skill.canonical_key: after}


def test_two_new_skills_become_two_sequential_atomic_commits(tmp_path) -> None:
    _prepare_checkout(tmp_path)
    db_url = f"sqlite+pysqlite:///{tmp_path / 'two-skills.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = CheckoutPublisher(tmp_path)

    with factory() as session:
        upsert_skill(session, _skill("alpha"))
        upsert_skill(session, _skill("beta"))
    report = _publish(factory, publisher, tmp_path)

    assert report.events_published == 2
    assert publisher.commits == [
        ("C1", "A", "owner/repo:skills/alpha"),
        ("C2", "C1", "owner/repo:skills/beta"),
    ]
    assert publisher.commits[0][0] != publisher.commits[1][0]


def test_stop_after_first_event_is_consistent_and_next_run_only_publishes_second(tmp_path) -> None:
    _prepare_checkout(tmp_path)
    db_url = f"sqlite+pysqlite:///{tmp_path / 'recovery.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = CheckoutPublisher(tmp_path)

    with factory() as session:
        upsert_skill(session, _skill("alpha"))
        upsert_skill(session, _skill("beta"))
    first = _publish(factory, publisher, tmp_path, max_events=1)

    alpha = "owner/repo:skills/alpha"
    beta = "owner/repo:skills/beta"
    assert first.events_detected == 2
    assert first.events_published == 1
    assert (tmp_path / skill_record_path(alpha)).is_file()
    assert (tmp_path / skill_markdown_path(alpha)).is_file()
    assert (tmp_path / repository_markdown_path("owner/repo")).is_file()
    assert (tmp_path / category_markdown_path("engineering")).is_file()
    assert alpha in (tmp_path / "awesome/README.md").read_text(encoding="utf-8")
    assert "Human-owned introduction." in (tmp_path / "README.md").read_text(encoding="utf-8")
    assert not (tmp_path / skill_record_path(beta)).exists()
    assert not (tmp_path / skill_markdown_path(beta)).exists()

    calls_before_resume = len(publisher.event_calls)
    second = _publish(factory, publisher, tmp_path)

    assert second.events_detected == 1
    assert second.events_published == 1
    assert publisher.event_calls[calls_before_resume:] == [beta]
    assert (tmp_path / skill_record_path(beta)).is_file()
    assert publisher.commits[-1] == ("C2", "C1", beta)


def test_stars_only_observation_change_creates_no_skill_commit(tmp_path) -> None:
    _prepare_checkout(tmp_path)
    db_url = f"sqlite+pysqlite:///{tmp_path / 'telemetry.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = CheckoutPublisher(tmp_path)

    with factory() as session:
        upsert_skill(session, _skill("alpha", stars=10))
    first = _publish(factory, publisher, tmp_path)
    assert first.events_published == 1

    commits_before = list(publisher.commits)
    with factory() as session:
        upsert_skill(session, _skill("alpha", stars=999))
    second = _publish(factory, publisher, tmp_path)

    assert second.events_detected == 0
    assert second.events_published == 0
    assert publisher.commits == commits_before


def test_removal_requires_two_successful_misses_and_then_one_remove_commit(tmp_path) -> None:
    _prepare_checkout(tmp_path)
    db_url = f"sqlite+pysqlite:///{tmp_path / 'removal.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = CheckoutPublisher(tmp_path)
    key = "owner/repo:skills/alpha"

    with factory() as session:
        upsert_skill(session, _skill("alpha"))
    assert _publish(factory, publisher, tmp_path).events_published == 1

    with factory() as session:
        reconcile_successful_repository_scan(
            session,
            repo_full_name="owner/repo",
            observed_keys=set(),
            scanned_at=NOW + timedelta(minutes=1),
        )
    first_miss = _publish(factory, publisher, tmp_path)
    assert first_miss.events_detected == 0
    assert (tmp_path / skill_record_path(key)).is_file()

    commits_before_remove = len(publisher.commits)
    with factory() as session:
        reconcile_successful_repository_scan(
            session,
            repo_full_name="owner/repo",
            observed_keys=set(),
            scanned_at=NOW + timedelta(minutes=2),
        )
    second_miss = _publish(factory, publisher, tmp_path)

    assert second_miss.events_detected == 1
    assert second_miss.removals == 1
    assert second_miss.events_published == 1
    assert len(publisher.commits) == commits_before_remove + 1
    assert publisher.event_types[-1] == "remove"
    assert not (tmp_path / skill_record_path(key)).exists()
    assert not (tmp_path / skill_markdown_path(key)).exists()
    assert not (tmp_path / repository_markdown_path("owner/repo")).exists()
    assert not (tmp_path / category_markdown_path("engineering")).exists()


def test_failed_repository_scan_does_not_increase_miss_counter(tmp_path) -> None:
    class ScanGitHub:
        tree = [
            {"path": "skills/demo/SKILL.md", "type": "blob"},
            {"path": "skills/demo/scripts/check.py", "type": "blob"},
        ]
        files = {
            "skills/demo/SKILL.md": (
                "---\nname: demo\ndescription: Review repositories safely when evidence is needed.\n"
                "license: MIT\n---\n# Demo\nInspect evidence.\n"
            ),
            "skills/demo/scripts/check.py": "print('ok')\n",
        }

        def recursive_tree(self, repo):
            return self.tree

        def read_text_file(self, repo, path, max_bytes=512_000):
            return self.files[path]

    class FailingScanGitHub(ScanGitHub):
        def recursive_tree(self, repo):
            raise GitHubError("tree unavailable")

    repo = DiscoveredRepository(
        full_name="example/skills",
        html_url="https://github.com/example/skills",
        default_branch="main",
        description="demo",
        stars=12,
        forks=2,
        pushed_at=NOW,
        archived=False,
        license_spdx="MIT",
        discovery_source="test",
    )
    db_url = f"sqlite+pysqlite:///{tmp_path / 'scan-failure.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)

    with factory() as session:
        index_repository(ScanGitHub(), session, repo, now=NOW)  # type: ignore[arg-type]
    with factory() as session, pytest.raises(GitHubError, match="tree unavailable"):
        index_repository(
            FailingScanGitHub(),
            session,
            repo,
            now=NOW + timedelta(minutes=1),
        )  # type: ignore[arg-type]
    with factory() as session:
        record = session.scalar(select(SkillRecord).where(SkillRecord.name == "demo"))
        assert record is not None
        assert record.consecutive_misses == 0


def test_malformed_canonical_record_fails_closed_before_mutation(tmp_path) -> None:
    _prepare_checkout(tmp_path)
    bad_record = tmp_path / "catalog/skills/bad/record.json"
    bad_record.parent.mkdir(parents=True)
    bad_record.write_text("{not-json", encoding="utf-8")
    db_url = f"sqlite+pysqlite:///{tmp_path / 'malformed.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = CheckoutPublisher(tmp_path)

    report = _publish(factory, publisher, tmp_path)

    assert report.global_failure is True
    assert report.failures
    assert publisher.commits == []
    assert publisher.event_calls == []


def test_concurrent_human_commit_retries_on_new_head_without_force_and_preserves_edit() -> None:
    event, catalog = _add_event()
    heads = iter(["A", "B"])
    current_head = "A"
    patch_bodies: list[dict[str, Any]] = []
    commit_parents: list[str] = []
    readme_blobs: list[str] = []
    blob_number = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal current_head, blob_number
        body = _json_body(request)
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            current_head = next(heads)
            return httpx.Response(200, json={"object": {"sha": current_head}})
        if path.endswith(f"/git/commits/{current_head}"):
            return httpx.Response(200, json={"tree": {"sha": f"TREE-{current_head}"}})
        if path.endswith("/contents/README.md"):
            text = README
            if current_head == "B":
                text = README.replace(
                    "Human-owned introduction.", "Human edit during publication."
                )
            return _content(text)
        if "/contents/catalog/skills/" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/blobs"):
            blob_number += 1
            text = base64.b64decode(body["content"]).decode()
            if "AWESOME_INDEX_START" in text:
                readme_blobs.append(text)
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if path.endswith("/git/trees"):
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
    assert patch_bodies and all(body["force"] is False for body in patch_bodies)
    assert "Human edit during publication." in readme_blobs[-1]
    assert "Human-owned introduction." not in readme_blobs[-1]


def test_response_loss_after_ref_update_does_not_duplicate_skill_commit() -> None:
    event, catalog = _add_event()
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
            return httpx.Response(201, json={"sha": "C"})
        if path.endswith("/git/refs/heads/main"):
            assert body == {"sha": "C", "force": False}
            state["published"] = True
            raise httpx.ReadError("connection lost after accepted update", request=request)
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    result = publisher.publish_event(event, catalog, repository=REPOSITORY)

    assert result.status == "noop"
    assert result.attempts == 2
    assert commit_posts == 1


def test_aggregate_catalog_regenerates_from_canonical_records_without_local_views(tmp_path) -> None:
    _prepare_checkout(tmp_path)
    db_url = f"sqlite+pysqlite:///{tmp_path / 'materialize.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = CheckoutPublisher(tmp_path)

    with factory() as session:
        upsert_skill(session, _skill("alpha"))
        upsert_skill(session, _skill("beta"))
    assert _publish(factory, publisher, tmp_path).events_published == 2

    aggregate_paths = [
        tmp_path / "AWESOME.md",
        tmp_path / "data/catalog.json",
        tmp_path / "data/catalog.csv",
        tmp_path / "data/repositories.json",
        tmp_path / "data/stats.json",
        tmp_path / "data/refresh.json",
    ]
    for path in aggregate_paths:
        if path.exists():
            path.unlink()

    published = load_published_catalog(tmp_path)
    outputs = materialize_records(published, generated_at=NOW)
    for relative, text in outputs.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    awesome = (tmp_path / "AWESOME.md").read_text(encoding="utf-8")
    catalog = json.loads((tmp_path / "data/catalog.json").read_text(encoding="utf-8"))
    stats = json.loads((tmp_path / "data/stats.json").read_text(encoding="utf-8"))
    assert "alpha" in awesome and "beta" in awesome
    assert {row["name"] for row in catalog} == {"alpha", "beta"}
    assert stats["skills"] == 2
