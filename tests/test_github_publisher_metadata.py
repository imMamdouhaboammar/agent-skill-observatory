from datetime import UTC, datetime

from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import SkillEvent, build_published_record
from skill_observatory.github_publisher import GitHubAtomicPublisher


def test_skill_commit_message_contains_deterministic_metadata_body() -> None:
    now = datetime(2026, 9, 10, 8, 30, tzinfo=UTC)
    skill = IndexedSkill(
        canonical_key="owner/repo:skills/example",
        content_fingerprint="c" * 64,
        source_fingerprint="s" * 64,
        analysis_fingerprint="a" * 64,
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_default_branch="main",
        path="skills/example",
        name="example",
        description="Example skill",
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
        pushed_at=now,
        archived=False,
        discovery_source="test",
        indexed_at=now,
        evidence={"categories": ["research", "engineering"]},
    )
    after = build_published_record(skill, published_at=now, event="add")
    event = SkillEvent(
        type="add",
        canonical_key=skill.canonical_key,
        after=after,
        priority=4,
        observed_at=now,
    )

    assert GitHubAtomicPublisher._commit_message(event) == "\n".join(
        [
            "skill(add): example · owner/repo",
            "",
            "Skill-Key: owner/repo:skills/example",
            "Event: add",
            f"Source-Fingerprint: {'s' * 64}",
            f"Analysis-Fingerprint: {'a' * 64}",
            "Overall-Score: 90",
            "Security-Score: 95",
            "Categories: engineering, research",
            "Observed-At: 2026-09-10T08:30:00+00:00",
        ]
    )
