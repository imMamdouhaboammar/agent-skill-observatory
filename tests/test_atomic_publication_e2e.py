from datetime import UTC, datetime
from pathlib import Path

from skill_observatory.aggregate_publication import AggregatePublicationResult
from skill_observatory.db import init_database, make_session_factory
from skill_observatory.directory import render_skill_event
from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import PublicationResult
from skill_observatory.publication import publish_pending_events
from skill_observatory.publication_store import (
    category_markdown_path,
    repository_markdown_path,
    skill_markdown_path,
    skill_record_path,
)
from skill_observatory.repository import upsert_skill

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
        evidence={"categories": ["engineering"]},
    )


class CheckoutPublisher:
    """Apply the real directory renderer to a checkout while recording atomic commits."""

    def __init__(self, checkout_root: Path) -> None:
        self.checkout_root = checkout_root
        self.head = "A"
        self.commits: list[tuple[str, str, str]] = []
        self.event_calls: list[str] = []

    def current_head(self, repository: str, branch: str = "main") -> str:
        return self.head

    def publish_event(self, event, catalog, *, repository: str, branch: str = "main"):
        self.event_calls.append(event.canonical_key)
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


def test_two_new_skills_become_two_sequential_atomic_commits(tmp_path) -> None:
    _prepare_checkout(tmp_path)
    db_url = f"sqlite+pysqlite:///{tmp_path / 'two-skills.db'}"
    init_database(db_url)
    factory = make_session_factory(db_url)
    publisher = CheckoutPublisher(tmp_path)

    with factory() as session:
        upsert_skill(session, _skill("alpha"))
        upsert_skill(session, _skill("beta"))
        report = publish_pending_events(
            session,
            publisher,
            checkout_root=tmp_path,
            repository=REPOSITORY,
            branch="main",
            max_events=100,
            time_budget_seconds=420,
            now=NOW,
            aggregate_publish=_aggregate_noop,
        )

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
        first = publish_pending_events(
            session,
            publisher,
            checkout_root=tmp_path,
            repository=REPOSITORY,
            branch="main",
            max_events=1,
            time_budget_seconds=420,
            now=NOW,
            aggregate_publish=_aggregate_noop,
        )

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
    with factory() as session:
        second = publish_pending_events(
            session,
            publisher,
            checkout_root=tmp_path,
            repository=REPOSITORY,
            branch="main",
            max_events=100,
            time_budget_seconds=420,
            now=NOW,
            aggregate_publish=_aggregate_noop,
        )

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
        first = publish_pending_events(
            session,
            publisher,
            checkout_root=tmp_path,
            repository=REPOSITORY,
            branch="main",
            max_events=100,
            time_budget_seconds=420,
            now=NOW,
            aggregate_publish=_aggregate_noop,
        )
        assert first.events_published == 1

    commits_before = list(publisher.commits)
    with factory() as session:
        upsert_skill(session, _skill("alpha", stars=999))
        second = publish_pending_events(
            session,
            publisher,
            checkout_root=tmp_path,
            repository=REPOSITORY,
            branch="main",
            max_events=100,
            time_budget_seconds=420,
            now=NOW,
            aggregate_publish=_aggregate_noop,
        )

    assert second.events_detected == 0
    assert second.events_published == 0
    assert publisher.commits == commits_before
