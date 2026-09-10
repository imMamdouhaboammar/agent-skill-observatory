from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import SkillEvent, build_published_record
from skill_observatory.github_publisher import GitHubPublisherError
from skill_observatory.local_git_publisher import LocalGitAtomicPublisher
from skill_observatory.publication_errors import PublicationError
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


def _prepare_repo(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Test Bot")
    _git(root, "config", "user.email", "bot@example.com")
    _git(root, "remote", "add", "origin", "https://github.com/acme/observatory.git")
    (root / "README.md").write_text(README, encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "initial")


def test_local_git_publisher_creates_one_atomic_skill_commit(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
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


def test_local_git_publisher_rejects_retry_counts_above_one(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    event, catalog = _event()
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)

    with pytest.raises(ValueError, match="supports exactly one attempt"):
        publisher.publish_event(
            event,
            catalog,
            repository="acme/observatory",
            branch="main",
            max_attempts=2,
        )


def test_local_git_publisher_rejects_unstaged_worktree_changes(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    (tmp_path / "README.md").write_text(
        README.replace("Human text", "unrelated edit"), encoding="utf-8"
    )
    event, catalog = _event()
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)

    with pytest.raises(PublicationError, match="clean Git worktree"):
        publisher.publish_event(
            event,
            catalog,
            repository="acme/observatory",
            branch="main",
        )


def test_local_git_publisher_rejects_repository_origin_mismatch(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    event, catalog = _event()
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)

    with pytest.raises(RuntimeError, match="origin repository"):
        publisher.publish_event(
            event,
            catalog,
            repository="other/project",
            branch="main",
        )

    assert _git(tmp_path, "rev-parse", "HEAD") == initial_head
    assert _git(tmp_path, "status", "--porcelain", "--untracked-files=all") == ""


def test_local_git_publisher_rolls_back_partial_event_mutation(monkeypatch, tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    event, catalog = _event()
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)

    def fail_stage(_patch) -> None:
        raise GitHubPublisherError("stage failed")

    monkeypatch.setattr(publisher, "_stage_patch", fail_stage)

    with pytest.raises(RuntimeError, match="stage failed"):
        publisher.publish_event(
            event,
            catalog,
            repository="acme/observatory",
            branch="main",
        )

    assert _git(tmp_path, "rev-parse", "HEAD") == initial_head
    assert _git(tmp_path, "status", "--porcelain", "--untracked-files=all") == ""
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == README
    assert not (tmp_path / skill_record_path(event.canonical_key)).exists()


def test_local_git_publisher_wraps_read_failures(monkeypatch, tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    event, catalog = _event()
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)
    real_read_text = Path.read_text

    def fail_read(path: Path, *args, **kwargs):
        if path.name == "README.md":
            raise OSError("disk read failed")
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_read)

    with pytest.raises(RuntimeError, match="README.md.*read"):
        publisher.publish_event(
            event,
            catalog,
            repository="acme/observatory",
            branch="main",
        )


def test_local_git_publisher_rejects_mismatched_push_url_before_mutation(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    _git(
        tmp_path,
        "remote",
        "set-url",
        "--push",
        "origin",
        "https://github.com/other/project.git",
    )
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    event, catalog = _event()
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)

    with pytest.raises(PublicationError, match="push repository"):
        publisher.publish_event(
            event,
            catalog,
            repository="acme/observatory",
            branch="main",
        )

    assert _git(tmp_path, "rev-parse", "HEAD") == initial_head
    assert _git(tmp_path, "status", "--porcelain", "--untracked-files=all") == ""


def test_local_git_publisher_redacts_credentials_from_remote_validation_errors(
    tmp_path: Path,
) -> None:
    _prepare_repo(tmp_path)
    secret = "ghp_DO_NOT_LEAK_THIS_TOKEN"
    _git(
        tmp_path,
        "remote",
        "set-url",
        "origin",
        f"https://oauth2:{secret}@example.invalid/acme/observatory.git",
    )
    event, catalog = _event()
    publisher = LocalGitAtomicPublisher(checkout_root=tmp_path)

    with pytest.raises(PublicationError) as exc_info:
        publisher.publish_event(
            event,
            catalog,
            repository="acme/observatory",
            branch="main",
        )

    assert secret not in str(exc_info.value)


def test_local_git_publisher_serializes_checkout_transactions(tmp_path: Path) -> None:
    _prepare_repo(tmp_path)
    first = LocalGitAtomicPublisher(checkout_root=tmp_path)
    second = LocalGitAtomicPublisher(checkout_root=tmp_path)

    with first._publication_lock(), pytest.raises(PublicationError, match="lock"):
        with second._publication_lock(blocking=False):
            raise AssertionError("second publication transaction acquired checkout lock")
