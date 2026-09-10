from __future__ import annotations

import json
from collections import Counter

from pydantic import BaseModel, Field

from .events import PublishedSkillRecord, SkillEvent
from .publication_store import (
    category_markdown_path,
    repository_markdown_path,
    skill_markdown_path,
    skill_record_path,
)

README_START = "<!-- AWESOME_INDEX_START -->"
README_END = "<!-- AWESOME_INDEX_END -->"


class DirectoryPatch(BaseModel):
    writes: dict[str, str] = Field(default_factory=dict)
    deletes: list[str] = Field(default_factory=list)


def _categories(record: PublishedSkillRecord) -> list[str]:
    raw = (record.skill.evidence or {}).get("categories") or []
    values = sorted({str(item).strip() for item in raw if str(item).strip()})
    return values or ["uncategorized"]


def _client_names(record: PublishedSkillRecord) -> list[str]:
    raw = (record.skill.evidence or {}).get("client_compatibility_evidence") or {}
    if not isinstance(raw, dict):
        return []
    return sorted(str(name) for name in raw)


def _manifest(record: PublishedSkillRecord) -> str:
    value = (record.skill.evidence or {}).get("manifest")
    if isinstance(value, str) and value:
        return value
    branch = record.skill.repo_default_branch
    path = record.skill.path
    suffix = "SKILL.md" if path == "." else f"{path}/SKILL.md"
    return f"{record.skill.repo_url}/blob/{branch}/{suffix}"


def _render_record_json(record: PublishedSkillRecord) -> str:
    payload = record.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _render_skill_page(record: PublishedSkillRecord) -> str:
    skill = record.skill
    categories = _categories(record)
    clients = _client_names(record)
    findings = skill.security.findings
    first_seen = (skill.evidence or {}).get("first_seen_at") or "unknown"
    lines = [
        f"# {skill.name}",
        "",
        f"Source repository: [{skill.repo_full_name}]({skill.repo_url})",
        "",
        f"Canonical key: `{record.canonical_key}`",
        "",
        f"Manifest: [{_manifest(record)}]({_manifest(record)})",
        "",
        "## Description",
        "",
        skill.description,
        "",
        "## Classification",
        "",
        f"Categories: {', '.join(categories)}",
        f"Client compatibility: {', '.join(clients) if clients else 'not explicitly detected'}",
        f"License: {skill.license or 'not declared'}",
        "",
        "## Resources",
        "",
        f"Scripts: {skill.resources.scripts}",
        f"References: {skill.resources.references}",
        f"Assets: {skill.resources.assets}",
        f"Other: {skill.resources.other}",
        "",
        "## Scores",
        "",
        f"Overall: {skill.score.overall}",
        f"Quality: {skill.score.quality}",
        f"Security: {skill.score.security}",
        f"Maintenance: {skill.score.maintenance}",
        f"Adoption: {skill.score.adoption}",
        "",
        "## Static security findings",
        "",
    ]
    if findings:
        lines.extend(
            f"- {finding.severity}: {finding.rule} in {finding.file}: {finding.message}"
            for finding in findings
        )
    else:
        lines.append("No static findings recorded")
    lines.extend(
        [
            "",
            "Static analysis is not malware certification",
            "",
            "## Publication metadata",
            "",
            f"First seen: {first_seen}",
            f"Indexed: {skill.indexed_at.isoformat()}",
            f"Published: {record.published_at.isoformat()}",
            f"Publication event: {record.publication_event}",
            f"Source fingerprint: `{record.source_fingerprint}`",
            f"Analysis fingerprint: `{record.analysis_fingerprint}`",
            "",
        ]
    )
    return "\n".join(lines)


def _repo_records(
    catalog: dict[str, PublishedSkillRecord], repo_full_name: str
) -> list[PublishedSkillRecord]:
    return sorted(
        (record for record in catalog.values() if record.skill.repo_full_name == repo_full_name),
        key=lambda record: (
            -record.skill.score.overall,
            -record.skill.stars,
            record.skill.name.casefold(),
            record.canonical_key,
        ),
    )


def _render_repository_page(records: list[PublishedSkillRecord]) -> str:
    first = records[0].skill
    categories = sorted({category for record in records for category in _categories(record)})
    best_score = max(record.skill.score.overall for record in records)
    security_bands = Counter(
        "85+"
        if record.skill.security.score >= 85
        else "60-84"
        if record.skill.security.score >= 60
        else "<60"
        for record in records
    )
    lines = [
        f"# {first.repo_full_name}",
        "",
        f"Repository: [{first.repo_url}]({first.repo_url})",
        "",
        f"Published Skills: {len(records)}",
        f"Categories: {', '.join(categories)}",
        f"Best overall score: {best_score}",
        (
            "Security distribution: "
            f"85+={security_bands['85+']}, 60-84={security_bands['60-84']}, "
            f"<60={security_bands['<60']}"
        ),
        "",
        "| Skill | Path | Score | Security | Categories |",
        "|---|---|---:|---:|---|",
    ]
    for record in records:
        skill = record.skill
        path = skill.path if skill.path != "." else "_root"
        lines.append(
            f"| [{skill.name}](../../skills/{skill.repo_full_name}/{path}/README.md) | "
            f"`{skill.path}` | {skill.score.overall} | {skill.security.score} | "
            f"{', '.join(_categories(record))} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _category_records(
    catalog: dict[str, PublishedSkillRecord], category: str
) -> list[PublishedSkillRecord]:
    return sorted(
        (record for record in catalog.values() if category in _categories(record)),
        key=lambda record: (
            -record.skill.score.overall,
            -record.skill.stars,
            record.skill.name.casefold(),
            record.canonical_key,
        ),
    )


