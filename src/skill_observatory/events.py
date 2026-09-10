from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from .domain import IndexedSkill, SkillEventType


class PublishedSkillRecord(BaseModel):
    schema_version: int = 1
    canonical_key: str
    source_fingerprint: str
    analysis_fingerprint: str
    published_at: datetime
    publication_event: SkillEventType
    skill: IndexedSkill

    @model_validator(mode="after")
    def canonical_key_matches_skill(self) -> Self:
        if self.skill.canonical_key != self.canonical_key:
            raise ValueError("published record canonical_key must match skill canonical_key")
        return self


class SkillEvent(BaseModel):
    type: SkillEventType
    canonical_key: str
    before: PublishedSkillRecord | None = None
    after: PublishedSkillRecord | None = None
    priority: int
    observed_at: datetime

    @model_validator(mode="after")
    def valid_transition(self) -> Self:
        if self.type == "add":
            if self.before is not None or self.after is None:
                raise ValueError("add event requires after state and no before state")
        elif self.type == "remove":
            if self.before is None or self.after is not None:
                raise ValueError("remove event requires before state and no after state")
        elif self.before is None or self.after is None:
            raise ValueError(f"{self.type} event requires before and after states")

        for state in (self.before, self.after):
            if state is not None and state.canonical_key != self.canonical_key:
                raise ValueError("event state canonical_key must match event canonical_key")
        return self


class PublicationResult(BaseModel):
    canonical_key: str
    event_type: SkillEventType
    status: Literal["published", "noop", "deferred"]
    commit_sha: str | None = None
    parent_sha: str | None = None
    attempts: int = 0
    files_changed: list[str] = Field(default_factory=list)


def build_published_record(
    skill: IndexedSkill,
    *,
    published_at: datetime,
    event: SkillEventType,
) -> PublishedSkillRecord:
    return PublishedSkillRecord(
        canonical_key=skill.canonical_key,
        source_fingerprint=skill.source_fingerprint,
        analysis_fingerprint=skill.analysis_fingerprint,
        published_at=published_at,
        publication_event=event,
        skill=skill,
    )


def _event_priority(
    event_type: SkillEventType,
    *,
    urgent: bool = False,
) -> int:
    if urgent:
        return 0
    return {"remove": 1, "update": 2, "reindex": 3, "add": 4}[event_type]


def _qualification_state(skill: IndexedSkill) -> bool | None:
    raw = skill.evidence.get("qualification")
    if not isinstance(raw, dict):
        return None
    value = raw.get("qualified")
    return value if isinstance(value, bool) else None


def compute_skill_events(
    observed: list[IndexedSkill],
    published: dict[str, PublishedSkillRecord],
    *,
    observed_at: datetime,
) -> list[SkillEvent]:
    events: list[SkillEvent] = []
    seen: set[str] = set()
    for skill in observed:
        if skill.canonical_key in seen:
            raise ValueError(f"duplicate observed canonical key: {skill.canonical_key}")
        seen.add(skill.canonical_key)

        before = published.get(skill.canonical_key)
        qualification = _qualification_state(skill)
        if before is None:
            if skill.consecutive_misses != 0 or qualification is not True:
                continue
            after = build_published_record(skill, published_at=observed_at, event="add")
            events.append(
                SkillEvent(
                    type="add",
                    canonical_key=skill.canonical_key,
                    after=after,
                    priority=_event_priority("add"),
                    observed_at=observed_at,
                )
            )
            continue

        if skill.consecutive_misses >= 2:
            events.append(
                SkillEvent(
                    type="remove",
                    canonical_key=skill.canonical_key,
                    before=before,
                    priority=_event_priority("remove"),
                    observed_at=observed_at,
                )
            )
            continue
        if skill.consecutive_misses != 0:
            continue

        if qualification is False:
            events.append(
                SkillEvent(
                    type="remove",
                    canonical_key=skill.canonical_key,
                    before=before,
                    priority=_event_priority("remove", urgent=True),
                    observed_at=observed_at,
                )
            )
            continue
        if qualification is None:
            continue

        security_downgrade = skill.security.score < before.skill.security.score
        event_type: SkillEventType | None = None
        if skill.source_fingerprint != before.source_fingerprint:
            event_type = "update"
        elif skill.analysis_fingerprint != before.analysis_fingerprint:
            event_type = "reindex"
        if event_type is None:
            continue

        after = build_published_record(skill, published_at=observed_at, event=event_type)
        events.append(
            SkillEvent(
                type=event_type,
                canonical_key=skill.canonical_key,
                before=before,
                after=after,
                priority=_event_priority(event_type, urgent=security_downgrade),
                observed_at=observed_at,
            )
        )

    return sorted(events, key=lambda event: (event.priority, event.canonical_key))
