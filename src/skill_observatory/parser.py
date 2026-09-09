from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .domain import ParsedSkill, ResourceCounts, SpecValidation

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillParseError(ValueError):
    pass


def _frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---\n"):
        raise SkillParseError("SKILL.md must start with YAML frontmatter")
    end = raw.find("\n---\n", 4)
    if end == -1:
        raise SkillParseError("SKILL.md frontmatter is not terminated")
    try:
        data = yaml.safe_load(raw[4:end]) or {}
    except yaml.YAMLError as exc:
        raise SkillParseError(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise SkillParseError("SKILL.md frontmatter must be a mapping")
    return data, raw[end + 5 :]


def _resource_counts(root: Path) -> ResourceCounts:
    def count_files(name: str) -> int:
        directory = root / name
        if not directory.is_dir():
            return 0
        return sum(
            1
            for p in directory.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )

    standard = {"SKILL.md", "scripts", "references", "assets"}
    other = sum(1 for p in root.iterdir() if p.name not in standard)
    return ResourceCounts(
        scripts=count_files("scripts"),
        references=count_files("references"),
        assets=count_files("assets"),
        other=other,
    )


def _validate(root: Path, data: dict[str, Any]) -> SpecValidation:
    errors: list[str] = []
    warnings: list[str] = []
    name = data.get("name")
    description = data.get("description")

    if not isinstance(name, str) or not name:
        errors.append("name is required")
    else:
        if len(name) > 64:
            errors.append("name must be at most 64 characters")
        if not NAME_RE.fullmatch(name):
            errors.append("name must use lowercase letters, digits, and single hyphens only")
        if name != root.name:
            errors.append("name must match the parent directory name")

    if not isinstance(description, str) or not description.strip():
        errors.append("description is required and must be non-empty")
    elif len(description) > 1024:
        errors.append("description must be at most 1024 characters")

    compatibility = data.get("compatibility")
    if compatibility is not None:
        if not isinstance(compatibility, str):
            errors.append("compatibility must be a string")
        elif len(compatibility) > 500:
            errors.append("compatibility must be at most 500 characters")

    metadata = data.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            errors.append("metadata must be a mapping")
        elif any(not isinstance(k, str) or not isinstance(v, str) for k, v in metadata.items()):
            warnings.append("metadata values should be strings according to the open specification")

    allowed = data.get("allowed-tools")
    if allowed is not None and not isinstance(allowed, str):
        warnings.append("allowed-tools should be a space-separated string")

    return SpecValidation(valid=not errors, errors=errors, warnings=warnings)


def parse_skill_directory(root: Path) -> ParsedSkill:
    root = root.resolve()
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        raise SkillParseError(f"No SKILL.md found in {root}")
    raw = skill_md.read_text(encoding="utf-8")
    data, body = _frontmatter(raw)
    spec = _validate(root, data)

    metadata_raw = data.get("metadata") or {}
    metadata = {str(k): str(v) for k, v in metadata_raw.items()} if isinstance(metadata_raw, dict) else {}
    allowed_raw = data.get("allowed-tools") or ""
    allowed_tools = allowed_raw.split() if isinstance(allowed_raw, str) else []
    files = [
        p
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]

    return ParsedSkill(
        root=root,
        skill_md_path=skill_md,
        name=str(data.get("name") or ""),
        description=str(data.get("description") or ""),
        license=str(data["license"]) if data.get("license") is not None else None,
        compatibility=str(data["compatibility"]) if data.get("compatibility") is not None else None,
        metadata=metadata,
        allowed_tools=allowed_tools,
        body=body.strip(),
        raw=raw,
        resource_counts=_resource_counts(root),
        spec=spec,
        files=files,
    )
