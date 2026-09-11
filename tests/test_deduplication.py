from datetime import UTC, datetime

from skill_observatory.db import init_database, make_session_factory
from skill_observatory.domain import (
    IndexedSkill,
    ResourceCounts,
    ScoreBreakdown,
    SecurityReport,
    SpecValidation,
)
from skill_observatory.repository import find_duplicate_key, upsert_skill

NOW = datetime(2026, 9, 10, 19, 0, tzinfo=UTC)
FINGERPRINT = "a" * 64


def _skill(canonical_key: str) -> IndexedSkill:
    repo_full_name, path = canonical_key.split(":", 1)
    return IndexedSkill(
        canonical_key=canonical_key,
        content_fingerprint=FINGERPRINT,
        source_fingerprint="b" * 64,
        analysis_fingerprint="c" * 64,
        repo_full_name=repo_full_name,
        repo_url=f"https://github.com/{repo_full_name}",
        repo_default_branch="main",
        path=path,
        name=path.rsplit("/", 1)[-1],
        description="A duplicate fixture with deterministic provenance.",
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
            maintenance=90,
            adoption=0,
        ),
        resources=ResourceCounts(),
        stars=0,
        forks=0,
        pushed_at=NOW,
        archived=False,
        discovery_source="test",
        indexed_at=NOW,
        evidence={"qualification": {"qualified": True}},
    )


def test_duplicate_fingerprint_has_stable_canonical_winner(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'dedupe.db'}"
    init_database(url)
    factory = make_session_factory(url)
    winner = "alpha/repo:skills/demo"
    loser = "zeta/repo:skills/demo"

    with factory() as session:
        upsert_skill(session, _skill(loser))

        assert find_duplicate_key(session, FINGERPRINT, winner) is None

        upsert_skill(session, _skill(winner))

        assert find_duplicate_key(session, FINGERPRINT, winner) is None
        assert find_duplicate_key(session, FINGERPRINT, loser) == winner
