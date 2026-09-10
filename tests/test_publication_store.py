from datetime import UTC, datetime

import pytest

from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import PublishedSkillRecord
from skill_observatory.publication_store import (
    PublicationStateError,
    category_markdown_path,
    load_published_catalog,
    repository_markdown_path,
    skill_markdown_path,
    skill_record_path,
)

NOW = datetime(2026, 9, 10, 7, 30, tzinfo=UTC)


def _published(canonical_key: str, *, name: str = "example") -> PublishedSkillRecord:
    repo_full_name, path = canonical_key.split(":", 1)
    skill = IndexedSkill(
        canonical_key=canonical_key,
        content_fingerprint="c" * 64,
        source_fingerprint="s" * 64,
        analysis_fingerprint="a" * 64,
        repo_full_name=repo_full_name,
        repo_url=f"https://github.com/{repo_full_name}",
        repo_default_branch="main",
        path=path,
        name=name,
        description="Example skill",
        license="MIT",
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
    return PublishedSkillRecord(
        canonical_key=canonical_key,
        source_fingerprint=skill.source_fingerprint,
        analysis_fingerprint=skill.analysis_fingerprint,
        published_at=NOW,
        publication_event="add",
        skill=skill,
    )


def test_canonical_skill_paths_preserve_nested_and_mixed_case_segments() -> None:
    assert str(skill_record_path("Owner/Repo:skills/FrontEnd")) == (
        "catalog/skills/Owner/Repo/skills/FrontEnd/record.json"
    )
    assert str(skill_markdown_path("Owner/Repo:skills/FrontEnd")) == (
        "awesome/skills/Owner/Repo/skills/FrontEnd/README.md"
    )
    assert str(repository_markdown_path("Owner/Repo")) == "awesome/repos/Owner/Repo.md"


def test_root_skill_uses_reserved_root_segment() -> None:
    assert str(skill_record_path("owner/repo:.")) == (
        "catalog/skills/owner/repo/_root/record.json"
    )
    assert str(skill_markdown_path("owner/repo:.")) == (
        "awesome/skills/owner/repo/_root/README.md"
    )


def test_category_path_uses_normalized_slug() -> None:
    assert str(category_markdown_path("Code Review & Quality")) == (
        "awesome/categories/code-review-quality.md"
    )


@pytest.mark.parametrize(
    "canonical_key",
    [
        "owner/repo:../escape",
        "owner/repo:skills/../../escape",
        "owner/repo:/absolute",
        "owner/repo:skills/./escape",
        "owner/repo:_root",
        "../repo:skills/example",
        "owner/repo:skills/\\escape",
        "owner/repo:skills/\x00escape",
    ],
)
def test_skill_paths_reject_unsafe_or_ambiguous_inputs(canonical_key: str) -> None:
    with pytest.raises(ValueError):
        skill_record_path(canonical_key)


def test_repository_and_category_paths_reject_traversal() -> None:
    with pytest.raises(ValueError):
        repository_markdown_path("owner/../repo")
    with pytest.raises(ValueError):
        category_markdown_path("../security")


def test_load_published_catalog_returns_records_keyed_by_canonical_key(tmp_path) -> None:
    records = [
        _published("owner/repo:skills/alpha", name="alpha"),
        _published("Other/Repo:.", name="root-skill"),
    ]
    for record in records:
        path = tmp_path / skill_record_path(record.canonical_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")

    loaded = load_published_catalog(tmp_path)

    assert list(sorted(loaded)) == ["Other/Repo:.", "owner/repo:skills/alpha"]
    assert loaded["owner/repo:skills/alpha"].skill.name == "alpha"
    assert loaded["Other/Repo:."].skill.name == "root-skill"


def test_load_published_catalog_fails_closed_on_malformed_json(tmp_path) -> None:
    path = tmp_path / "catalog/skills/owner/repo/skills/bad/record.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(PublicationStateError, match="malformed published record"):
        load_published_catalog(tmp_path)


def test_load_published_catalog_fails_closed_on_duplicate_key(tmp_path) -> None:
    record = _published("owner/repo:skills/example")
    first = tmp_path / skill_record_path(record.canonical_key)
    first.parent.mkdir(parents=True)
    first.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    duplicate = tmp_path / "catalog/skills/duplicate/copy/record.json"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")

    with pytest.raises(PublicationStateError, match="duplicate published canonical key"):
        load_published_catalog(tmp_path)
