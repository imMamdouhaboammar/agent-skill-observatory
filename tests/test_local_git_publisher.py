from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from skill_observatory.local_git_publisher import LocalGitAtomicPublisher

from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import SkillEvent, build_published_record
from skill_observatory.publication_store import skill_record_path

NOW = datetime(2026, 9, 10, 14, 30, tzinfo=UTC)
README = (
    "# Human heading\n\nHuman text\n"
    "<!-- AWESOME_INDEX_START -->\nold\n<!-- AWESOME_INDEX_END -->\n"
)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _event() -> tuple[SkillEvent, dict[str, object]]:
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
        pushed_at=NOW,
        archived=False,
        discovery_source="test",
        indexed_at=NOW,
        evidence={"categories": ["engineering"]},
    )
    after = build_published_record(skill, published_at=NOW, event="add")
    event = SkillEvent(
        type="add",
        canonical_key=skill.canonical_key,
        after=after,
        priority=4,
        observed_at=NOW,
    )
    return event, {skill.canonical_key: after}


def test_local_git_publisher_creates_one_atomic_skill_commit(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.name", "Test Bot")
    _git(tmp_path, "config", "user.email", "bot@example.com")
    (tmp_path / "README.md").write_text(README, encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "initial")
    initial_head = _git(tmp_path, "rev-parse", "HEAD")

    event, catalog = _event()
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)
    result = publisher.publish_event(
        event,
        catalog,
        repository="acme/observatory",
        branch="main",
    )

    assert result.status == "published"
    assert result.parent_sha == initial_head
    assert result.commit_sha == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "rev-list", "--count", f"{initial_head}..HEAD") == "1"
    assert _git(tmp_path, "log", "-1", "--pretty=%s") == "skill(add): example · owner/repo"
    assert (tmp_path / skill_record_path(event.canonical_key)).exists()
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Human text" in readme
    assert "Published skills: **1**" in readme
