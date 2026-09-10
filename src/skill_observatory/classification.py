from __future__ import annotations

from pathlib import Path

CATEGORY_KEYWORDS = {
    "engineering": {
        "code", "repository", "pull request", "debug", "test",
        "frontend", "backend", "api", "git", "developer", "ci",
    },
    "security": {
        "security", "vulnerability", "threat", "secret",
        "credential", "permission", "audit", "dependency risk",
    },
    "data": {
        "data", "sql", "database", "analytics", "etl",
        "csv", "spreadsheet", "pandas", "warehouse",
    },
    "research": {
        "research", "source", "citation", "literature",
        "evidence", "investigate", "documentation",
    },
    "design": {"design", "ui", "ux", "visual", "figma", "typography", "layout", "accessibility"},
    "content": {"write", "writing", "copy", "content", "article", "social", "caption", "editorial"},
    "devops": {
        "deploy", "deployment", "docker", "kubernetes", "terraform",
        "cloud", "sre", "observability", "release",
    },
    "productivity": {
        "workflow", "automation", "planning", "meeting",
        "task", "productivity", "handoff",
    },
}


def classify_categories(description: str, body: str) -> list[str]:
    haystack = f"{description}\n{body}".lower()
    scored: list[tuple[int, str]] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score:
            scored.append((score, category))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [category for _, category in scored[:4]] or ["other"]


def infer_clients(path: str, compatibility: str | None, files: list[Path]) -> dict[str, list[str]]:
    evidence: dict[str, list[str]] = {}
    normalized = path.lower().strip("/")
    compatibility_l = (compatibility or "").lower()
    file_names = {str(path).replace("\\", "/").lower() for path in files}

    def add(client: str, reason: str) -> None:
        evidence.setdefault(client, []).append(reason)

    if normalized.startswith(".agents/skills"):
        add("OpenAI Codex", "skill stored under the cross-client .agents/skills path")
        add("GitHub Copilot", "GitHub Copilot supports project skills under .agents/skills")
    if normalized.startswith(".claude/skills"):
        add("Claude Code", "skill stored under .claude/skills")
        add("GitHub Copilot", "GitHub Copilot supports project skills under .claude/skills")
    if normalized.startswith(".github/skills"):
        add("GitHub Copilot", "skill stored under .github/skills")
    has_openai_yaml = any(
        name.endswith("agents/openai.yaml") or name == "agents/openai.yaml"
        for name in file_names
    )
    if has_openai_yaml:
        add("OpenAI Codex", "agents/openai.yaml metadata is present")
    if "codex" in compatibility_l or "openai" in compatibility_l:
        add("OpenAI Codex", "compatibility metadata names Codex/OpenAI")
    if "claude" in compatibility_l:
        add("Claude Code", "compatibility metadata names Claude")
    if "copilot" in compatibility_l:
        add("GitHub Copilot", "compatibility metadata names Copilot")
    return evidence
