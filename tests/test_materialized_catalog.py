import json
from datetime import UTC, datetime

from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.events import PublishedSkillRecord
from skill_observatory.publishing import materialize_published_catalog

NOW = datetime(2026, 9, 10, 9, 30, tzinfo=UTC)


def _record(name: str, score: int) -> PublishedSkillRecord:
    skill = IndexedSkill(
        canonical_key=f"owner/repo:skills/{name}",
        content_fingerprint=name[0] * 64,
        source_fingerprint=name[-1] * 64,
        analysis_fingerprint=name[0] * 64,
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_default_branch="main",
        path=f"skills/{name}",
        name=name,
        description=f"{name} skill",
        license="MIT",
        compatibility=None,
        metadata={},
        allowed_tools=[],
        spec=SpecValidation(valid=True),
        security=SecurityReport(score=95),
        score=ScoreBreakdown(
            overall=score,
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
        evidence={
            "categories": ["engineering"],
            "manifest": f"https://github.com/owner/repo/blob/main/skills/{name}/SKILL.md",
        },
    )
    return PublishedSkillRecord(
        canonical_key=skill.canonical_key,
        source_fingerprint=skill.source_fingerprint,
        analysis_fingerprint=skill.analysis_fingerprint,
        published_at=NOW,
        publication_event="add",
        skill=skill,
    )


def test_materialization_returns_only_explicit_aggregate_paths() -> None:
    records = {
        "owner/repo:skills/alpha": _record("alpha", 91),
        "owner/repo:skills/beta": _record("beta", 82),
    }
    outputs = materialize_published_catalog(records, generated_at=NOW)

    assert set(outputs) == {
        "AWESOME.md",
        "data/catalog.json",
        "data/catalog.csv",
        "data/repositories.json",
        "data/stats.json",
        "data/refresh.json",
    }
    catalog = json.loads(outputs["data/catalog.json"])
    assert [row["canonical_key"] for row in catalog] == [
        "owner/repo:skills/alpha",
        "owner/repo:skills/beta",
    ]
    assert json.loads(outputs["data/stats.json"])["skills"] == 2
    assert "alpha" in outputs["AWESOME.md"]
    assert "beta" in outputs["AWESOME.md"]


def test_materialization_is_stable_across_input_insertion_order() -> None:
    alpha = _record("alpha", 91)
    beta = _record("beta", 82)
    forward = materialize_published_catalog(
        {alpha.canonical_key: alpha, beta.canonical_key: beta}, generated_at=NOW
    )
    reverse = materialize_published_catalog(
        {beta.canonical_key: beta, alpha.canonical_key: alpha}, generated_at=NOW
    )

    assert forward == reverse
