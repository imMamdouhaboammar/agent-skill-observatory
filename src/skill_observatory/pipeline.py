from __future__ import annotations

import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy.orm import Session

from .classification import classify_categories, infer_clients
from .dedupe import canonical_skill_key, content_fingerprint
from .domain import DiscoveredRepository, IndexedSkill, RepositorySignals
from .github import GitHubClient, GitHubError
from .parser import SkillParseError, parse_skill_directory
from .repository import (
    estimate_star_velocity_7d,
    find_duplicate_key,
    record_repository_snapshot,
    upsert_skill,
)
from .scoring import score_skill
from .security import assess_skill_security

MAX_SKILL_FILES = 120
MAX_SINGLE_FILE_BYTES = 512_000
TEXTISH_SUFFIXES = {
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini", ".sh", ".bash", ".zsh",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".ps1", ".rb", ".pl", ".sql", ".xml", ".csv",
}


class PipelineReport(dict[str, Any]):
    pass


def _is_skill_manifest(path: str) -> bool:
    return PurePosixPath(path).name.lower() == "skill.md"


def _candidate_skill_roots(tree: list[dict[str, Any]]) -> list[str]:
    roots: list[str] = []
    for item in tree:
        path = str(item.get("path") or "")
        if item.get("type") == "blob" and _is_skill_manifest(path):
            parent = str(PurePosixPath(path).parent)
            roots.append("" if parent == "." else parent)
    return sorted(set(roots))


def _paths_for_skill(tree: list[dict[str, Any]], root: str) -> list[str]:
    prefix = f"{root}/" if root else ""
    paths: list[str] = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = str(item.get("path") or "")
        if not path.startswith(prefix):
            continue
        rel = path[len(prefix) :]
        if "/" not in rel:
            if rel.lower() == "skill.md" or PurePosixPath(rel).suffix.lower() in TEXTISH_SUFFIXES:
                paths.append(path)
            continue
        top = rel.split("/", 1)[0]
        if top in {"scripts", "references", "assets", "evals", "agents"}:
            suffix = PurePosixPath(rel).suffix.lower()
            if suffix in TEXTISH_SUFFIXES or top == "assets":
                paths.append(path)
    return paths[:MAX_SKILL_FILES]


def _safe_local_path(base: Path, relative: str) -> Path:
    candidate = (base / relative).resolve()
    base_resolved = base.resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        raise ValueError(f"unsafe repository path: {relative}")
    return candidate


def _materialize_skill(
    client: GitHubClient,
    repo: DiscoveredRepository,
    root: str,
    tree: list[dict[str, Any]],
    temp: Path,
) -> Path:
    skill_dir = temp / (PurePosixPath(root).name if root else repo.full_name.split("/")[-1])
    skill_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{root}/" if root else ""
    for remote_path in _paths_for_skill(tree, root):
        rel = remote_path[len(prefix) :]
        local_path = _safe_local_path(skill_dir, rel)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = client.read_text_file(repo, remote_path, max_bytes=MAX_SINGLE_FILE_BYTES)
        except GitHubError:
            if rel.lower() == "skill.md":
                raise
            continue
        local_path.write_text(text, encoding="utf-8")
    canonical_manifest = skill_dir / "SKILL.md"
    if not canonical_manifest.exists():
        for item in skill_dir.iterdir():
            if item.is_file() and item.name.lower() == "skill.md":
                item.rename(canonical_manifest)
                break
    return skill_dir


def _repo_has_tests(tree: list[dict[str, Any]]) -> bool:
    for item in tree:
        path = str(item.get("path") or "").lower()
        parts = path.split("/")
        if any(part in {"test", "tests", "evals"} for part in parts):
            return True
    return False


def _repo_has_readme(tree: list[dict[str, Any]]) -> bool:
    return any(
        PurePosixPath(str(item.get("path") or "")).name.lower().startswith("readme")
        for item in tree
    )


