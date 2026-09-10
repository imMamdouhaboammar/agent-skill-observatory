from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from .events import PublishedSkillRecord


class PublicationStateError(RuntimeError):
    pass


def _validate_segment(value: str, *, label: str) -> str:
    if not value or value in {".", ".."}:
        raise ValueError(f"invalid {label} segment: {value!r}")
    if "\x00" in value or "\\" in value or "/" in value:
        raise ValueError(f"unsafe {label} segment: {value!r}")
    return value


def _split_repository(repo_full_name: str) -> tuple[str, str]:
    if "\x00" in repo_full_name or "\\" in repo_full_name:
        raise ValueError("unsafe repository name")
    parts = repo_full_name.split("/")
    if len(parts) != 2:
        raise ValueError("repository must be owner/repo")
    owner = _validate_segment(parts[0], label="owner")
    repo = _validate_segment(parts[1], label="repository")
    return owner, repo


def _split_canonical_key(canonical_key: str) -> tuple[str, str, tuple[str, ...]]:
    if canonical_key.count(":") != 1:
        raise ValueError("canonical key must contain exactly one ':'")
    repo_full_name, skill_path = canonical_key.split(":", 1)
    owner, repo = _split_repository(repo_full_name)
    if skill_path == ".":
        return owner, repo, ("_root",)
    if not skill_path or skill_path.startswith("/"):
        raise ValueError("skill path must be relative")
    if "\x00" in skill_path or "\\" in skill_path:
        raise ValueError("unsafe skill path")
    segments = tuple(skill_path.split("/"))
    for segment in segments:
        _validate_segment(segment, label="skill path")
    if segments[0] == "_root":
        raise ValueError("_root is reserved for repository-root Skills")
    return owner, repo, segments


def skill_record_path(canonical_key: str) -> PurePosixPath:
    owner, repo, segments = _split_canonical_key(canonical_key)
    return PurePosixPath("catalog", "skills", owner, repo, *segments, "record.json")


def skill_markdown_path(canonical_key: str) -> PurePosixPath:
    owner, repo, segments = _split_canonical_key(canonical_key)
    return PurePosixPath("awesome", "skills", owner, repo, *segments, "README.md")


def repository_markdown_path(repo_full_name: str) -> PurePosixPath:
    owner, repo = _split_repository(repo_full_name)
    return PurePosixPath("awesome", "repos", owner, f"{repo}.md")


def category_markdown_path(category: str) -> PurePosixPath:
    if not category or "\x00" in category or "\\" in category or "/" in category:
        raise ValueError("unsafe category")
    if category in {".", ".."} or ".." in category.split("/"):
        raise ValueError("unsafe category")
    slug = re.sub(r"[^a-z0-9]+", "-", category.casefold()).strip("-")
    if not slug:
        raise ValueError("category does not contain a usable slug")
    return PurePosixPath("awesome", "categories", f"{slug}.md")


def load_published_catalog(root: Path) -> dict[str, PublishedSkillRecord]:
    catalog_root = root / "catalog" / "skills"
    if not catalog_root.exists():
        return {}

    published: dict[str, PublishedSkillRecord] = {}
    for path in sorted(catalog_root.rglob("record.json")):
        try:
            record = PublishedSkillRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValidationError, ValueError) as exc:
            raise PublicationStateError(f"malformed published record at {path}: {exc}") from exc
        if record.canonical_key in published:
            raise PublicationStateError(
                f"duplicate published canonical key: {record.canonical_key}"
            )
        published[record.canonical_key] = record
    return published
