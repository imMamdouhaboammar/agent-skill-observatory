from datetime import datetime, timedelta, timezone

from skill_observatory.domain import RepositorySignals, SecurityReport, SpecValidation
from skill_observatory.scoring import score_skill


def test_score_rewards_compliance_docs_tests_license_and_recent_activity() -> None:
    now = datetime.now(timezone.utc)
    score = score_skill(
        spec=SpecValidation(valid=True, errors=[], warnings=[]),
        security=SecurityReport(score=100, findings=[]),
        repo=RepositorySignals(
            stars=500,
            forks=50,
            pushed_at=now - timedelta(days=3),
            archived=False,
            license_spdx="MIT",
            has_tests=True,
            has_readme=True,
            contributors=8,
            star_velocity_7d=25.0,
        ),
        description_length=180,
        body_chars=3000,
    )
    assert score.overall >= 80
    assert score.quality >= 80
    assert score.maintenance >= 70


def test_archived_repo_is_penalized() -> None:
    now = datetime.now(timezone.utc)
    score = score_skill(
        spec=SpecValidation(valid=True, errors=[], warnings=[]),
        security=SecurityReport(score=100, findings=[]),
        repo=RepositorySignals(
            stars=500,
            forks=50,
            pushed_at=now - timedelta(days=800),
            archived=True,
            license_spdx=None,
            has_tests=False,
            has_readme=False,
            contributors=1,
            star_velocity_7d=0.0,
        ),
        description_length=40,
        body_chars=200,
    )
    assert score.overall < 55
    assert score.maintenance < 30