def _render_category_page(category: str, records: list[PublishedSkillRecord]) -> str:
    lines = [
        f"# {category}",
        "",
        f"Published Skills: {len(records)}",
        "",
        "| Skill | Repository | Score | Security | Stars | Description |",
        "|---|---|---:|---:|---:|---|",
    ]
    for record in records:
        skill = record.skill
        path = skill.path if skill.path != "." else "_root"
        description = " ".join(skill.description.split()).replace("|", "\\|")
        lines.append(
            f"| [{skill.name}](../skills/{skill.repo_full_name}/{path}/README.md) | "
            f"[{skill.repo_full_name}]({skill.repo_url}) | {skill.score.overall} | "
            f"{skill.security.score} | {skill.stars} | {description} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_awesome_index(catalog: dict[str, PublishedSkillRecord]) -> str:
    records = sorted(catalog.values(), key=lambda record: record.canonical_key)
    repos = sorted({record.skill.repo_full_name for record in records})
    categories = sorted({category for record in records for category in _categories(record)})
    lines = [
        "# Agent Skill Observatory Directory",
        "",
        f"Published skills: **{len(records)}**",
        f"Repositories: **{len(repos)}**",
        "",
        "## Browse repositories",
        "",
    ]
    if repos:
        for repo in repos:
            owner, name = repo.split("/", 1)
            lines.append(f"- [{repo}](./repos/{owner}/{name}.md)")
    else:
        lines.append("No published repositories yet")
    lines.extend(["", "## Browse categories", ""])
    if categories:
        for category in categories:
            lines.append(f"- [{category}](./categories/{category_markdown_path(category).name})")
    else:
        lines.append("No published categories yet")
    lines.extend(["", "## All skills", ""])
    if records:
        for record in records:
            path = skill_markdown_path(record.canonical_key).relative_to("awesome")
            lines.append(f"- [{record.skill.name}](./{path}) · `{record.canonical_key}`")
    else:
        lines.append("No published skills yet")
    return "\n".join(lines).rstrip() + "\n"


def _readme_block(event: SkillEvent, catalog: dict[str, PublishedSkillRecord]) -> str:
    repos = {record.skill.repo_full_name for record in catalog.values()}
    return "\n".join(
        [
            f"Published skills: **{len(catalog)}**",
            f"Repositories: **{len(repos)}**",
            f"Latest Skill event: **{event.type}** · `{event.canonical_key}`",
            "",
            "[Browse the GitHub directory](./awesome/README.md) · [Open AWESOME.md](./AWESOME.md)",
        ]
    )


def _replace_readme_marker(text: str, block: str) -> str:
    if text.count(README_START) != 1 or text.count(README_END) != 1:
        raise ValueError("root README must contain exactly one Awesome index marker pair")
    before, tail = text.split(README_START, 1)
    previous, after = tail.split(README_END, 1)
    if README_START in previous or README_END in before:
        raise ValueError("invalid root README marker ordering")
    return before + README_START + "\n" + block.rstrip("\n") + "\n" + README_END + after


def _record_categories(record: PublishedSkillRecord | None) -> set[str]:
    return set(_categories(record)) if record is not None else set()


def render_skill_event(
    event: SkillEvent,
    catalog_after_event: dict[str, PublishedSkillRecord],
    *,
    current_root_readme: str,
) -> DirectoryPatch:
    writes: dict[str, str] = {}
    deletes: set[str] = set()

    if event.type == "remove":
        if event.before is None:
            raise ValueError("remove event requires before state")
        deletes.add(str(skill_record_path(event.canonical_key)))
        deletes.add(str(skill_markdown_path(event.canonical_key)))
        target_record = event.before
    else:
        if event.after is None:
            raise ValueError(f"{event.type} event requires after state")
        target_record = event.after
        writes[str(skill_record_path(event.canonical_key))] = _render_record_json(event.after)
        writes[str(skill_markdown_path(event.canonical_key))] = _render_skill_page(event.after)

    repo_name = target_record.skill.repo_full_name
    repo_records = _repo_records(catalog_after_event, repo_name)
    repo_path = str(repository_markdown_path(repo_name))
    if repo_records:
        writes[repo_path] = _render_repository_page(repo_records)
    else:
        deletes.add(repo_path)

    affected_categories = _record_categories(event.before) | _record_categories(event.after)
    for category in sorted(affected_categories):
        path = str(category_markdown_path(category))
        records = _category_records(catalog_after_event, category)
        if records:
            writes[path] = _render_category_page(category, records)
        else:
            deletes.add(path)

    writes["awesome/README.md"] = _render_awesome_index(catalog_after_event)
    writes["README.md"] = _replace_readme_marker(
        current_root_readme, _readme_block(event, catalog_after_event)
    )

    deletes.difference_update(writes)
    ordered_writes = {path: writes[path] for path in sorted(writes)}
    return DirectoryPatch(writes=ordered_writes, deletes=sorted(deletes))
