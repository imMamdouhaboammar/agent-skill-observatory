from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import (
    PublishedSkillRecord,
    SkillEvent,
    build_published_record,
    compute_skill_events,
)

NOW = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)
CANONICAL_KEY = "owner/repo:skills/example"


def _skill(
    canonical_key: str = CANONICAL_KEY,
    *,
    source: str = "s",
    analysis: str = "a",
    stars: int = 10,
    forks: int = 2,
    security: int = 100,
    misses: int = 0,
    qualified: bool | None = True,
) -> IndexedSkill:
    repo_full_name, path = canonical_key.split(":", 1)
    evidence: dict[str, object] = {"categories": ["engineering"]}
    if qualified is not None:
        evidence["qualification"] = {
            "qualified": qualified,
            "blocking_reasons": [] if qualified else ["static-security"],
        }
    return IndexedSkill(
        canonical_key=canonical_key,
        content_fingerprint="c" * 64,
        source_fingerprint=source * 64,
        analysis_fingerprint=analysis * 64,
        repo_full_name=repo_full_name,
        repo_url=f"https://github.com/{repo_full_name}",
        repo_default_branch="main",
        path=path,
        name=path.rsplit("/", 1)[-1] if path != "." else "root",
        description="Example skill",
        license=None,
        compatibility=None,
        metadata={},
        allowed_tools=[],
        spec=SpecValidation(valid=True),
        security=SecurityReport(score=security),
        score=ScoreBreakdown(
            overall=90,
            quality=90,
            security=security,
            maintenance=80,
            adoption=70,
        ),
        resources=ResourceCounts(),
        stars=stars,
        forks=forks,
        pushed_at=NOW,
        archived=False,
        discovery_source="test",
        indexed_at=NOW,
        consecutive_misses=misses,
        evidence=evidence,
    )


def _published(
    skill: IndexedSkill | None = None,
    *,
    event: str = "add",
) -> PublishedSkillRecord:
    current = skill or _skill()
    return PublishedSkillRecord(
        canonical_key=current.canonical_key,
        source_fingerprint=current.source_fingerprint,
        analysis_fingerprint=current.analysis_fingerprint,
        published_at=NOW,
        publication_event=event,  # type: ignore[arg-type]
        skill=current,
    )


def test_add_event_requires_after_state() -> None:
    with pytest.raises(ValidationError):
        SkillEvent(
            type="add",
            canonical_key=CANONICAL_KEY,
            priority=5,
            observed_at=NOW,
        )


def test_remove_event_requires_before_state() -> None:
    with pytest.raises(ValidationError):
        SkillEvent(
            type="remove",
            canonical_key=CANONICAL_KEY,
            priority=2,
            observed_at=NOW,
        )


def test_update_event_accepts_before_and_after_states() -> None:
    before = _published()
    after = before.model_copy(
        update={
            "source_fingerprint": "u" * 64,
            "publication_event": "update",
            "published_at": NOW,
        }
    )

    event = SkillEvent(
        type="update",
        canonical_key=CANONICAL_KEY,
        before=before,
        after=after,
        priority=3,
        observed_at=NOW,
    )

    assert event.before == before
    assert event.after == after
    assert event.type == "update"


def test_build_published_record_uses_semantic_fingerprints() -> None:
    skill = _skill(source="x", analysis="y")
    record = build_published_record(skill, published_at=NOW, event="reindex")

    assert record.source_fingerprint == "x" * 64
    assert record.analysis_fingerprint == "y" * 64
    assert record.publication_event == "reindex"
    assert record.skill == skill


def test_new_qualified_active_skill_emits_exactly_one_add_event() -> None:
    events = compute_skill_events([_skill()], {}, observed_at=NOW)

    assert len(events) == 1
    assert events[0].type == "add"
    assert events[0].canonical_key == CANONICAL_KEY
    assert events[0].before is None
    assert events[0].after is not None
    assert events[0].after.source_fingerprint == "s" * 64


def test_new_unqualified_skill_does_not_emit_add() -> None:
    assert compute_skill_events([_skill(qualified=False)], {}, observed_at=NOW) == []


