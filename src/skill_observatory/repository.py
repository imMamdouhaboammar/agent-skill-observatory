from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .db import SkillRecord
from .domain import IndexedSkill


def upsert_skill(session: Session, skill: IndexedSkill) -> SkillRecord:
    record = session.scalar(select(SkillRecord).where(SkillRecord.canonical_key == skill.canonical_key))
    if record is None:
        record = SkillRecord(canonical_key=skill.canonical_key, first_seen_at=skill.indexed_at, last_seen_at=skill.indexed_at, is_active=True)
        session.add(record)

    record.content_fingerprint = skill.content_fingerprint
    record.repo_full_name = skill.repo_full_name
    record.repo_url = skill.repo_url
    record.repo_default_branch = skill.repo_default_branch
    record.path = skill.path
    record.name = skill.name
    record.description = skill.description
    record.license = skill.license
    record.compatibility = skill.compatibility
    record.metadata_json = skill.metadata
    record.allowed_tools_json = skill.allowed_tools
    record.spec_json = skill.spec.model_dump(mode="json")
    record.security_json = skill.security.model_dump(mode="json")
    record.score_json = skill.score.model_dump(mode="json")
    record.resources_json = skill.resources.model_dump(mode="json")
    record.stars = skill.stars
    record.forks = skill.forks
    record.pushed_at = skill.pushed_at
    record.archived = skill.archived
    record.discovery_source = skill.discovery_source
    record.indexed_at = skill.indexed_at
    record.evidence_json = skill.evidence
    record.overall_score = skill.score.overall
    record.quality_score = skill.score.quality
    record.security_score = skill.score.security
    record.maintenance_score = skill.score.maintenance
    record.adoption_score = skill.score.adoption
    record.last_seen_at = skill.indexed_at
    record.is_active = True
    session.commit()
    session.refresh(record)
    return record


def list_skills(
    session: Session,
    *,
    query: str | None = None,
    min_score: int = 0,
    spec_valid: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SkillRecord], int]:
    clauses = [SkillRecord.overall_score >= min_score]
    if query:
        like = f"%{query.strip()}%"
        clauses.append(or_(SkillRecord.name.ilike(like), SkillRecord.description.ilike(like), SkillRecord.repo_full_name.ilike(like)))
    if spec_valid is not None:
        # JSON boolean comparison is portable enough for SQLite/Postgres when serialized by SQLAlchemy.
        clauses.append(SkillRecord.spec_json["valid"].as_boolean() == spec_valid)

    stmt = select(SkillRecord).where(*clauses)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        session.scalars(
            stmt.order_by(SkillRecord.overall_score.desc(), SkillRecord.stars.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return items, int(total)


def estimate_star_velocity_7d(session: Session, repo_full_name: str, current_stars: int, now) -> float:
    from datetime import timedelta

    from .db import RepositorySnapshot

    cutoff = now - timedelta(days=14)
    previous = session.scalar(
        select(RepositorySnapshot)
        .where(
            RepositorySnapshot.repo_full_name == repo_full_name,
            RepositorySnapshot.captured_at >= cutoff,
            RepositorySnapshot.captured_at < now,
        )
        .order_by(RepositorySnapshot.captured_at.asc())
        .limit(1)
    )
    if previous is None:
        return 0.0
    elapsed_days = max((now - previous.captured_at).total_seconds() / 86400.0, 0.25)
    return max(0.0, (current_stars - previous.stars) / elapsed_days * 7.0)


def record_repository_snapshot(session: Session, *, repo_full_name: str, captured_at, stars: int, forks: int) -> None:
    from .db import RepositorySnapshot

    session.add(
        RepositorySnapshot(
            repo_full_name=repo_full_name,
            captured_at=captured_at,
            stars=stars,
            forks=forks,
            open_issues=0,
            watchers=0,
            score_hint=0.0,
        )
    )
    session.commit()


def find_duplicate_key(session: Session, fingerprint: str, canonical_key: str) -> str | None:
    record = session.scalar(
        select(SkillRecord)
        .where(
            SkillRecord.content_fingerprint == fingerprint,
            SkillRecord.canonical_key != canonical_key,
        )
        .order_by(SkillRecord.id.asc())
        .limit(1)
    )
    return record.canonical_key if record is not None else None