def index_repository(
    client: GitHubClient,
    session: Session,
    repo: DiscoveredRepository,
    *,
    now: datetime | None = None,
) -> tuple[int, list[str]]:
    indexed_at = now or datetime.now(UTC)
    tree = client.recursive_tree(repo)
    roots = _candidate_skill_roots(tree)
    if not roots:
        return 0, []

    velocity = estimate_star_velocity_7d(session, repo.full_name, repo.stars, indexed_at)
    repo_signals = RepositorySignals(
        stars=repo.stars,
        forks=repo.forks,
        pushed_at=repo.pushed_at,
        archived=repo.archived,
        license_spdx=repo.license_spdx,
        has_tests=_repo_has_tests(tree),
        has_readme=_repo_has_readme(tree),
        contributors=0,
        star_velocity_7d=velocity,
    )

    count = 0
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="skillobs-") as tmp:
        temp = Path(tmp)
        for root in roots:
            try:
                local_dir = _materialize_skill(client, repo, root, tree, temp)
                parsed = parse_skill_directory(local_dir)
                security = assess_skill_security(parsed)
                score = score_skill(
                    spec=parsed.spec,
                    security=security,
                    repo=repo_signals,
                    description_length=len(parsed.description),
                    body_chars=len(parsed.body),
                )
                repo_owner, repo_name = repo.full_name.split("/", 1)
                canonical_key = canonical_skill_key(repo_owner, repo_name, root or ".")
                fingerprint = content_fingerprint(parsed.raw)
                duplicate_of = find_duplicate_key(session, fingerprint, canonical_key)
                categories = classify_categories(parsed.description, parsed.body)
                clients = infer_clients(root or ".", parsed.compatibility, parsed.files)
                indexed = IndexedSkill(
                    canonical_key=canonical_key,
                    content_fingerprint=fingerprint,
                    repo_full_name=repo.full_name,
                    repo_url=repo.html_url,
                    repo_default_branch=repo.default_branch,
                    path=root or ".",
                    name=parsed.name,
                    description=parsed.description,
                    license=parsed.license or repo.license_spdx,
                    compatibility=parsed.compatibility,
                    metadata=parsed.metadata,
                    allowed_tools=parsed.allowed_tools,
                    spec=parsed.spec,
                    security=security,
                    score=score,
                    resources=parsed.resource_counts,
                    stars=repo.stars,
                    forks=repo.forks,
                    pushed_at=repo.pushed_at,
                    archived=repo.archived,
                    discovery_source=repo.discovery_source,
                    indexed_at=indexed_at,
                    evidence={
                        "manifest": (
                            f"{repo.html_url}/blob/{repo.default_branch}/"
                            f"{root + '/' if root else ''}SKILL.md"
                        ),
                        "tree_files_scanned": len(_paths_for_skill(tree, root)),
                        "repo_has_tests": repo_signals.has_tests,
                        "repo_has_readme": repo_signals.has_readme,
                        "star_velocity_7d": velocity,
                        "categories": categories,
                        "client_compatibility_evidence": clients,
                        "duplicate_of": duplicate_of,
                        "source_tier": (
                            "official-seed"
                            if repo.discovery_source == "official-seed"
                            else "community"
                        ),
                    },
                )
                upsert_skill(session, indexed)
                count += 1
            except (GitHubError, SkillParseError, OSError, ValueError) as exc:
                errors.append(f"{repo.full_name}:{root or '.'}: {exc}")
    record_repository_snapshot(
        session,
        repo_full_name=repo.full_name,
        captured_at=indexed_at,
        stars=repo.stars,
        forks=repo.forks,
    )
    return count, errors


def refresh_catalog(
    client: GitHubClient,
    session: Session,
    repositories: Iterable[DiscoveredRepository] | None = None,
    *,
    max_repositories: int | None = None,
) -> PipelineReport:
    repos = list(repositories if repositories is not None else client.discover())
    if max_repositories is not None:
        repos = repos[:max_repositories]
    report: PipelineReport = PipelineReport(
        repositories_seen=len(repos),
        repositories_with_skills=0,
        skills_indexed=0,
        errors=[],
    )
    for repo in repos:
        try:
            count, errors = index_repository(client, session, repo)
        except GitHubError as exc:
            report["errors"].append(f"{repo.full_name}: {exc}")
            continue
        if count:
            report["repositories_with_skills"] += 1
            report["skills_indexed"] += count
        report["errors"].extend(errors)
    return report
