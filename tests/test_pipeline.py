from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from skill_observatory.db import SkillRecord, init_database, make_session_factory
from skill_observatory.domain import DiscoveredRepository
from skill_observatory.github import GitHubError
from skill_observatory.pipeline import index_repository

NOW = datetime(2026, 9, 10, 7, 15, tzinfo=UTC)


class FakeGitHub:
    def __init__(self, script: str = "print('ok')\n") -> None:
        self.tree = [
            {"path": "README.md", "type": "blob"},
            {"path": "tests/test_demo.py", "type": "blob"},
            {"path": "skills/demo/SKILL.md", "type": "blob"},
            {"path": "skills/demo/scripts/check.py", "type": "blob"},
        ]
        self.files = {
            "skills/demo/SKILL.md": (
                "---\n"
                "name: demo\n"
                "description: Review repositories safely. "
                "Use when an agent must inspect project evidence.\n"
                "license: MIT\n"
                "---\n"
                "# Demo\n"
                "Inspect evidence before making claims.\n"
            ),
            "skills/demo/scripts/check.py": script,
        }

    def recursive_tree(self, repo):
        return self.tree

    def read_text_file(self, repo, path, max_bytes=512_000):
        return self.files[path]


class FailingGitHub(FakeGitHub):
    def recursive_tree(self, repo):
        raise GitHubError("tree unavailable")


def _repo(*, stars: int = 12, forks: int = 2) -> DiscoveredRepository:
    return DiscoveredRepository(
        full_name="example/skills",
        html_url="https://github.com/example/skills",
        default_branch="main",
        description="demo",
        stars=stars,
        forks=forks,
        pushed_at=NOW,
        archived=False,
        license_spdx="MIT",
        discovery_source="test",
    )


def _record(factory) -> SkillRecord:
    with factory() as session:
        record = session.scalar(select(SkillRecord).where(SkillRecord.name == "demo"))
        assert record is not None
        session.expunge(record)
        return record


def test_indexes_verified_skill_into_database(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'pipeline.db'}"
    init_database(url)
    factory = make_session_factory(url)
    with factory() as session:
        count, errors = index_repository(
            FakeGitHub(), session, _repo(), now=NOW  # type: ignore[arg-type]
        )
        record = session.scalar(select(SkillRecord).where(SkillRecord.name == "demo"))
    assert errors == []
    assert count == 1
    assert record is not None
    assert record.spec_json["valid"] is True
    assert record.security_score == 100
    assert record.overall_score > 60
    assert record.source_fingerprint
    assert record.analysis_fingerprint
    assert record.consecutive_misses == 0
    assert record.last_successful_repo_scan_at is not None


def test_source_fingerprint_changes_when_bounded_script_changes(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'source.db'}"
    init_database(url)
    factory = make_session_factory(url)
    github = FakeGitHub()
    with factory() as session:
        index_repository(github, session, _repo(), now=NOW)  # type: ignore[arg-type]
    before = _record(factory)

    github.files["skills/demo/scripts/check.py"] = "print('changed')\n"
    with factory() as session:
        index_repository(
            github, session, _repo(), now=NOW + timedelta(minutes=1)  # type: ignore[arg-type]
        )
    after = _record(factory)

    assert after.content_fingerprint == before.content_fingerprint
    assert after.source_fingerprint != before.source_fingerprint


def test_telemetry_changes_do_not_change_semantic_fingerprints(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'telemetry.db'}"
    init_database(url)
    factory = make_session_factory(url)
    github = FakeGitHub()
    with factory() as session:
        index_repository(github, session, _repo(stars=12, forks=2), now=NOW)  # type: ignore[arg-type]
    before = _record(factory)

    with factory() as session:
        index_repository(
            github,
            session,
            _repo(stars=999, forks=77),
            now=NOW + timedelta(minutes=1),
        )  # type: ignore[arg-type]
    after = _record(factory)

    assert after.source_fingerprint == before.source_fingerprint
    assert after.analysis_fingerprint == before.analysis_fingerprint


def test_successful_missing_scans_increment_and_return_resets(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'missing.db'}"
    init_database(url)
    factory = make_session_factory(url)
    github = FakeGitHub()
    with factory() as session:
        index_repository(github, session, _repo(), now=NOW)  # type: ignore[arg-type]

    github.tree = []
    with factory() as session:
        index_repository(
            github, session, _repo(), now=NOW + timedelta(minutes=1)  # type: ignore[arg-type]
        )
    first_miss = _record(factory)
    assert first_miss.consecutive_misses == 1

    with factory() as session:
        index_repository(
            github, session, _repo(), now=NOW + timedelta(minutes=2)  # type: ignore[arg-type]
        )
    second_miss = _record(factory)
    assert second_miss.consecutive_misses == 2

    with factory() as session:
        index_repository(
            github, session, _repo(), now=NOW + timedelta(minutes=3)  # type: ignore[arg-type]
        )
    third_miss = _record(factory)
    assert third_miss.consecutive_misses == 2

    github.tree = FakeGitHub().tree
    with factory() as session:
        index_repository(
            github, session, _repo(), now=NOW + timedelta(minutes=4)  # type: ignore[arg-type]
        )
    returned = _record(factory)
    assert returned.consecutive_misses == 0


def test_failed_repository_scan_does_not_increment_misses(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'failed.db'}"
    init_database(url)
    factory = make_session_factory(url)
    with factory() as session:
        index_repository(FakeGitHub(), session, _repo(), now=NOW)  # type: ignore[arg-type]

    with factory() as session, pytest.raises(GitHubError, match="tree unavailable"):
        index_repository(
            FailingGitHub(),
            session,
            _repo(),
            now=NOW + timedelta(minutes=1),
        )  # type: ignore[arg-type]

    record = _record(factory)
    assert record.consecutive_misses == 0
