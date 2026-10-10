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

# Detect explicit unrestricted file-serving capabilities in skill instructions.
# These are static risk indicators; they do not assert an exploit is possible.
RULES.append(
    Rule(
        "unrestricted-host-file-access",
        "high",
        re.compile(
            r"\b(?:serve|serves|serving|expose|exposes|exposing|share|shares|sharing|browse|browses|browsing|read|reads|reading|provides?\s+access\s+to)\b"
            r".{0,100}\b(?:any|all|every|arbitrary|unrestricted|entire)\b.{0,100}"
            r"\b(?:file|files|filesystem|file system)\b.{0,60}\b(?:host|local|server|machine)\b"
            r"|\b(?:serve|serves|serving|expose|exposes|exposing|share|shares|sharing|browse|browses|browsing|read|reads|reading|provides?\s+access\s+to)\b"
            r".{0,100}\b(?:any|all|every|arbitrary|unrestricted|entire)\b.{0,100}"
            r"\b(?:host|local|server|machine)\b.{0,60}\b(?:file|files|filesystem|file system)\b",
            re.IGNORECASE,
        ),
        "Skill may serve or expose arbitrary files from its host without a bounded share root.",
    )
)

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
    lines = text.splitlines()
    for line_no, line in enumerate(lines, 1):
        for rule in RULES:
            if rule.name == "unrestricted-host-file-access":
                # Allow ordinary wrapped prose while reporting a capability only
                # once, where its action verb first appears.
                context = " ".join(lines[line_no - 1 : line_no + 2])
                match = None
                for candidate in rule.pattern.finditer(context):
                    if candidate.start() >= len(line):
                        break
                    # Do not combine a benign verb from one sentence with
                    # unrestricted host-file terms in a later sentence.
                    if re.search(r"[.;!?](?=\\s|$)", candidate.group()):
                        continue
                    prefix = context[max(0, candidate.start() - 90) : candidate.start()]
                    prefix = re.split(r"[.;!?]\\s*", prefix)[-1]
                    if re.search(
                        r"\\b(?:never|do not|don't|must not|should not|cannot|can't|"
                        r"prevent(?:s|ed)?|block(?:s|ed)?|den(?:y|ies)|disallow(?:s)?|"
                        r"prohibit(?:s)?|forbid(?:s)?|refuse(?:s)?)\\b.{0,65}$",
                        prefix,
                        re.IGNORECASE,
                    ):
                        continue
                    # Scope the share-root exemption to the matched clause,
                    # not another mode or sentence on the same line.
                    clause = re.split(r"[.;!?]\\s*", context[candidate.start() :], maxsplit=1)[0]
                    if re.search(
                        r"\\b(?:in|within|inside|under|from)\\s+(?:the|a|an)?\\s*"
                        r"(?:(?:local|configured|approved|designated|selected)\\s+)?"
                        r"(?:share|shared)\\s+(?:root|directory|folder)\\b",
                        clause,
                        re.IGNORECASE,
                    ):
                        continue
                    match = candidate
                    break
                if match is None:
                    continue
            else:
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
