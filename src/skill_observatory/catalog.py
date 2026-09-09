from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import SkillRecord


def catalog_stats(session: Session) -> dict[str, Any]:
    total = int(session.scalar(select(func.count()).select_from(SkillRecord)) or 0)
    valid = int(
        session.scalar(
            select(func.count()).select_from(SkillRecord).where(SkillRecord.spec_json["valid"].as_boolean() == True)  # noqa: E712
        )
        or 0
    )
    safe = int(
        session.scalar(select(func.count()).select_from(SkillRecord).where(SkillRecord.security_score >= 85))
        or 0
    )
    high_quality = int(
        session.scalar(select(func.count()).select_from(SkillRecord).where(SkillRecord.overall_score >= 80))
        or 0
    )
    repos = int(session.scalar(select(func.count(func.distinct(SkillRecord.repo_full_name)))) or 0)
    return {
        "skills": total,
        "repositories": repos,
        "spec_valid": valid,
        "security_85_plus": safe,
        "score_80_plus": high_quality,
    }


def records_as_dicts(session: Session) -> list[dict[str, Any]]:
    records = list(
        session.scalars(select(SkillRecord).order_by(SkillRecord.overall_score.desc(), SkillRecord.stars.desc()))
    )
    return [
        {
            "id": r.id,
            "canonical_key": r.canonical_key,
            "repo_full_name": r.repo_full_name,
            "repo_url": r.repo_url,
            "path": r.path,
            "name": r.name,
            "description": r.description,
            "license": r.license,
            "compatibility": r.compatibility,
            "metadata": r.metadata_json,
            "allowed_tools": r.allowed_tools_json,
            "spec": r.spec_json,
            "security": r.security_json,
            "score": r.score_json,
            "resources": r.resources_json,
            "stars": r.stars,
            "forks": r.forks,
            "pushed_at": r.pushed_at.isoformat(),
            "archived": r.archived,
            "discovery_source": r.discovery_source,
            "indexed_at": r.indexed_at.isoformat(),
            "evidence": r.evidence_json,
        }
        for r in records
    ]


def export_catalog(session: Session, output: Path, format: str = "json") -> Path:
    rows = records_as_dicts(session)
    output.parent.mkdir(parents=True, exist_ok=True)
    if format == "json":
        output.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        return output
    if format == "csv":
        fields = [
            "id",
            "name",
            "repo_full_name",
            "repo_url",
            "path",
            "description",
            "license",
            "stars",
            "forks",
            "pushed_at",
            "archived",
            "discovery_source",
            "overall_score",
            "quality_score",
            "security_score",
            "maintenance_score",
            "adoption_score",
            "spec_valid",
        ]
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                score = row["score"]
                writer.writerow(
                    {
                        "id": row["id"],
                        "name": row["name"],
                        "repo_full_name": row["repo_full_name"],
                        "repo_url": row["repo_url"],
                        "path": row["path"],
                        "description": row["description"],
                        "license": row["license"],
                        "stars": row["stars"],
                        "forks": row["forks"],
                        "pushed_at": row["pushed_at"],
                        "archived": row["archived"],
                        "discovery_source": row["discovery_source"],
                        "overall_score": score["overall"],
                        "quality_score": score["quality"],
                        "security_score": score["security"],
                        "maintenance_score": score["maintenance"],
                        "adoption_score": score["adoption"],
                        "spec_valid": row["spec"]["valid"],
                    }
                )
        return output
    raise ValueError("format must be 'json' or 'csv'")
