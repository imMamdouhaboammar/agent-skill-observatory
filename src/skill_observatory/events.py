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
