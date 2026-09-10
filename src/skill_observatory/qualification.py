from __future__ import annotations

import re

from pydantic import BaseModel, Field

from .domain import ParsedSkill, RepositorySignals, SecurityReport

POLICY_VERSION = 1
MIN_INSTRUCTION_CHARS = 400
MIN_SECURITY_SCORE = 90

_RESOURCE_PATH_RE = re.compile(
    r"(?<![\w./-])(?:\./)?(?:scripts|references|assets|evals|agents)/"
    r"[A-Za-z0-9_.@+%=-]+(?:/[A-Za-z0-9_.@+%=-]+)*"
)
_PRIVATE_PATH_PATTERNS = (
    re.compile(r"/(?:Users|home)/[^/\s`'\"]+/", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s`'\"]+\\", re.IGNORECASE),
)
_PROMPT_OVERRIDE_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(?:all\s+)?(?:previous|prior)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\breveal\s+(?:the\s+)?(?:system|developer)\s+prompt\b", re.IGNORECASE),
    re.compile(r"\boverride\s+(?:the\s+)?(?:system|developer)\s+instructions\b", re.IGNORECASE),
)


class QualificationReport(BaseModel):
    policy_version: int = POLICY_VERSION
    qualified: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)


def _relative_files(parsed: ParsedSkill) -> set[str]:
    paths: set[str] = set()
    root = parsed.root.resolve()
    for path in parsed.files:
        try:
            relative = path.resolve().relative_to(root)
        except ValueError:
            continue
        paths.add(relative.as_posix())
    return paths


def _resource_integrity(parsed: ParsedSkill) -> bool:
    available = _relative_files(parsed)
    referenced = {
        match.group(0).removeprefix("./").rstrip(".,;:)")
        for match in _RESOURCE_PATH_RE.finditer(parsed.body)
    }
    return referenced.issubset(available)


def _portable(parsed: ParsedSkill) -> bool:
    body = parsed.body
    if "../" in body or "..\\" in body:
        return False
    return not any(pattern.search(body) for pattern in _PRIVATE_PATH_PATTERNS)


def _behaviorally_safe(parsed: ParsedSkill) -> bool:
    return not any(pattern.search(parsed.body) for pattern in _PROMPT_OVERRIDE_PATTERNS)


def _instruction_depth(parsed: ParsedSkill) -> bool:
    body = parsed.body.strip()
    if len(body) < MIN_INSTRUCTION_CHARS:
        return False
    headings = re.findall(r"(?m)^#{1,6}\s+\S+", body)
    steps = re.findall(r"(?m)^\s*(?:[-*]|\d+[.)])\s+\S+", body)
    return len(headings) >= 2 or len(steps) >= 3


def _license_present(parsed: ParsedSkill, repo: RepositorySignals) -> bool:
    value = (parsed.license or repo.license_spdx or "").strip()
    return bool(value) and value.upper() not in {"NONE", "NOASSERTION", "UNLICENSED"}


def qualify_skill(
    parsed: ParsedSkill,
    security: SecurityReport,
    repo: RepositorySignals,
    *,
    duplicate_of: str | None,
) -> QualificationReport:
    """Apply deterministic publication admission checks without popularity inputs."""

    has_blocking_security_finding = any(
        finding.severity in {"medium", "high", "critical"}
        for finding in security.findings
    )
    relative_files = _relative_files(parsed)
    has_local_eval = any(path.startswith("evals/") for path in relative_files)
    checks = {
        "spec-validity": parsed.spec.valid,
        "instruction-depth": _instruction_depth(parsed),
        "static-security": (
            security.score >= MIN_SECURITY_SCORE and not has_blocking_security_finding
        ),
        "script-verification": parsed.resource_counts.scripts == 0 or repo.has_tests or has_local_eval,
        "portability": _portable(parsed),
        "resource-integrity": _resource_integrity(parsed),
        "behavioral-safety": _behaviorally_safe(parsed),
        "duplicate": duplicate_of is None,
        "active-source": not repo.archived,
        "license": _license_present(parsed, repo),
    }
    blocking_reasons = [name for name, passed in checks.items() if not passed]
    return QualificationReport(
        qualified=not blocking_reasons,
        blocking_reasons=blocking_reasons,
        checks=checks,
    )
