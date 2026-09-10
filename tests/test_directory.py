from datetime import UTC, datetime

from skill_observatory.directory import render_skill_event
from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityFinding,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import SkillEvent, build_published_record
from skill_observatory.publication_store import (
    category_markdown_path,
    repository_markdown_path,
    skill_markdown_path,
    skill_record_path,
)

NOW = datetime(2026, 9, 10, 8, 0, tzinfo=UTC)
README = (
    "# Human heading\n\nHuman prose stays byte-for-byte.\n"
    "<!-- AWESOME_INDEX_START -->\nold generated block\n<!-- AWESOME_INDEX_END -->\n"
    "Human suffix stays too.\n"
)


def _skill(
    *,
    category: str = "engineering",
    source: str = "s",
    analysis: str = "a",
) -> IndexedSkill:
    return IndexedSkill(
        canonical_key="owner/repo:skills/example",
        content_fingerprint="c" * 64,
        source_fingerprint=source * 64,
        analysis_fingerprint=analysis * 64,
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_default_branch="main",
        path="skills/example",
        name="example",
        description="Example repository review skill",
        license="MIT",
        compatibility="Codex compatible",
        metadata={},
        allowed_tools=[],
        spec=SpecValidation(valid=True),
        security=SecurityReport(
            score=92,
            findings=[
                SecurityFinding(
                    rule="external-command",
                    severity="medium",
                    file="SKILL.md",
                    line=8,
                    message="Mentions an external command",
                    evidence="example command",
                )
            ],
        ),
        score=ScoreBreakdown(
            overall=88,
            quality=90,
            security=92,
            maintenance=80,
            adoption=70,
        ),
        resources=ResourceCounts(scripts=1, references=2),
        stars=42,
        forks=3,
        pushed_at=NOW,
        archived=False,
        discovery_source="test",
        indexed_at=NOW,
        evidence={
            "categories": [category],
            "manifest": "https://github.com/owner/repo/blob/main/skills/example/SKILL.md",
            "client_compatibility_evidence": {"OpenAI Codex": ["path evidence"]},
            "first_seen_at": "2026-09-01T00:00:00+00:00",
        },
    )


def _add_event(skill: IndexedSkill) -> SkillEvent:
    after = build_published_record(skill, published_at=NOW, event="add")
    return SkillEvent(
        type="add",
        canonical_key=skill.canonical_key,
        after=after,
        priority=4,
        observed_at=NOW,
    )


def test_add_event_writes_only_sharded_directory_surfaces() -> None:
    skill = _skill()
    event = _add_event(skill)
    assert event.after is not None
    catalog = {skill.canonical_key: event.after}

    patch = render_skill_event(event, catalog, current_root_readme=README)

    assert set(patch.writes) == {
        str(skill_record_path(skill.canonical_key)),
        str(skill_markdown_path(skill.canonical_key)),
        str(repository_markdown_path(skill.repo_full_name)),
        str(category_markdown_path("engineering")),
        "awesome/README.md",
        "README.md",
    }
    assert patch.deletes == []
    assert "Example repository review skill" in patch.writes[
        str(skill_markdown_path(skill.canonical_key))
    ]
    assert "OpenAI Codex" in patch.writes[str(skill_markdown_path(skill.canonical_key))]
    assert "Static analysis is not malware certification" in patch.writes[
        str(skill_markdown_path(skill.canonical_key))
    ]
    assert "AWESOME.md" not in patch.writes
    assert not any(path.startswith("data/") for path in patch.writes)


def test_root_readme_preserves_every_byte_outside_markers() -> None:
    skill = _skill()
    event = _add_event(skill)
    assert event.after is not None

    rendered = render_skill_event(
        event,
        {skill.canonical_key: event.after},
        current_root_readme=README,
    ).writes["README.md"]

    before = README.split("<!-- AWESOME_INDEX_START -->", 1)[0]
    after = README.split("<!-- AWESOME_INDEX_END -->", 1)[1]
    assert rendered.startswith(before + "<!-- AWESOME_INDEX_START -->")
    assert rendered.endswith("<!-- AWESOME_INDEX_END -->" + after)
    assert "Published skills: **1**" in rendered
    assert "Latest Skill event: **add**" in rendered


def test_update_regenerates_old_and_new_category_surfaces() -> None:
    before_skill = _skill(category="research")
    after_skill = _skill(category="engineering", analysis="z")
    before = build_published_record(before_skill, published_at=NOW, event="add")
    after = build_published_record(after_skill, published_at=NOW, event="reindex")
    event = SkillEvent(
        type="reindex",
        canonical_key=after_skill.canonical_key,
        before=before,
        after=after,
        priority=3,
        observed_at=NOW,
    )

    patch = render_skill_event(
        event,
        {after_skill.canonical_key: after},
        current_root_readme=README,
    )

    assert str(category_markdown_path("engineering")) in patch.writes
    assert str(category_markdown_path("research")) in patch.deletes
    assert str(repository_markdown_path("owner/repo")) in patch.writes


def test_remove_deletes_empty_skill_repo_and_category_surfaces() -> None:
    skill = _skill()
    before = build_published_record(skill, published_at=NOW, event="add")
    event = SkillEvent(
        type="remove",
        canonical_key=skill.canonical_key,
        before=before,
        priority=1,
        observed_at=NOW,
    )

    patch = render_skill_event(event, {}, current_root_readme=README)

    assert set(patch.deletes) == {
        str(skill_record_path(skill.canonical_key)),
        str(skill_markdown_path(skill.canonical_key)),
        str(repository_markdown_path(skill.repo_full_name)),
        str(category_markdown_path("engineering")),
    }
    assert set(patch.writes) == {"awesome/README.md", "README.md"}
    assert "Published skills: **0**" in patch.writes["README.md"]


def test_rendering_is_byte_deterministic() -> None:
    skill = _skill()
    event = _add_event(skill)
    assert event.after is not None
    catalog = {skill.canonical_key: event.after}

    first = render_skill_event(event, catalog, current_root_readme=README)
    second = render_skill_event(
        event,
        dict(reversed(list(catalog.items()))),
        current_root_readme=README,
    )

    assert first == second
