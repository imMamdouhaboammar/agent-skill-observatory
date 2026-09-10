from datetime import UTC, datetime

from skill_observatory.db import init_database, make_session_factory
from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import PublicationResult
from skill_observatory.publication import publish_pending_events
from skill_observatory.repository import upsert_skill

NOW = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)


def _skill(name: str) -> IndexedSkill:
    return IndexedSkill(
        canonical_key=f"owner/repo:skills/{name}",
        content_fingerprint=name[0] * 64,
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
        stars=10,
        forks=2,
        pushed_at=NOW,
        archived=False,
        discovery_source="test",
        indexed_at=NOW,
        evidence={"categories": ["engineering"]},
    )


class FakePublisher:
    def __init__(self, statuses: list[str] | None = None) -> None:
        self.calls: list[tuple[str, list[str]]] = []
        self.statuses = iter(statuses or ["published", "published"])
        self.head = "A"

    def current_head(self, repository: str, branch: str = "main") -> str:
        return self.head

    def publish_event(self, event, catalog, *, repository: str, branch: str = "main"):
        self.calls.append((event.canonical_key, sorted(catalog)))
        status = next(self.statuses)
        if status == "published":
            self.head = f"C{len(self.calls)}"
        return PublicationResult(
            canonical_key=event.canonical_key,
            event_type=event.type,
            status=status,
            commit_sha=self.head if status == "published" else None,
            parent_sha="A",
            attempts=2 if status == "deferred" else 1,
        )


def test_two_events_publish_sequentially_as_distinct_calls(tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'publication.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = FakePublisher()

    with factory() as session:
        upsert_skill(session, _skill("alpha"))
        upsert_skill(session, _skill("beta"))
        report = publish_pending_events(
            session,
            publisher,
            checkout_root=tmp_path,
            repository="acme/observatory",
            branch="main",
            max_events=100,
            time_budget_seconds=420,
            now=NOW,
        )

    assert [call[0] for call in publisher.calls] == [
        "owner/repo:skills/alpha",
        "owner/repo:skills/beta",
    ]
    assert publisher.calls[0][1] == ["owner/repo:skills/alpha"]
    assert publisher.calls[1][1] == [
        "owner/repo:skills/alpha",
        "owner/repo:skills/beta",
    ]
    assert report.events_detected == 2
    assert report.events_published == 2
    assert report.adds == 2
    assert report.main_before == "A"
    assert report.main_after == "C2"
    assert not hasattr(publisher, "publish_batch")


def test_max_events_leaves_remaining_delta_unpublished(tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'limit.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = FakePublisher()

    with factory() as session:
        upsert_skill(session, _skill("alpha"))
        upsert_skill(session, _skill("beta"))
        report = publish_pending_events(
            session,
            publisher,
            checkout_root=tmp_path,
            repository="acme/observatory",
            branch="main",
            max_events=1,
            time_budget_seconds=420,
            now=NOW,
        )

    assert len(publisher.calls) == 1
    assert report.events_detected == 2
    assert report.events_published == 1


def test_deferred_work_is_reported_without_becoming_a_failure(tmp_path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'deferred.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = FakePublisher(["deferred"])

    with factory() as session:
        upsert_skill(session, _skill("alpha"))
        report = publish_pending_events(
            session,
            publisher,
            checkout_root=tmp_path,
            repository="acme/observatory",
            branch="main",
            max_events=100,
            time_budget_seconds=420,
            now=NOW,
        )

    assert report.events_deferred == 1
    assert report.events_published == 0
    assert report.failures == []