def test_new_skill_with_unknown_legacy_qualification_does_not_emit_add() -> None:
    assert compute_skill_events([_skill(qualified=None)], {}, observed_at=NOW) == []


def test_published_skill_that_loses_qualification_is_removed_first() -> None:
    before = _published(_skill(qualified=True))
    observed = _skill(qualified=False)

    events = compute_skill_events([observed], {CANONICAL_KEY: before}, observed_at=NOW)

    assert [(event.type, event.canonical_key) for event in events] == [
        ("remove", CANONICAL_KEY)
    ]
    assert events[0].priority == 0


def test_published_skill_with_unknown_legacy_qualification_is_preserved() -> None:
    before = _published(_skill(qualified=True))
    observed = _skill(qualified=None, analysis="z")

    assert compute_skill_events([observed], {CANONICAL_KEY: before}, observed_at=NOW) == []


def test_source_change_emits_update() -> None:
    before = _published()
    observed = _skill(source="u")

    events = compute_skill_events(
        [observed], {CANONICAL_KEY: before}, observed_at=NOW + timedelta(minutes=1)
    )

    assert [event.type for event in events] == ["update"]
    assert events[0].before == before
    assert events[0].after is not None
    assert events[0].after.source_fingerprint == "u" * 64


def test_analysis_only_change_emits_reindex() -> None:
    before = _published()
    observed = _skill(analysis="r")

    events = compute_skill_events([observed], {CANONICAL_KEY: before}, observed_at=NOW)

    assert [event.type for event in events] == ["reindex"]
    assert events[0].after is not None
    assert events[0].after.analysis_fingerprint == "r" * 64


def test_telemetry_only_change_emits_no_skill_event() -> None:
    before = _published()
    observed = _skill(stars=999, forks=77).model_copy(
        update={"indexed_at": NOW + timedelta(hours=1)}
    )

    assert compute_skill_events([observed], {CANONICAL_KEY: before}, observed_at=NOW) == []


def test_first_confirmed_miss_emits_no_removal() -> None:
    before = _published()
    observed = _skill(misses=1)

    assert compute_skill_events([observed], {CANONICAL_KEY: before}, observed_at=NOW) == []


def test_two_confirmed_misses_emit_remove() -> None:
    before = _published()
    observed = _skill(misses=2)

    events = compute_skill_events([observed], {CANONICAL_KEY: before}, observed_at=NOW)

    assert [event.type for event in events] == ["remove"]
    assert events[0].before == before
    assert events[0].after is None


def test_identical_semantic_state_emits_no_event() -> None:
    skill = _skill()
    assert compute_skill_events([skill], {CANONICAL_KEY: _published(skill)}, observed_at=NOW) == []


def test_event_order_is_deterministic_and_security_downgrade_is_first() -> None:
    security_key = "owner/repo:skills/a-security"
    remove_key = "owner/repo:skills/b-remove"
    update_key = "owner/repo:skills/c-update"
    reindex_key = "owner/repo:skills/d-reindex"
    add_key = "owner/repo:skills/e-add"

    security_before = _skill(security_key, analysis="a", security=100)
    observed = [
        _skill(add_key),
        _skill(reindex_key, analysis="z"),
        _skill(update_key, source="z"),
        _skill(remove_key, misses=2),
        _skill(security_key, analysis="z", security=70),
    ]
    published = {
        security_key: _published(security_before),
        remove_key: _published(_skill(remove_key)),
        update_key: _published(_skill(update_key)),
        reindex_key: _published(_skill(reindex_key)),
    }

    events = compute_skill_events(observed, published, observed_at=NOW)

    assert [(event.type, event.canonical_key) for event in events] == [
        ("reindex", security_key),
        ("remove", remove_key),
        ("update", update_key),
        ("reindex", reindex_key),
        ("add", add_key),
    ]
    assert events[0].priority < events[1].priority


def test_applying_event_after_state_makes_recomputation_idempotent() -> None:
    observed = _skill(source="u")
    published = {CANONICAL_KEY: _published()}
    event = compute_skill_events([observed], published, observed_at=NOW)[0]
    assert event.after is not None

    published[event.canonical_key] = event.after

    assert compute_skill_events([observed], published, observed_at=NOW) == []
