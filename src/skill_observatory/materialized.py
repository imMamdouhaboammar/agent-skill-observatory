from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from .events import PublishedSkillRecord


def _row(record: PublishedSkillRecord) -> dict[str, Any]:
    skill = record.skill
    return {
        "canonical_key": skill.canonical_key,
        "repo_full_name": skill.repo_full_name,
        "repo_url": skill.repo_url,
        "repo_default_branch": skill.repo_default_branch,
        "path": skill.path,
        "name": skill.name,
        "description": skill.description,
        "license": skill.license,
        "compatibility": skill.compatibility,
        "metadata": skill.metadata,
        "allowed_tools": skill.allowed_tools,
        "spec": skill.spec.model_dump(mode="json"),
        "security": skill.security.model_dump(mode="json"),
        "score": skill.score.model_dump(mode="json"),
        "resources": skill.resources.model_dump(mode="json"),
        "stars": skill.stars,
        "forks": skill.forks,
        "pushed_at": skill.pushed_at.isoformat(),
        "archived": skill.archived,
        "discovery_source": skill.discovery_source,
        "indexed_at": skill.indexed_at.isoformat(),
        "evidence": skill.evidence,
    }


def published_rows(published: dict[str, PublishedSkillRecord]) -> list[dict[str, Any]]:
    return [_row(published[key]) for key in sorted(published)]


def published_stats(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "skills": len(rows),
        "repositories": len({str(row["repo_full_name"]) for row in rows}),
        "spec_valid": sum(bool((row.get("spec") or {}).get("valid")) for row in rows),
        "security_85_plus": sum(
            int((row.get("score") or {}).get("security") or 0) >= 85 for row in rows
        ),
        "score_80_plus": sum(
            int((row.get("score") or {}).get("overall") or 0) >= 80 for row in rows
        ),
    }


def published_repository_rollups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                "name": row["name"],
                "path": row["path"],
                "description": row["description"],
                "overall_score": int(score.get("overall") or 0),
                "security_score": int(score.get("security") or 0),
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
                str(item["name"]).casefold(),
            )
        )
    repos.sort(
        key=lambda item: (
            -int(item["best_score"]),
            str(item["repo_full_name"]).casefold(),
        )
    )
    return repos


def render_catalog_csv(rows: list[dict[str, Any]]) -> str:
    fields = [
        "canonical_key",
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
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        score = row["score"]
        writer.writerow(
            {
                "canonical_key": row["canonical_key"],
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
    return handle.getvalue()


def render_awesome_from_rows(
    rows: list[dict[str, Any]],
    repos: list[dict[str, Any]],
    stats: dict[str, int],
    generated_at: datetime,
) -> str:
    def manifest(row: dict[str, Any]) -> str:
        evidence = row.get("evidence") or {}
        value = evidence.get("manifest")
        if isinstance(value, str) and value:
            return value
        branch = row.get("repo_default_branch") or "main"
        path = str(row.get("path") or ".")
        suffix = "SKILL.md" if path == "." else f"{path}/SKILL.md"
        return f"{row['repo_url']}/blob/{branch}/{suffix}"

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    valid_rows = [row for row in rows if (row.get("spec") or {}).get("valid")]
    for row in valid_rows:
        categories = (row.get("evidence") or {}).get("categories") or ["uncategorized"]
        for category in categories:
            by_category[str(category)].append(row)
    top = sorted(
        valid_rows,
        key=lambda row: (
            -int((row.get("score") or {}).get("overall") or 0),
            -int((row.get("score") or {}).get("security") or 0),
            -int((row.get("score") or {}).get("quality") or 0),
            str(row.get("name") or "").casefold(),
            str(row.get("canonical_key") or ""),
        ),
    )[:25]
    lines = [
        "# Awesome Agent Skills & Repositories",
        "",
        "Evidence-backed materialized view generated from canonical published Skill records on main.",
        "",
        f"> Last refreshed: {generated_at.astimezone(UTC):%Y-%m-%d %H:%M UTC}",
        "> Scores are review signals, not a guarantee that third-party code is safe to execute.",
        "",
        "## Snapshot",
        "",
        f"- **{stats['skills']}** published skills",
        f"- **{stats['repositories']}** repositories",
        f"- **{stats['spec_valid']}** spec-valid manifests",
        f"- **{stats['security_85_plus']}** skills with security score 85+",
        f"- **{stats['score_80_plus']}** skills with overall score 80+",
        "",
        "## Top verified skills",
        "",
        "| Skill | Repository | Score | Security | Stars |",
        "|---|---|---:|---:|---:|",
    ]
    if not top:
        lines.append("| _No published skills yet_ |  |  |  |  |")
    for row in top:
        score = row.get("score") or {}
        lines.append(
            f"| [{row['name']}]({manifest(row)}) | [{row['repo_full_name']}]({row['repo_url']}) | "
            f"{int(score.get('overall') or 0)} | {int(score.get('security') or 0)} | "
            f"{int(row.get('stars') or 0)} |"
        )
    lines.extend(
        [
            "",
            "## Repository directory",
            "",
            "| Repository | Skills | Best score | Stars | Categories |",
            "|---|---:|---:|---:|---|",
        ]
    )
    if not repos:
        lines.append("| _No repositories published yet_ | 0 | 0 | 0 |  |")
    for repo in repos:
        lines.append(
            f"| [{repo['repo_full_name']}]({repo['repo_url']}) | {repo['skills_count']} | "
            f"{repo['best_score']} | {repo['stars']} | {', '.join(repo['categories']) or 'uncategorized'} |"
        )
    lines.extend(
        [
            "",
            "## Machine-readable data",
            "",
            "- [`data/catalog.json`](./data/catalog.json)",
            "- [`data/catalog.csv`](./data/catalog.csv)",
            "- [`data/repositories.json`](./data/repositories.json)",
            "- [`data/stats.json`](./data/stats.json)",
            "- [`data/refresh.json`](./data/refresh.json)",
            "",
            "Generated automatically from canonical published records. Do not edit by hand.",
            "",
        ]
    )
    return "\n".join(lines)


def materialize_records(
    published: dict[str, PublishedSkillRecord], *, generated_at: datetime
) -> dict[str, str]:
    rows = published_rows(published)
    stats = published_stats(rows)
    repos = published_repository_rollups(rows)
    return {
        "AWESOME.md": render_awesome_from_rows(rows, repos, stats, generated_at),
        "data/catalog.json": json.dumps(rows, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "data/catalog.csv": render_catalog_csv(rows),
        "data/repositories.json": json.dumps(
            repos, indent=2, ensure_ascii=False, sort_keys=True
        )
        + "\n",
        "data/stats.json": json.dumps(stats, indent=2, sort_keys=True) + "\n",
        "data/refresh.json": json.dumps(
            {"generated_at": generated_at.astimezone(UTC).isoformat()}, indent=2, sort_keys=True
        )
        + "\n",
    }
