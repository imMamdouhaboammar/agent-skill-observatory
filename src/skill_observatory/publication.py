from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .aggregate_publication import AggregatePublicationResult, publish_materialized_views
from .domain import IndexedSkill
from .events import PublicationResult, PublishedSkillRecord, SkillEvent, compute_skill_events
from .github_publisher import GitHubPublisherError
from .materialized import materialize_records
from .publication_store import PublicationStateError, load_published_catalog
from .repository import list_observed_skills

AggregatePublish = Callable[..., AggregatePublicationResult]


class AtomicPublisher(Protocol):
    def current_head(self, repository: str, branch: str = "main") -> str: ...

    def publish_event(
        self,
        event: SkillEvent,
        catalog_after_event: dict[str, PublishedSkillRecord],
        *,
        repository: str,
        branch: str = "main",
        max_attempts: int = 1,
    ) -> PublicationResult: ...


class PublicationReport(BaseModel):
    events_detected: int = 0
    events_published: int = 0
    events_noop: int = 0
    events_deferred: int = 0
    adds: int = 0
    updates: int = 0
    reindexes: int = 0
    removals: int = 0
    conflicts_retried: int = 0
    failures: list[str] = Field(default_factory=list)
    aggregate_status: str | None = None
    aggregate_commit_sha: str | None = None
    main_before: str | None = None
    main_after: str | None = None
    global_failure: bool = False


def _catalog_after(
    published: dict[str, PublishedSkillRecord], event: SkillEvent
) -> dict[str, PublishedSkillRecord]:
    candidate = dict(published)
    if event.type == "remove":
        candidate.pop(event.canonical_key, None)
    else:
        if event.after is None:
            raise ValueError(f"{event.type} event requires after state")
        candidate[event.canonical_key] = event.after
    return candidate


def _count_event_types(report: PublicationReport, events: list[SkillEvent]) -> None:
    report.adds = sum(event.type == "add" for event in events)
    report.updates = sum(event.type == "update" for event in events)
    report.reindexes = sum(event.type == "reindex" for event in events)
    report.removals = sum(event.type == "remove" for event in events)


def _fatal(report: PublicationReport, exc: Exception) -> PublicationReport:
    report.failures.append(str(exc))
    report.global_failure = True
    return report


def _aggregate_catalog(
    published: dict[str, PublishedSkillRecord], observed: list[IndexedSkill]
) -> dict[str, PublishedSkillRecord]:
    observed_by_key = {skill.canonical_key: skill for skill in observed}
    aggregate = dict(published)
    for key, record in published.items():
        latest = observed_by_key.get(key)
        if latest is None or latest.consecutive_misses:
            continue
        if (
            latest.source_fingerprint == record.source_fingerprint
            and latest.analysis_fingerprint == record.analysis_fingerprint
        ):
            aggregate[key] = record.model_copy(update={"skill": latest})
    return aggregate


def publish_pending_events(
    session: Session,
    publisher: AtomicPublisher,
    *,
    checkout_root: Path,
    repository: str,
    branch: str,
    max_events: int,
    time_budget_seconds: int,
    now: datetime | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    aggregate_publish: AggregatePublish = publish_materialized_views,
) -> PublicationReport:
    if max_events < 1:
        raise ValueError("max_events must be at least 1")
    if time_budget_seconds < 1:
        raise ValueError("time_budget_seconds must be at least 1")

    observed_at = now or datetime.now(UTC)
    report = PublicationReport()
    started = monotonic()

    try:
        report.main_before = publisher.current_head(repository, branch)
        published = load_published_catalog(checkout_root)
        observed = list_observed_skills(session)
        events = compute_skill_events(observed, published, observed_at=observed_at)
    except (GitHubPublisherError, PublicationStateError, ValueError) as exc:
        return _fatal(report, exc)

    report.events_detected = len(events)
    _count_event_types(report, events)

    for event in events:
        attempted = report.events_published + report.events_noop + report.events_deferred
        if attempted >= max_events:
            break
        if monotonic() - started >= time_budget_seconds:
            break

        candidate = _catalog_after(published, event)
        try:
            result = publisher.publish_event(
                event,
                candidate,
                repository=repository,
                branch=branch,
            )
        except GitHubPublisherError as exc:
            return _fatal(report, exc)

        report.conflicts_retried += max(0, result.attempts - 1)
        if result.status == "published":
            report.events_published += 1
            published = candidate
        elif result.status == "noop":
            report.events_noop += 1
            published = candidate
        else:
            report.events_deferred += 1

    try:
        aggregate_records = _aggregate_catalog(published, observed)
        outputs = materialize_records(aggregate_records, generated_at=observed_at)
        aggregate_result = aggregate_publish(
            publisher,
            outputs,
            repository=repository,
            branch=branch,
        )
        report.aggregate_status = aggregate_result.status
        report.aggregate_commit_sha = aggregate_result.commit_sha
        report.conflicts_retried += max(0, aggregate_result.attempts - 1)
        report.main_after = publisher.current_head(repository, branch)
    except (GitHubPublisherError, PublicationStateError, ValueError) as exc:
        return _fatal(report, exc)
    return report
