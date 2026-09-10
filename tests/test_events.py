from datetime import UTC, datetime

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
    compute_skill_events,
)

NOW = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)
CANONICAL_KEY = "owner/repo:skills/example"


def _skill() -> IndexedSkill:
    return IndexedSkill(
        canonical_key=CANONICAL_KEY,
        content_fingerprint="c" * 64,
        source_fingerprint="s" * 64,
        analysis_fingerprint="a" * 64,
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_default_branch="main",
        path="skills/example",
        name="example",
        description="Example skill",
        license=None,
        compatibility=None,
        metadata={},
        allowed_tools=[],
        spec=SpecValidation(valid=True),
        security=SecurityReport(score=100),
        score=ScoreBreakdown(
            overall=90,
            quality=90,
            security=100,
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
        evidence={},
    )


def _published() -> PublishedSkillRecord:
    return PublishedSkillRecord(
        canonical_key=CANONICAL_KEY,
        source_fingerprint="s" * 64,
        analysis_fingerprint="a" * 64,
        published_at=NOW,
        publication_event="add",
        skill=_skill(),
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


def test_new_active_skill_emits_exactly_one_add_event() -> None:
    events = compute_skill_events([_skill()], {}, observed_at=NOW)

    assert len(events) == 1
    assert events[0].type == "add"
    assert events[0].canonical_key == CANONICAL_KEY
    assert events[0].before is None
    assert events[0].after is not None
    assert events[0].after.source_fingerprint == "s" * 64
