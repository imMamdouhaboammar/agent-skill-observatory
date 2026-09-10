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
            select(func.count())
            .select_from(SkillRecord)
            .where(SkillRecord.spec_json["valid"].as_boolean() == True)  # noqa: E712
        )
        or 0
    )
    safe = int(
        session.scalar(
            select(func.count())
            .select_from(SkillRecord)
            .where(SkillRecord.security_score >= 85)
        )
        or 0
    )
    high_quality = int(
        session.scalar(
            select(func.count())
            .select_from(SkillRecord)
            .where(SkillRecord.overall_score >= 80)
        )
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
        session.scalars(
            select(SkillRecord).order_by(
                SkillRecord.overall_score.desc(),
                SkillRecord.security_score.desc(),
                SkillRecord.quality_score.desc(),
                SkillRecord.canonical_key.asc(),
            )
        )
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


def repository_rollups(session: Session) -> list[dict[str, Any]]:
    rows = records_as_dicts(session)
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["repo_full_name"])
        score = row.get("score") or {}
        repo = grouped.setdefault(
            key,
            {
                "repo_full_name": key,
                "repo_url": row["repo_url"],
                "default_branch": row.get("repo_default_branch") or "main",
                "stars": int(row.get("stars") or 0),
                "forks": int(row.get("forks") or 0),
                "pushed_at": row.get("pushed_at"),
                "archived": bool(row.get("archived", False)),
                "skills_count": 0,
                "spec_valid_count": 0,
                "security_85_plus_count": 0,
                "best_score": 0,
                "categories": [],
                "skills": [],
            },
        )
        repo["skills_count"] += 1
        repo["spec_valid_count"] += int(bool((row.get("spec") or {}).get("valid")))
        repo["security_85_plus_count"] += int(int(score.get("security") or 0) >= 85)
        repo["best_score"] = max(int(repo["best_score"]), int(score.get("overall") or 0))
        repo["stars"] = max(int(repo["stars"]), int(row.get("stars") or 0))
        repo["forks"] = max(int(repo["forks"]), int(row.get("forks") or 0))
        pushed = str(row.get("pushed_at") or "")
        if pushed > str(repo.get("pushed_at") or ""):
            repo["pushed_at"] = pushed
        categories = set(repo["categories"])
        categories.update(str(item) for item in (row.get("evidence") or {}).get("categories", []))
        repo["categories"] = sorted(categories)
        repo["skills"].append(
            {
                "canonical_key": row["canonical_key"],
                "name": row["name"],
                "path": row["path"],
                "description": row["description"],
                "overall_score": int(score.get("overall") or 0),
                "security_score": int(score.get("security") or 0),
                "quality_score": int(score.get("quality") or 0),
                "spec_valid": bool((row.get("spec") or {}).get("valid")),
                "manifest": (row.get("evidence") or {}).get("manifest"),
            }
        )

    repos = list(grouped.values())
    for repo in repos:
        repo["skills"].sort(
            key=lambda item: (
                -int(item["overall_score"]),
                -int(item["security_score"]),
                -int(item["quality_score"]),
                str(item["name"]).casefold(),
                str(item["canonical_key"]),
            )
        )
    repos.sort(key=lambda item: (-int(item["best_score"]), str(item["repo_full_name"])))
    return repos


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
