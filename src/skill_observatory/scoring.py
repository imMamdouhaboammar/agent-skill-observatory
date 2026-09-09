from __future__ import annotations

import math
from datetime import datetime, timezone

from .domain import RepositorySignals, ScoreBreakdown, SecurityReport, SpecValidation


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def score_skill(
    *,
    spec: SpecValidation,
    security: SecurityReport,
    repo: RepositorySignals,
    description_length: int,
    body_chars: int,
) -> ScoreBreakdown:
    reasons: list[str] = []

    quality = 30.0
    quality += 30 if spec.valid else 0
    quality += 10 if 80 <= description_length <= 700 else 3
    quality += 15 if body_chars >= 1000 else (8 if body_chars >= 400 else 0)
    quality += 8 if repo.has_tests else 0
    quality += 7 if repo.has_readme else 0
    if not spec.valid:
        reasons.append("Open Agent Skills specification errors reduce quality confidence.")
    if repo.has_tests:
        reasons.append("Repository includes test evidence.")

    age_days = max(0, (datetime.now(timezone.utc) - repo.pushed_at).days)
    maintenance = 100.0
    if age_days > 730:
        maintenance -= 65
    elif age_days > 365:
        maintenance -= 45
    elif age_days > 180:
        maintenance -= 25
    elif age_days > 90:
        maintenance -= 12
    if repo.archived:
        maintenance -= 55
        reasons.append("Archived repositories receive a strong maintenance penalty.")
    if repo.contributors >= 5:
        maintenance += 5

    adoption = 10 + min(55, math.log10(repo.stars + 1) * 22)
    adoption += min(15, math.log10(repo.forks + 1) * 8)
    adoption += min(20, max(0.0, repo.star_velocity_7d) * 0.8)

    quality_i = _clamp(quality)
    maintenance_i = _clamp(maintenance)
    adoption_i = _clamp(adoption)
    overall = _clamp(
        quality_i * 0.35 + security.score * 0.30 + maintenance_i * 0.20 + adoption_i * 0.15
    )
    if repo.archived:
        overall = min(overall, 49)
    if repo.license_spdx:
        overall = _clamp(overall + 3)
        reasons.append(f"Repository declares license {repo.license_spdx}.")
    else:
        reasons.append("No repository license detected.")
    if security.score < 85:
        reasons.append("Static safety scan found commands that need human review before execution.")

    return ScoreBreakdown(
        overall=overall,
        quality=quality_i,
        security=security.score,
        maintenance=maintenance_i,
        adoption=adoption_i,
        reasons=reasons,
    )
