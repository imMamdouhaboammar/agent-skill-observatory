from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .domain import ParsedSkill, SecurityFinding, SecurityReport


@dataclass(frozen=True)
class Rule:
    name: str
    severity: str
    pattern: re.Pattern[str]
    message: str


RULES = [
    Rule(
        "pipe-to-shell",
        "high",
        re.compile(r"(?:curl|wget)\b[^\n|]*(?:\||\|\s*)(?:ba)?sh\b", re.IGNORECASE),
        "Downloads remote content and pipes it directly to a shell.",
    ),
    Rule(
        "recursive-delete",
        "high",
        re.compile(r"\brm\s+-[^\n]*r[^\n]*f|\brm\s+-rf\b|\brm\s+-fr\b", re.IGNORECASE),
        "Uses recursive forced deletion.",
    ),
    Rule(
        "credential-access",
        "high",
        re.compile(
            r"(?:\.ssh|\.aws/credentials|\.config/gh/hosts\.yml|id_rsa|GITHUB_TOKEN)",
            re.IGNORECASE,
        ),
        "References credential or private-key locations.",
    ),
    Rule(
        "world-writable",
        "medium",
        re.compile(r"\bchmod\s+777\b"),
        "Makes a path world-writable.",
    ),
    Rule(
        "dynamic-exec",
        "medium",
        re.compile(r"\b(?:eval|exec)\s*\("),
        "Uses dynamic code execution.",
    ),
    Rule(
        "sudo",
        "medium",
        re.compile(r"\bsudo\b"),
        "Requests elevated operating-system privileges.",
    ),
]

PENALTIES = {"low": 4, "medium": 10, "high": 24, "critical": 40}
TEXT_EXTENSIONS = {".sh", ".bash", ".zsh", ".py", ".js", ".ts", ".ps1", ".rb", ".pl", ".md"}


def _scan_file(path: Path, root: Path) -> list[SecurityFinding]:
    if path.suffix.lower() not in TEXT_EXTENSIONS and path.name != "SKILL.md":
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    findings: list[SecurityFinding] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for rule in RULES:
            match = rule.pattern.search(line)
            if match:
                findings.append(
                    SecurityFinding(
                        rule=rule.name,
                        severity=rule.severity,  # type: ignore[arg-type]
                        file=str(path.relative_to(root)),
                        line=line_no,
                        message=rule.message,
                        evidence=line.strip()[:240],
                    )
                )
    return findings


def assess_skill_security(skill: ParsedSkill) -> SecurityReport:
    findings: list[SecurityFinding] = []
    for path in skill.files:
        findings.extend(_scan_file(path, skill.root))
    penalty = sum(PENALTIES[item.severity] for item in findings)
    score = max(0, 100 - penalty)
    return SecurityReport(score=score, findings=findings)
