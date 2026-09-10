from __future__ import annotations

import re
from pathlib import Path

MAX_CATEGORIES = 6

CATEGORY_KEYWORDS = {
    "engineering": {
        "code", "repository", "pull request", "debug", "developer", "frontend", "backend", "api", "git", "ci",
    },
    "code-review": {"code review", "review diff", "pull request review", "review changes"},
    "testing": {"test", "testing", "pytest", "jest", "playwright", "cypress", "e2e", "regression"},
    "security": {
        "security", "vulnerability", "threat", "secret", "credential", "permission", "audit", "dependency risk",
    },
    "data": {
        "data", "sql", "database", "analytics", "etl", "csv", "spreadsheet", "pandas", "warehouse",
    },
    "ai-ml": {
        "llm", "machine learning", "model evaluation", "embedding", "embeddings", "rag", "fine-tuning", "prompt evaluation",
    },
    "research": {
        "research", "source", "citation", "literature", "evidence", "investigate", "documentation research",
    },
    "design": {
        "design", "ui", "ux", "visual", "figma", "typography", "layout", "accessibility",
    },
    "content": {"write", "writing", "copy", "content", "article", "social", "caption", "editorial"},
    "marketing": {
        "marketing", "campaign", "ads", "advertising", "seo", "brand", "conversion", "media buying",
    },
    "devops": {
        "deploy", "deployment", "docker", "kubernetes", "terraform", "cloud", "sre", "observability", "release",
    },
    "product": {"product", "product manager", "prd", "roadmap", "user story", "feature prioritization"},
    "project-management": {"project management", "sprint", "milestone", "backlog", "issue triage", "delivery plan"},
    "productivity": {"workflow", "automation", "planning", "meeting", "task", "productivity", "handoff"},
    "documentation": {"documentation", "docs", "readme", "technical writing", "api reference", "changelog"},
    "browser-automation": {"browser", "playwright", "selenium", "web automation", "scrape", "crawl"},
    "integrations": {"integration", "webhook", "oauth", "connector", "third-party api", "mcp"},
    "mobile": {"mobile", "android", "ios", "react native", "flutter", "swift", "kotlin"},
    "media": {"video", "audio", "image", "media", "captioning", "transcription", "render"},
    "finance": {"finance", "financial", "accounting", "invoice", "budget", "forecast", "portfolio"},
    "legal-compliance": {"legal", "compliance", "policy", "privacy", "gdpr", "license review", "regulatory"},
    "education": {"education", "teaching", "lesson", "course", "quiz", "exercise", "learning"},
    "customer-support": {"customer support", "support ticket", "help desk", "customer service", "incident response"},
    "commerce": {"commerce", "ecommerce", "checkout", "catalog", "order", "inventory", "storefront"},
}


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = rf"(?<![\w-]){re.escape(keyword)}(?![\w-])"
    return re.search(pattern, text) is not None


def classify_categories(description: str, body: str) -> list[str]:
    description_l = description.lower()
    body_l = body.lower()
    scored: list[tuple[int, str]] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        description_hits = sum(
            1 for keyword in keywords if _contains_keyword(description_l, keyword)
        )
        body_hits = sum(1 for keyword in keywords if _contains_keyword(body_l, keyword))
        score = (description_hits * 2) + body_hits
        if score:
            scored.append((score, category))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [category for _, category in scored[:MAX_CATEGORIES]] or ["other"]


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
